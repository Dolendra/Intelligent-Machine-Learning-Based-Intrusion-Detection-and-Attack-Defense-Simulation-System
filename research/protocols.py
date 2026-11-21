"""Experiment protocols for the open-set study.

* LOAFO     leave-one-attack-family-out: one family is removed from train/val and appears
            only at test time as a simulated zero-day.
* Temporal  train on earlier capture days, test on a later day (CICIDS2017's Friday
            attacks — Bot, PortScan, DDoS — never occur Monday–Thursday).
* Cross     train on CICIDS2017, test on CSE-CIC-IDS2018 (different network, year, tooling).

Every run returns a JSON-serializable record; aggregation happens in ``summarize``.
"""
from __future__ import annotations

import time
from typing import Callable, Iterable

import numpy as np
import pandas as pd

from research.data import cap_per_family, feature_columns, stratified_split
from research.features import SignedLogScaler
from research.metrics import detection_metrics, mean_ci, openset_attribution, paired_test, seed_level_test
from research.openset import PROPOSED, AegisOSR, method_scores

LOAFO_FAMILIES = ["Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"]
RARE_NATURAL_UNKNOWN = ["Infiltration", "Heartbleed"]

TRAIN_CAPS = {"BENIGN": 300_000, "_attack": 60_000}
VAL_CAPS = {"BENIGN": 60_000, "_attack": 10_000}
TEST_CAPS = {"BENIGN": 150_000, "_attack": 25_000}

Log = Callable[[str], None]
# Optional per-flow score sink, called as dump(key, model, scores, families, groups) — see research/scoredump.py.
Dump = Callable[..., None]


def _cap_keep_index(df: pd.DataFrame, caps: dict[str, int], seed: int) -> pd.DataFrame:
    parts = [g.sample(n=caps[str(f)], random_state=seed) if len(g) > caps[str(f)] else g
             for f, g in df.groupby("family", observed=True)]
    return pd.concat(parts)


def _caps(df: pd.DataFrame, spec: dict) -> dict[str, int]:
    return {str(f): spec["BENIGN"] if f == "BENIGN" else spec["_attack"] for f in df["family"].unique()}


WARMUP_WINDOWS = (500, 2000, 5000)
ORACLE_WINDOW = 2000


def _evaluate(model: AegisOSR, Xte: np.ndarray, fam: np.ndarray, groups: np.ndarray,
              alpha: float, dump: Dump | None = None, key: dict | None = None) -> tuple[dict, dict, float]:
    t = time.time()
    sc = model.score(Xte)
    elapsed = time.time() - t
    if dump is not None:  # passive observer: records per-flow evidence, never changes model state
        dump(key or {}, model, sc, fam, groups)
    methods = {name: detection_metrics(m, groups, alpha, fam) for name, m in method_scores(sc).items()}
    attribution = openset_attribution(model.label(sc), fam, groups)
    return methods, attribution, elapsed


