"""Pre-registered R3 analysis (docs/research/R3_AMENDMENT.md §3-§5): hypotheses A1-A7 and the reliability
study RS1/RS2, all from the campaign's per-flow score dumps.

    python scripts/74_r3_analysis.py --run campaign [--tag v1]

Steps
  1. score every dump file: matched-FPR TPR (threshold at exactly 1 % benign FPR, interpolated ROC), conformal
     recall / realised FPR with the smoothed p-values (primary) and the deterministic ones (sensitivity), and
     the raw-stream AUROCs needed by RS1;
  2. anchor: conformal metrics recomputed from the dumps must equal the run records (≤ 1e-6);
  3. confirmatory tests exactly as pre-registered (seed = unit, paired t primary, Wilcoxon sensitivity,
     Holm across models, hierarchical bootstrap folds/days -> seeds);
  4. reliability study (Spearman with day-cluster bootstrap) and the Phase 7 gate.

Outputs (never overwritten): research_artifacts/r3/analysis/<run>[_<tag>]/{rows.json, hypotheses.json,
reliability.json, MANIFEST.json}.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score, roc_curve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from research.artifact_guard import R3_DIR, assert_writable  # noqa: E402
from research.openset import PROPOSED  # noqa: E402

ALPHA = 0.01
TARGET_FPR = 0.01
BOOT = 10_000
BOOT_SEED = 20261122
MODELS = ["xgb_ref", "dt", "rf", "et", "xgb", "lgbm", "catboost"]
B = "Closed-set (sup only)"
F = PROPOSED
MAX = "Aegis-OSR w/ max fusion"
OMNI = "Aegis-OSR w/ omnibus fusion"
KNN = "kNN distance"
METHODS = [B, F, MAX, OMNI, KNN]
ADAPT = "recal@2000"
SCREEN_ALPHA0 = 0.05
TOST_MARGIN = 0.02


# ----------------------------------------------------------------------------- per-file metrics
def tpr_at(benign: np.ndarray, attack: np.ndarray, fpr: float = TARGET_FPR) -> float | None:
    if len(attack) == 0 or len(benign) == 0:
        return None
    f, t, _ = roc_curve(np.r_[np.zeros(len(benign)), np.ones(len(attack))], np.r_[benign, attack])
    return float(np.interp(fpr, f, t))


def auroc(benign: np.ndarray, attack: np.ndarray) -> float | None:
    if len(attack) == 0 or len(benign) == 0:
        return None
    return float(roc_auc_score(np.r_[np.zeros(len(benign)), np.ones(len(attack))], np.r_[benign, attack]))


def score_file(path: Path) -> tuple[dict, dict]:
    d = pd.read_parquet(path)
    g = d["group"].astype(str).to_numpy()
    masks = {"benign": g == "benign", "known": g == "known", "unknown": g == "unknown", "attack": g != "benign"}
    b = masks["benign"]
    out = {}
    for m in METHODS:
        s = d[f"fused__{m}"].to_numpy(float)
        p = d[f"p__{m}"].to_numpy(float)
        pdet = d[f"pdet__{m}"].to_numpy(float) if f"pdet__{m}" in d else None
        r = {"conformal_fpr": float((p[b] <= ALPHA).mean()),
             "conformal_fpr_det": None if pdet is None else float((pdet[b] <= ALPHA).mean())}
        for tgt in ("known", "unknown", "attack"):
            mk = masks[tgt]
            r[f"tpr_{tgt}"] = tpr_at(s[b], s[mk]) if mk.any() else None
            r[f"recall_{tgt}"] = float((p[mk] <= ALPHA).mean()) if mk.any() else None
            r[f"recall_{tgt}_det"] = (float((pdet[mk] <= ALPHA).mean()) if mk.any() and pdet is not None else None)
        out[m] = r
    streams = {}
    for c in ("raw_sup", "raw_knn"):
        if c in d:
            v = d[c].to_numpy(float)
            streams[c[4:]] = auroc(v[b], v[masks["attack"]]) if masks["attack"].any() else None
    return out, {"stream_auroc": streams, "n": {k: int(v.sum()) for k, v in masks.items()}}


def _model_runs(runs: list[Path]) -> dict[str, Path]:
    """Model -> the run directory holding its dumps (a model must appear in exactly one run)."""
    where: dict[str, Path] = {}
    for run in runs:
        for model in MODELS:
            if (run / "scores" / model / "manifest.json").exists():
                if model in where:
                    raise SystemExit(f"{model} appears in two runs: {where[model]} and {run}")
                where[model] = run
    return where


def collect(runs: list[Path]) -> tuple[list[dict], list[dict]]:
    rows, files = [], []
    for model, run in _model_runs(runs).items():
        man_path = run / "scores" / model / "manifest.json"
        man = json.loads(man_path.read_text(encoding="utf-8"))["files"]
        for rel, info in sorted(man.items()):
            path = run / "scores" / model / rel
            if hashlib.sha256(path.read_bytes()).hexdigest() != info["sha256"]:
                raise SystemExit(f"dump hash mismatch: {path}")
            res, extra = score_file(path)
            key = {"model": model, "protocol": info["protocol"], "fold": str(info["fold"]), "seed": int(info["seed"]),
                   "variant": info["variant"]}
            files.append({**key, **extra})
            for m, r in res.items():
                rows.append({**key, "method": m, **r})
    return rows, files


# ----------------------------------------------------------------------------- anchor
def anchor(runs: list[Path], rows: list[dict]) -> dict:
    idx = {(r["model"], r["protocol"], r["fold"], r["seed"], r["variant"], r["method"]): r for r in rows}
    checked, worst = 0, 0.0
    for model, run in _model_runs(runs).items():
        for rec_path in sorted(run.glob(f"*__{model}_records.json")):
            for rec in json.loads(rec_path.read_text(encoding="utf-8"))["records"]:
                blocks = {"none": rec["methods"], **{v: a["methods"] for v, a in (rec.get("adaptation") or {}).items()}}
                for v, methods in blocks.items():
                    for m in METHODS:
                        got = idx.get((model, rec["protocol"], str(rec["fold"]), int(rec["seed"]), v, m))
                        if got is None:
                            raise SystemExit(f"no dump for {model} {rec['protocol']} {rec['fold']} s{rec['seed']} {v}")
                        for a_key, b_key in (("fpr", "conformal_fpr"), ("known_recall", "recall_known"),
                                             ("zero_day_recall", "recall_unknown")):
                            want = methods[m].get(a_key)
                            if want is None or got[b_key] is None:
                                continue
                            worst = max(worst, abs(round(got[b_key], 6) - want))
                            checked += 1
    if checked == 0 or worst > 1e-6:
        raise SystemExit(f"anchor failed: checked={checked}, max abs diff={worst}")
    return {"values_checked": checked, "max_abs_diff": worst}


# ----------------------------------------------------------------------------- statistics helpers
def holm(ps: dict[str, float | None]) -> dict[str, float | None]:
    items = sorted(((k, p) for k, p in ps.items() if p is not None), key=lambda kv: kv[1])
    out: dict[str, float | None] = {k: None for k in ps}
    running = 0.0
    m = len(items)
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def diff_table(rows, model, protocol, variant, metric, a, b, other_model=None, fold_filter=None):
    """{fold: {seed: a - b}}; with other_model, a is ``model``'s method a and b is ``other_model``'s method a."""
    sel = {(r["model"], r["fold"], r["seed"], r["method"]): r for r in rows
           if r["protocol"] == protocol and r["variant"] == variant}
    out: dict[str, dict[int, float]] = {}
    for (mdl, fold, seed, meth), r in sel.items():
        if mdl != model or meth != a or (fold_filter and not fold_filter(fold)):
            continue
        rb = sel.get((other_model, fold, seed, a)) if other_model else sel.get((model, fold, seed, b))
        if rb is None or r[metric] is None or rb[metric] is None:
            continue
        out.setdefault(fold, {})[seed] = r[metric] - rb[metric]
    return out


def hier_boot(table: dict[str, dict[int, float]], rng) -> list[float] | None:
    if not table:
        return None
    vals = [np.array([table[g][s] for s in sorted(table[g])]) for g in table]
    est = np.empty(BOOT)
    for i in range(BOOT):
        gi = rng.integers(0, len(vals), len(vals))
        est[i] = np.mean([vals[j][rng.integers(0, len(vals[j]), len(vals[j]))].mean() for j in gi])
    return [float(np.quantile(est, 0.025)), float(np.quantile(est, 0.975))]


def summarise(table: dict[str, dict[int, float]], rng) -> dict:
    if not table:
        return {"n_seeds": 0}
    seeds = sorted({s for v in table.values() for s in v})
    per_seed = np.array([np.mean([table[f][s] for f in table if s in table[f]]) for s in seeds])
    per_fold = {f: float(np.mean(list(v.values()))) for f, v in table.items()}
    sd = per_seed.std(ddof=1) if len(per_seed) > 1 else 0.0
    t = stats.ttest_1samp(per_seed, 0.0) if len(per_seed) > 1 and sd > 0 else None
    w = stats.wilcoxon(per_seed) if len(per_seed) > 1 and np.any(per_seed != 0) else None
    return {
        "mean": float(per_seed.mean()), "sd_over_seeds": float(sd), "n_seeds": int(len(per_seed)),
        "per_seed": {str(s): float(v) for s, v in zip(seeds, per_seed)}, "per_fold": per_fold,
        "folds_positive": int(sum(v > 0 for v in per_fold.values())), "folds": len(per_fold),
        "t_p": None if t is None else float(t.pvalue), "wilcoxon_p": None if w is None else float(w.pvalue),
        "seed_ci95": (None if t is None else [float(per_seed.mean() + q * sd / np.sqrt(len(per_seed)))
                                              for q in stats.t.ppf([0.025, 0.975], len(per_seed) - 1)]),
        "hierarchical_bootstrap_95ci": hier_boot(table, rng),
    }


def tost_p(per_seed: np.ndarray, margin: float) -> float | None:
    """Two one-sided t-tests: equivalence within ±margin; returns the larger one-sided p."""
    if len(per_seed) < 2 or per_seed.std(ddof=1) == 0:
        return None
    lo = stats.ttest_1samp(per_seed, -margin, alternative="greater").pvalue
    hi = stats.ttest_1samp(per_seed, margin, alternative="less").pvalue
    return float(max(lo, hi))


def noninferior_p(per_seed: np.ndarray, margin: float) -> float | None:
    if len(per_seed) < 2 or per_seed.std(ddof=1) == 0:
        return None
    return float(stats.ttest_1samp(per_seed, -margin, alternative="greater").pvalue)


def count_verdict(results: dict, direction: str, need: int = 5, reject_at: int = 2, use_holm: bool = True) -> dict:
    sig = {m: r for m, r in results.items() if r.get("n_seeds")}
    ok = [m for m, r in sig.items() if (r["mean"] > 0 if direction == "pos" else r["mean"] < 0)
          and (not use_holm or (r.get("holm_p") is not None and r["holm_p"] < 0.05))]
    n_dir = sum(1 for r in sig.values() if (r["mean"] > 0 if direction == "pos" else r["mean"] < 0))
    verdict = ("supported" if len(ok) >= need else "rejected" if (len(ok) if use_holm else n_dir) <= reject_at
               else "inconclusive")
    return {"models_meeting_criterion": ok, "n_meeting": len(ok), "n_in_direction": n_dir, "n_models": len(sig),
            "verdict": verdict}


# ----------------------------------------------------------------------------- hypotheses
def hypotheses(rows: list[dict], rng) -> dict:
    out: dict = {}
    have = sorted({r["model"] for r in rows}, key=MODELS.index)

    def per_model(protocol, variant, metric, a, b, fold_filter=None):
        res = {m: summarise(diff_table(rows, m, protocol, variant, metric, a, b, fold_filter=fold_filter), rng)
               for m in have}
        hp = holm({m: r.get("t_p") for m, r in res.items()})
        for m in res:
            res[m]["holm_p"] = hp[m]
        return res

    # A1: LOAFO, Fisher - arm B, zero-day TPR at matched FPR
    a1 = per_model("loafo", "none", "tpr_unknown", F, B)
    out["A1"] = {"description": "LOAFO: Fisher - arm B zero-day TPR @ matched 1 % FPR", "per_model": a1,
                 **count_verdict(a1, "pos")}

    # A2: arm C Fisher, each model vs xgb_ref
    a2 = {}
    for m in [x for x in have if x != "xgb_ref"]:
        tab = diff_table(rows, m, "loafo", "none", "tpr_unknown", F, None, other_model="xgb_ref")
        s = summarise(tab, rng)
        if s.get("n_seeds"):
            s["tost_p"] = tost_p(np.array(list(s["per_seed"].values())), TOST_MARGIN)
        a2[m] = s
    hp = holm({m: r.get("t_p") for m, r in a2.items()})
    for m in a2:
        a2[m]["holm_p"] = hp[m]
    differs = [m for m, r in a2.items() if r.get("holm_p") is not None and r["holm_p"] < 0.05 and abs(r["mean"]) >= 0.03]
    equiv = [m for m, r in a2.items() if r.get("tost_p") is not None and r["tost_p"] < 0.05]
    out["A2"] = {"description": "LOAFO arm C (Fisher): model - xgb_ref zero-day TPR @ matched 1 % FPR",
                 "per_model": a2, "models_differing": differs, "models_equivalent": equiv,
                 "verdict": "supported" if differs else ("rejected" if a2 and len(equiv) == len(a2) else "inconclusive")}

    # A4: validity of smoothed conformal FPR under LOAFO
    a4 = {}
    for m in have:
        for meth in (B, F, MAX, OMNI):
            sel = [r for r in rows if r["model"] == m and r["protocol"] == "loafo" and r["variant"] == "none"
                   and r["method"] == meth]
            if not sel:
                continue
            seeds = sorted({r["seed"] for r in sel})
            per_seed = [np.mean([r["conformal_fpr"] for r in sel if r["seed"] == s]) for s in seeds]
            per_seed_det = [np.mean([r["conformal_fpr_det"] for r in sel if r["seed"] == s
                                     and r["conformal_fpr_det"] is not None] or [np.nan]) for s in seeds]
            mu = float(np.mean(per_seed))
            a4[f"{m} | {meth}"] = {"realised_fpr_smoothed": mu, "realised_fpr_deterministic": float(np.nanmean(per_seed_det)),
                                   "in_band": bool(0.008 <= mu <= 0.012)}
    fails = [k for k, v in a4.items() if not v["in_band"]]
    out["A4"] = {"description": "LOAFO realised FPR at alpha = 1 % (smoothed p), seed mean, band [0.8, 1.2] %",
                 "per_model_method": a4, "failures": fails,
                 "verdict": "supported" if not fails else "rejected",
                 "xgb_ref_failed": any(k.startswith("xgb_ref |") for k in fails)}

    # A5: cross_perday recal@2000, known TPR, Fisher - arm B
    a5 = per_model("cross_perday", ADAPT, "tpr_known", F, B)
    v5 = count_verdict(a5, "neg", use_holm=False)
    v5["verdict"] = ("supported" if v5["n_in_direction"] >= 5 else "rejected" if v5["n_in_direction"] <= 2
                     else "inconclusive")
    out["A5"] = {"description": "cross_perday recal@2000: Fisher - arm B known TPR @ matched 1 % FPR (direction count)",
                 "per_model": a5, **v5}

    # A6: cross_loafo recal@2000, held-out family TPR, Fisher - arm B (two-sided)
    a6 = per_model("cross_loafo", ADAPT, "tpr_unknown", F, B)
    pos, neg = count_verdict(a6, "pos"), count_verdict(a6, "neg")
    out["A6"] = {"description": "cross_loafo recal@2000: Fisher - arm B held-out-family TPR @ matched 1 % FPR",
                 "per_model": a6, "n_sig_positive": pos["n_meeting"], "n_sig_negative": neg["n_meeting"],
                 "verdict": ("LOAFO gain transfers" if pos["n_meeting"] >= 5 else
                             "reverses" if neg["n_meeting"] >= 5 else "setting- and model-dependent")}

    # A7: cross_perday recal@2000 known TPR: max fusion non-inferior to arm B (margin 0.02)
    a7 = {m: summarise(diff_table(rows, m, "cross_perday", ADAPT, "tpr_known", MAX, B), rng) for m in have}
    for m, r in a7.items():
        r["noninferiority_p"] = noninferior_p(np.array(list(r["per_seed"].values())), TOST_MARGIN) if r.get("n_seeds") else None
    ok = [m for m, r in a7.items() if r.get("noninferiority_p") is not None and r["noninferiority_p"] < 0.05]
    out["A7"] = {"description": "cross_perday recal@2000: max fusion - arm B known TPR, non-inferiority margin 0.02",
                 "per_model": a7, "models_noninferior": ok,
                 "verdict": "supported" if len(ok) >= 5 else "rejected" if len(ok) <= 2 else "inconclusive"}

    # exploratory (no confirmatory claims)
    expl = {}
    for proto, var, metric in (("temporal", "none", "tpr_unknown"), ("temporal", "none", "tpr_known"),
                               ("temporal", ADAPT, "tpr_unknown"), ("temporal", ADAPT, "tpr_known"),
                               ("cross_perday", "none", "tpr_known"), ("cross_perday", "recal+ref@2000", "tpr_known"),
                               ("cross_loafo", "none", "tpr_unknown"), ("cross_loafo", "recal+ref@2000", "tpr_unknown"),
                               ("loafo", "none", "recall_unknown")):
            for a, label in ((F, "fisher_minus_B"), (MAX, "max_minus_B")):
                key = f"{proto} | {var} | {metric} | {label}"
                expl[key] = {m: summarise(diff_table(rows, m, proto, var, metric, a, B), rng) for m in have}
    out["exploratory"] = expl
    return out


# ----------------------------------------------------------------------------- reliability study
def spearman_cluster(x, y, clusters, rng) -> dict:
    x, y, clusters = np.asarray(x, float), np.asarray(y, float), np.asarray(clusters)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y, clusters = x[ok], y[ok], clusters[ok]
    if len(x) < 4 or np.all(x == x[0]) or np.all(y == y[0]):
        return {"n": int(len(x)), "rho": None}
    rho = float(stats.spearmanr(x, y).statistic)
    uniq = np.unique(clusters)
    idx = {c: np.flatnonzero(clusters == c) for c in uniq}
    est = []
    for _ in range(2000):
        pick = np.concatenate([idx[c] for c in rng.choice(uniq, len(uniq))])
        if np.all(x[pick] == x[pick][0]) or np.all(y[pick] == y[pick][0]):
            continue
        est.append(stats.spearmanr(x[pick], y[pick]).statistic)
    ci = [float(np.quantile(est, 0.025)), float(np.quantile(est, 0.975))] if est else None
    return {"n": int(len(x)), "clusters": int(len(uniq)), "rho": rho, "day_cluster_ci95": ci}


def rs_verdict(r: dict) -> str:
    if r.get("rho") is None:
        return "not computable"
    if r["rho"] <= -0.5 and r["day_cluster_ci95"] and r["day_cluster_ci95"][1] < 0:
        return "supported"
    if abs(r["rho"]) < 0.3:
        return "rejected"
    return "inconclusive"


def reliability(runs: list[Path], rows: list[dict], files: list[dict], rng) -> dict:
    screens = {}
    for model, run in _model_runs(runs).items():
        for proto in ("cross_perday", "cross_loafo"):
            p = run / f"{proto}__{model}_records.json"
            if not p.exists():
                continue
            for rec in json.loads(p.read_text(encoding="utf-8"))["records"]:
                ex = (rec.get("screen") or {}).get("exceedance", {})
                screens[(model, proto, str(rec["fold"]), int(rec["seed"]))] = {**ex, "day": rec.get("day", rec["fold"])}
    fidx = {(f["model"], f["protocol"], f["fold"], f["seed"], f["variant"]): f for f in files}

    # RS1: e_j vs stream target AUROC (variant none). kNN counted once per (protocol, fold, seed) via xgb_ref.
    xs, ys, cl, kinds = [], [], [], []
    for (model, proto, fold, seed), ex in screens.items():
        f = fidx.get((model, proto, fold, seed, "none"))
        if f is None:
            continue
        if "sup" in ex and f["stream_auroc"].get("sup") is not None:
            xs.append(ex["sup"]); ys.append(f["stream_auroc"]["sup"]); cl.append(ex["day"]); kinds.append("sup")
        if model == "xgb_ref" and "knn" in ex and f["stream_auroc"].get("knn") is not None:
            xs.append(ex["knn"]); ys.append(f["stream_auroc"]["knn"]); cl.append(ex["day"]); kinds.append("knn")
    kinds = np.array(kinds)
    rs1 = spearman_cluster(xs, ys, cl, rng)
    rs1["by_stream"] = {k: spearman_cluster(np.array(xs)[kinds == k], np.array(ys)[kinds == k],
                                            np.array(cl)[kinds == k], rng) for k in ("sup", "knn")}
    rs1["verdict"] = rs_verdict(rs1)

    # RS2: e_knn vs Fisher - arm B TPR on all attacks at recal@2000
    ridx = {(r["model"], r["protocol"], r["fold"], r["seed"], r["variant"], r["method"]): r for r in rows}
    x2, y2, c2 = [], [], []
    for (model, proto, fold, seed), ex in screens.items():
        rf, rb = ridx.get((model, proto, fold, seed, ADAPT, F)), ridx.get((model, proto, fold, seed, ADAPT, B))
        if rf is None or rb is None or rf["tpr_attack"] is None or rb["tpr_attack"] is None or "knn" not in ex:
            continue
        x2.append(ex["knn"]); y2.append(rf["tpr_attack"] - rb["tpr_attack"]); c2.append(ex["day"])
    rs2 = spearman_cluster(x2, y2, c2, rng)
    rs2["verdict"] = rs_verdict(rs2)

    gate_open = rs1["verdict"] == "supported" and rs2["verdict"] == "supported"
    screen_summary = {}
    for (model, proto, fold, seed), ex in screens.items():
        if model == "xgb_ref":
            screen_summary.setdefault(f"{proto} | {fold}", []).append(ex.get("knn"))
    return {
        "RS1": rs1, "RS2": rs2,
        "phase7_gate": {"open": gate_open,
                        "rule": "build the gated method only if RS1 and RS2 are both supported (R3_AMENDMENT §5)"},
        "knn_screen_by_fold_xgb_ref": {k: float(np.mean([v for v in vs if v is not None])) for k, vs in screen_summary.items()},
        "screen_alpha0": SCREEN_ALPHA0,
    }


# ----------------------------------------------------------------------------- main
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", nargs="+", default=["campaign"], help="one or more run directories under r3/runs")
    ap.add_argument("--name", default=None, help="analysis name (default: the run names joined by '+')")
    ap.add_argument("--tag", default=None)
    a = ap.parse_args()
    run = [R3_DIR / "runs" / r for r in a.run]
    name = a.name or "+".join(a.run)
    out = R3_DIR / "analysis" / (name + (f"_{a.tag}" if a.tag else ""))
    if out.exists():
        raise SystemExit(f"{out} exists; analysis outputs are never overwritten (use --tag)")
    rows, files = collect(run)
    if not rows:
        raise SystemExit(f"no score dumps under {run}")
    anc = anchor(run, rows)
    print(f"anchor: {anc['values_checked']} values, max diff {anc['max_abs_diff']:.2e}")
    rng = np.random.default_rng(BOOT_SEED)
    hyp = hypotheses(rows, rng)
    rel = reliability(run, rows, files, rng)
    out.mkdir(parents=True)
    meta = {"runs": a.run, "generated": datetime.now(timezone.utc).isoformat(),
            "git_commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip(),
            "preregistration": "docs/research/R3_AMENDMENT.md", "alpha": ALPHA, "target_fpr": TARGET_FPR,
            "bootstrap": {"replicates": BOOT, "seed": BOOT_SEED}, "anchor": anc,
            "models": sorted({r["model"] for r in rows}, key=MODELS.index),
            "protocols": sorted({r["protocol"] for r in rows}), "seeds": sorted({r["seed"] for r in rows})}
    payloads = {"rows.json": {"meta": meta, "rows": rows, "files": files},
                "hypotheses.json": {"meta": meta, **hyp}, "reliability.json": {"meta": meta, **rel}}
    for name, body in payloads.items():
        p = out / name
        assert_writable(p)
        p.write_text(json.dumps(body, indent=1, default=float), encoding="utf-8")
    (out / "MANIFEST.json").write_text(json.dumps({"files": {n: sha256(out / n) for n in payloads}, **meta}, indent=1),
                                       encoding="utf-8")
    for h in ("A1", "A2", "A4", "A5", "A6", "A7"):
        print(h, hyp[h]["verdict"], "|", hyp[h]["description"])
        for m, r in (hyp[h].get("per_model") or {}).items():
            if r.get("n_seeds"):
                print(f"   {m:9s} mean={r['mean']:+.3f} t_p={r.get('t_p')} holm={r.get('holm_p')} "
                      f"hb={r.get('hierarchical_bootstrap_95ci')}")
    print("A4 failures:", hyp["A4"]["failures"])
    print("RS1", rel["RS1"]["verdict"], rel["RS1"].get("rho"), rel["RS1"].get("day_cluster_ci95"))
    print("RS2", rel["RS2"]["verdict"], rel["RS2"].get("rho"), rel["RS2"].get("day_cluster_ci95"))
    print("Phase 7 gate open:", rel["phase7_gate"]["open"])
    print("->", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