def run_once(
    *,
    protocol: str,
    fold: str,
    seed: int,
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    unknown_families: Iterable[str],
    alpha: float = 0.01,
    log: Log = print,
    ae_kwargs: dict | None = None,
    warmup: pd.DataFrame | None = None,
    warmup_oracle: pd.DataFrame | None = None,
    windows: Iterable[int] = WARMUP_WINDOWS,
    dump: Dump | None = None,
    model_kwargs: dict | None = None,
    on_split: Callable[[dict, dict], None] | None = None,
) -> dict:
    """Fit on train, calibrate on val, evaluate on test.

    If ``warmup`` (target-environment benign flows, arrival order) is given, additionally
    evaluate label-light adaptation: ``recal@W`` re-calibrates on the first W flows and
    ``recal+ref@W`` also extends the kNN benign reference. Warm-up flows are never in ``test``.
    """
    unknown = set(unknown_families)
    feats = feature_columns(train)
    if on_split is not None:  # e.g. R3 leakage checks; must not modify the frames
        on_split({"protocol": protocol, "fold": fold, "seed": seed, "unknown": sorted(unknown)},
                 {"train": train, "val": val, "test": test, "warmup": warmup, "warmup_oracle": warmup_oracle})
    t0 = time.time()
    scaler = SignedLogScaler().fit(train[feats].to_numpy())
    Xtr, Xva, Xte = (scaler.transform(d[feats].to_numpy()) for d in (train, val, test))
    model = AegisOSR(seed=seed, alpha=alpha, ae_kwargs=ae_kwargs, **(model_kwargs or {}))
    model.fit(Xtr, train["family"].to_numpy(), Xva, val["family"].to_numpy(), log=log)
    fit_s = time.time() - t0

    fam = test["family"].astype(str).to_numpy()
    groups = np.where(fam == "BENIGN", "benign", np.where(np.isin(fam, list(unknown)), "unknown", "known"))
    key = {"protocol": protocol, "fold": fold, "seed": seed}
    methods, attribution, score_s = _evaluate(model, Xte, fam, groups, alpha, dump, {**key, "variant": "none"})

    rec = {
        "protocol": protocol,
        "fold": fold,
        "seed": seed,
        "alpha": alpha,
        "known_families": [str(c) for c in model.classes_ if c != "BENIGN"],
        "unknown_families": sorted(unknown),
        "n_train": int(len(train)),
        "n_val": int(len(val)),
        "n_calibration": list(model.n_cal_),
        "n_test": {g: int((groups == g).sum()) for g in ("benign", "known", "unknown")},
        "methods": methods,
        "aegis_osr_attribution": attribution,
        "ae_epochs": len(model.ae_.history_) if hasattr(model, "ae_") else None,
        "fit_seconds": round(fit_s, 1),
        "score_ms_per_1k_flows": round(1e6 * score_s / max(len(test), 1), 3),
        "adaptation": {},
    }
    p = methods[PROPOSED]
    c = methods.get("Closed-set XGB") or next(iter(methods.values()))
    log(f"[{protocol}:{fold}:s{seed}] Aegis-OSR ZDR={p['zero_day_recall']} AUROC_u={p['auroc_unknown']} "
        f"FPR={p['fpr']:.4f} | closed-set ZDR={c['zero_day_recall']} FPR={c['fpr']:.4f} ({fit_s:.0f}s fit)")

    if warmup is not None and len(warmup):
        Xw_all = scaler.transform(warmup.sort_values(["day", "seq"])[feats].to_numpy())
        base_state = model.snapshot()
        for W in windows:
            if W > len(Xw_all):
                continue
            for variant, upd in (("recal", False), ("recal+ref", True)):
                model.restore(base_state).recalibrate(Xw_all[:W], update_reference=upd)
                m_ad, a_ad, _ = _evaluate(model, Xte, fam, groups, alpha, dump, {**key, "variant": f"{variant}@{W}"})
                rec["adaptation"][f"{variant}@{W}"] = {"window": W, "variant": variant, "methods": m_ad,
                                                       "aegis_osr_attribution": a_ad}
                pa = m_ad[PROPOSED]
                log(f"    {variant}@{W}: Aegis-OSR ZDR={pa['zero_day_recall']:.3f} FPR={pa['fpr']:.4f}")
        if warmup_oracle is not None and len(warmup_oracle) >= ORACLE_WINDOW:
            # upper bound: a *representative* random benign sample of the target (not in test)
            Xo = scaler.transform(warmup_oracle[feats].to_numpy()[:ORACLE_WINDOW])
            model.restore(base_state).recalibrate(Xo, update_reference=False)  # isolates calibration drift
            m_ad, a_ad, _ = _evaluate(model, Xte, fam, groups, alpha, dump,
                                      {**key, "variant": f"oracle@{ORACLE_WINDOW}"})
            rec["adaptation"][f"oracle@{ORACLE_WINDOW}"] = {"window": ORACLE_WINDOW, "variant": "oracle",
                                                           "methods": m_ad, "aegis_osr_attribution": a_ad}
            pa = m_ad[PROPOSED]
            log(f"    oracle@{ORACLE_WINDOW}: Aegis-OSR ZDR={pa['zero_day_recall']:.3f} FPR={pa['fpr']:.4f}")
        model.restore(base_state)
    return rec


def _oracle_sample(pool: pd.DataFrame, test: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    rest = pool[(pool["family"] == "BENIGN") & ~pool.index.isin(test.index)]
    return rest.sample(n=min(n, len(rest)), random_state=seed)


def _split_warmup(target: pd.DataFrame, max_window: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Earliest ``max_window`` benign target flows → warm-up; everything else → test pool."""
    benign = target[target["family"] == "BENIGN"].sort_values(["day", "seq"])
    warm = benign.iloc[:max_window]
    return warm, target.drop(index=warm.index)


# --------------------------------------------------------------------------- LOAFO
def loafo(df: pd.DataFrame, seeds: Iterable[int], families: Iterable[str] = LOAFO_FAMILIES, log: Log = print, **kw) -> list[dict]:
    records = []
    rare = df[df["family"].isin(RARE_NATURAL_UNKNOWN)]
    base = df[~df["family"].isin(RARE_NATURAL_UNKNOWN)]
    for seed in seeds:
        tr_all, va_all, te_all = stratified_split(base, (0.6, 0.1, 0.3), seed)
        for held in families:
            train = cap_per_family(tr_all[tr_all["family"] != held], _caps(tr_all, TRAIN_CAPS), seed)
            val = cap_per_family(va_all[va_all["family"] != held], _caps(va_all, VAL_CAPS), seed)
            held_rows = base[base["family"] == held]  # never seen in train/val → use all rows
            test = pd.concat([
                cap_per_family(te_all[te_all["family"] != held], _caps(te_all, TEST_CAPS), seed),
                cap_per_family(held_rows, TEST_CAPS["_attack"], seed),
                rare,
            ], ignore_index=True)
            records.append(run_once(protocol="loafo", fold=held, seed=seed, train=train, val=val, test=test,
                                    unknown_families=[held, *RARE_NATURAL_UNKNOWN], log=log, **kw))
    return records


# --------------------------------------------------------------------------- temporal
TEMPORAL_FOLDS = {
    "Mon-Wed→Thu": (["Monday", "Tuesday", "Wednesday"], ["Thursday"]),
    "Mon-Thu→Fri": (["Monday", "Tuesday", "Wednesday", "Thursday"], ["Friday"]),
}


def temporal(df: pd.DataFrame, seeds: Iterable[int], log: Log = print, **kw) -> list[dict]:
    records = []
    for seed in seeds:
        for fold, (train_days, test_days) in TEMPORAL_FOLDS.items():
            past = df[df["day"].isin(train_days) & ~df["family"].isin(RARE_NATURAL_UNKNOWN)]
            future = df[df["day"].isin(test_days)]
            warm, future = _split_warmup(future, max(WARMUP_WINDOWS))
            tr, va, _ = stratified_split(past, (0.85, 0.15, 0.0), seed)
            train = cap_per_family(tr, _caps(tr, TRAIN_CAPS), seed)
            val = cap_per_family(va, _caps(va, VAL_CAPS), seed)
            test = _cap_keep_index(future, _caps(future, TEST_CAPS), seed)
            oracle = _oracle_sample(future, test, ORACLE_WINDOW, seed)
            test = test.reset_index(drop=True)
            seen = set(train["family"].astype(str))
            unknown = sorted(set(test["family"].astype(str)) - seen)
            records.append(run_once(protocol="temporal", fold=fold, seed=seed, train=train, val=val, test=test,
                                    unknown_families=unknown, log=log, warmup=warm,
                                    warmup_oracle=oracle, **kw))
    return records


# --------------------------------------------------------------------------- cross-dataset
def cross_dataset(src: pd.DataFrame, dst: pd.DataFrame, seeds: Iterable[int], log: Log = print,
                  src_name: str = "CICIDS2017", dst_name: str = "CSE-CIC-IDS2018", **kw) -> list[dict]:
    feats = feature_columns(src)
    dst = dst[feats + [c for c in dst.columns if c not in feats]]
    records = []
    for seed in seeds:
        src_base = src[~src["family"].isin(RARE_NATURAL_UNKNOWN)]
        tr, va, _ = stratified_split(src_base, (0.85, 0.15, 0.0), seed)
        train = cap_per_family(tr, _caps(tr, TRAIN_CAPS), seed)
        val = cap_per_family(va, _caps(va, VAL_CAPS), seed)
        warm, pool = _split_warmup(dst, max(WARMUP_WINDOWS))
        test = _cap_keep_index(pool, _caps(pool, TEST_CAPS), seed)
        oracle = _oracle_sample(pool, test, ORACLE_WINDOW, seed)
        test = test.reset_index(drop=True)
        unknown = sorted(set(test["family"].astype(str)) - set(train["family"].astype(str)))
        records.append(run_once(protocol="cross_dataset", fold=f"{src_name}→{dst_name}", seed=seed, train=train,
                                val=val, test=test, unknown_families=unknown, log=log, warmup=warm,
                                warmup_oracle=oracle, **kw))
    return records


# --------------------------------------------------------------------------- cross-dataset, per day
PERDAY_TEST_CAPS = {"BENIGN": 20_000, "_attack": 8_000}


SCREEN_WINDOW = 500   # W_s: earliest benign flows of the warm-up window (RESEARCH_GAP_ANALYSIS, Contribution 1)
SCREEN_ALPHA0 = 0.05  # alpha_0 of the staleness screen


def stream_screen(model: AegisOSR, Xw: np.ndarray, n: int = SCREEN_WINDOW, alpha0: float = SCREEN_ALPHA0) -> dict:
    """Source-calibrated exceedance rate e_j of every evidence stream on the first ``n`` warm-up flows.

    e_j = fraction of target benign flows whose *source* benign p-value of stream j is <= alpha0
    (p_j = exp(-surprisal_j) under the source C1 maps). Without shift e_j is about alpha0.
    Uses only benign target flows; the model state is not changed.
    """
    if len(Xw) == 0:
        return {}
    raw, _ = model._raw_scores(Xw[:n])
    out = {}
    for k, v in raw.items():
        if k in model.cdf_:
            p = np.exp(-model.cdf_[k](v))
            out[k] = float(np.mean(p <= alpha0))
    return {"window": int(min(n, len(Xw))), "alpha0": alpha0, "exceedance": out}


def cross_dataset_perday(src: pd.DataFrame, dst: pd.DataFrame, seeds: Iterable[int], log: Log = print,
                         alpha: float = 0.01, ae_kwargs: dict | None = None,
                         windows: Iterable[int] = WARMUP_WINDOWS, dump: Dump | None = None,
                         model_kwargs: dict | None = None,
                         on_split: Callable[[dict, dict], None] | None = None,
                         held_out: str | None = None, protocol: str = "cross_perday") -> list[dict]:
    """CICIDS2017 → CSE-CIC-IDS2018 with **independent per-day** recalibration (R1b).

    The model is trained once per seed on CICIDS2017. For every 2018 capture day separately:
    the warm-up window = that day's earliest ``max(windows)`` benign flows (arrival order); the
    evaluation set is drawn only from the *rest* of that day, so calibration and evaluation
    flows never overlap and the window always comes from the day it is applied to. This fixes
    the earlier protocol, whose single warm-up window came from the first day only.
    """
    feats = feature_columns(src)
    dst = dst[feats + [c for c in dst.columns if c not in feats]]
    windows = tuple(windows)
    records = []
    for seed in seeds:
        src_base = src[~src["family"].isin(RARE_NATURAL_UNKNOWN)]
        tr, va, _ = stratified_split(src_base, (0.85, 0.15, 0.0), seed)
        if held_out is not None:  # cross-dataset LOAFO (PR-04): the family is absent from every source split
            tr, va = tr[tr["family"] != held_out], va[va["family"] != held_out]
        train = cap_per_family(tr, _caps(tr, TRAIN_CAPS), seed)
        val = cap_per_family(va, _caps(va, VAL_CAPS), seed)
        t0 = time.time()
        scaler = SignedLogScaler().fit(train[feats].to_numpy())
        model = AegisOSR(seed=seed, alpha=alpha, ae_kwargs=ae_kwargs, **(model_kwargs or {}))
        model.fit(scaler.transform(train[feats].to_numpy()), train["family"].to_numpy(),
                  scaler.transform(val[feats].to_numpy()), val["family"].to_numpy(), log=log)
        fit_s = time.time() - t0
        base_state = model.snapshot()
        known_set = set(model.classes_) - {"BENIGN"}
        for day in sorted(dst["day"].astype(str).unique()):
            day_df = dst[dst["day"].astype(str) == day]
            warm, pool = _split_warmup(day_df, max(windows))
            test = _cap_keep_index(pool, _caps(pool, PERDAY_TEST_CAPS), seed).reset_index(drop=True)
            overlap = int(len(set(warm.index) & set(pool.index)))
            if on_split is not None:
                on_split({"protocol": protocol, "fold": day, "seed": seed,
                          "unknown": [held_out] if held_out else []},
                         {"train": train, "val": val, "test": test, "warmup": warm})
            fam = test["family"].astype(str).to_numpy()
            unknown = sorted(set(fam) - known_set - {"BENIGN"})
            groups = np.where(fam == "BENIGN", "benign", np.where(np.isin(fam, unknown), "unknown", "known"))
            Xte = scaler.transform(test[feats].to_numpy())
            model.restore(base_state)
            key = {"protocol": protocol, "fold": day if held_out is None else f"{held_out}@{day}", "seed": seed}
            methods, attribution, _ = _evaluate(model, Xte, fam, groups, alpha, dump, {**key, "variant": "none"})
            rec = {
                "protocol": protocol, "fold": key["fold"], "day": day, "held_out": held_out,
                "seed": seed, "alpha": alpha,
                "known_families": sorted(known_set), "unknown_families": unknown,
                "n_test": {g: int((groups == g).sum()) for g in ("benign", "known", "unknown")},
                "test_families": {f: int((fam == f).sum()) for f in sorted(set(fam))},
                "warmup_available": int(len(warm)), "warmup_eval_overlap": overlap,
                "methods": methods, "aegis_osr_attribution": attribution, "fit_seconds": round(fit_s, 1),
                "adaptation": {},
            }
            Xw = scaler.transform(warm.sort_values("seq")[feats].to_numpy())
            rec["screen"] = stream_screen(model.restore(base_state), Xw)
            for W in windows:
                if W > len(Xw):
                    continue
                for variant, upd in (("recal", False), ("recal+ref", True)):
                    model.restore(base_state).recalibrate(Xw[:W], update_reference=upd)
                    m_ad, a_ad, _ = _evaluate(model, Xte, fam, groups, alpha, dump,
                                              {**key, "variant": f"{variant}@{W}"})
                    rec["adaptation"][f"{variant}@{W}"] = {"window": W, "variant": variant, "methods": m_ad,
                                                           "aegis_osr_attribution": a_ad}
            model.restore(base_state)
            p = methods[PROPOSED]
            ad = rec["adaptation"].get("recal@2000", {}).get("methods", {}).get(PROPOSED, {})
            log(f"[{protocol}:{key['fold']}:s{seed}] n={rec['n_test']} FPR={p['fpr']:.4f} → recal@2000 "
                f"FPR={ad.get('fpr', float('nan')):.4f} ZDR={ad.get('zero_day_recall', float('nan'))}")
            records.append(rec)
    return records


def cross_loafo(src: pd.DataFrame, dst: pd.DataFrame, seeds: Iterable[int], families: Iterable[str] | None = None,
                log: Log = print, **kw) -> list[dict]:
    """Cross-dataset LOAFO (R3 amendment PR-04, RES-6): design-free unknown flows.

    For each family F present in both datasets: train on CICIDS2017 without F, then evaluate per
    CSE-CIC-IDS2018 day that contains F (independent per-day warm-up, as in ``cross_dataset_perday``).
    F's 2018 flows were never used as unknowns in any design decision.
    """
    fams = sorted(set(map(str, src["family"].unique())) & set(map(str, dst["family"].unique()))
                  - {"BENIGN", *RARE_NATURAL_UNKNOWN}) if families is None else list(families)
    records = []
    for f in fams:
        days = sorted(dst.loc[dst["family"].astype(str) == f, "day"].astype(str).unique())
        sub = dst[dst["day"].astype(str).isin(days)]
        records += cross_dataset_perday(src, sub, seeds, log=log, held_out=f, protocol="cross_loafo", **kw)
    return records


# --------------------------------------------------------------------------- aggregation
METRICS = [
    "zero_day_recall", "auroc_unknown", "auprc_unknown", "known_recall", "fpr", "auroc_all",
    "zero_day_recall@0.001", "zero_day_recall@0.05", "fpr@0.001", "fpr@0.05", "known_recall@0.05",
]


def _f(x) -> float:
    """JSON round-trips NaN as null; treat both as missing."""
    return float("nan") if x is None else float(x)


def _nanmean(values) -> float:
    arr = np.array([_f(v) for v in values], dtype=float)
    return float(np.nanmean(arr)) if np.isfinite(arr).any() else float("nan")


def _summarize_methods(recs: list[dict], getter) -> dict:
    """Overall (fold-averaged per seed, CI over seeds) + per-fold CI for one record view."""
    methods = list(getter(recs[0]).keys())
    folds = sorted({r["fold"] for r in recs})
    seeds = sorted({r["seed"] for r in recs})
    per_fold = {
        fold: {m: {k: mean_ci([_f(getter(r)[m].get(k)) for r in recs if r["fold"] == fold]) for k in METRICS}
               for m in methods}
        for fold in folds
    }
    overall = {
        m: {k: mean_ci([_nanmean([getter(r)[m].get(k) for r in recs if r["seed"] == s]) for s in seeds])
            for k in METRICS}
        for m in methods
    }
    return {"per_fold": per_fold, "overall": overall}


def summarize(records: list[dict]) -> dict:
    """Mean ± 95% CI per (protocol, fold, method) and per protocol overall, paired Wilcoxon
    tests of Aegis-OSR against every other method (pairs = fold × seed), per-family zero-day
    recall, open-set attribution, and warm-up adaptation results."""
    out: dict = {"per_fold": {}, "overall": {}, "significance": {}, "attribution": {},
                 "per_family": {}, "adaptation": {}}
    by_proto: dict[str, list[dict]] = {}
    for r in records:
        by_proto.setdefault(r["protocol"], []).append(r)
    for proto, recs in by_proto.items():
        base = _summarize_methods(recs, lambda r: r["methods"])
        out["per_fold"][proto] = base["per_fold"]
        out["overall"][proto] = base["overall"]
        methods = list(recs[0]["methods"].keys())
        folds = sorted({r["fold"] for r in recs})
        keyed = sorted(recs, key=lambda r: (r["fold"], r["seed"]))
        out["significance"][proto] = {
            k: {m: paired_test([_f(r["methods"][PROPOSED][k]) for r in keyed], [_f(r["methods"][m][k]) for r in keyed])
                for m in methods if m != PROPOSED}
            for k in ("zero_day_recall", "auroc_unknown", "fpr")
        }
        # Cite this one: fold-averaged per seed, paired over independent seeds.
        seeds = sorted({r["seed"] for r in recs})
        per_seed = lambda m, k: [_nanmean([r["methods"][m][k] for r in recs if r["seed"] == s]) for s in seeds]  # noqa: E731
        out.setdefault("significance_seed_level", {})[proto] = {
            k: {m: seed_level_test(per_seed(PROPOSED, k), per_seed(m, k)) for m in methods if m != PROPOSED}
            for k in ("zero_day_recall", "auroc_unknown", "fpr")
        }
        out["attribution"][proto] = {
            fold: {k: mean_ci([_f(r["aegis_osr_attribution"][k]) for r in recs if r["fold"] == fold])
                   for k in recs[0]["aegis_osr_attribution"]}
            for fold in folds
        }
        # zero-day recall per *unknown family* (e.g. which Friday families are caught)
        fam_vals: dict[str, dict[str, list[float]]] = {}
        for r in recs:
            for m in methods:
                for fam, v in (r["methods"][m].get("zero_day_recall_by_family") or {}).items():
                    fam_vals.setdefault(fam, {}).setdefault(m, []).append(_f(v))
        out["per_family"][proto] = {fam: {m: mean_ci(v) for m, v in d.items()} for fam, d in fam_vals.items()}

        keys = sorted({k for r in recs for k in (r.get("adaptation") or {})})
        if keys:
            adapt: dict = {}
            for key in keys:
                sub = [{**r, "methods": r["adaptation"][key]["methods"]} for r in recs if key in (r.get("adaptation") or {})]
                summ = _summarize_methods(sub, lambda r: r["methods"])
                first = next(r["adaptation"][key] for r in recs if key in (r.get("adaptation") or {}))
                adapt[key] = {"variant": first["variant"], "window": first["window"],
                              "per_fold": summ["per_fold"], "overall": summ["overall"]}
            out["adaptation"][proto] = adapt
    return out
