"""Phase 2 matched-FPR re-analysis of the EXISTING per-flow score dumps (E-04, E-05). No training, no new scoring.

    python scripts/72_matched_fpr_reanalysis.py

Inputs (read only; produced by the R3 Stage-0 regression gate, which reproduced the committed records exactly):
  research_artifacts/r3/regression/scores/{loafo,cross_perday}/...   per-flow scores for every method
  research_artifacts/r3/regression/{loafo,cross_perday}_records.json  committed metrics (reproduction anchor)
  research_artifacts/openset_temporal_records.json                     temporal records (no dumps exist)

Why (docs/research/ML_PIPELINE_AUDIT.md):
  RES-2  tree models with tied scores realise FPR far below alpha, so "recall at alpha" compares unequal FPRs.
  RES-3  the paper quoted closed-set XGB only on the two 2018 days where it is best.
  RES-4  "the fusion inversion is specific to cross-network" was not checked at matched FPR.
  RES-7  CIs covered seed variance only; day- and family-level variation was not summarised.
  RES-22 AUROC hides operating-point failures; TPR at 1 % FPR is reported instead.

Two operating points per (fold, seed, variant, method):
  * conformal: alert iff p <= 0.01, exactly as deployed. Reproduces the committed records (anchor, asserted).
  * matched:   TPR at a realised FPR of exactly 1 % on the evaluated benign flows (ROC interpolation, i.e.
               randomised tie-breaking). This is an ORACLE ranking comparison: the threshold is set on the test
               benign flows, so it is not an operational result. It answers "which score ranks attacks better at
               equal false alarms", which is the comparison RES-2/3/4 need.

Outputs (new, versioned, refuse to overwrite):
  research_artifacts/reanalysis/matched_fpr_rows.json        one row per (protocol, fold, seed, variant, method)
  research_artifacts/reanalysis/matched_fpr_summary.json     per-day / per-family tables, seed-, day- and family-level
                                                             statistics, hierarchical bootstrap, temporal (records)
  research_artifacts/reanalysis/MANIFEST.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402
from sklearn.metrics import roc_auc_score, roc_curve  # noqa: E402

from research.artifact_guard import assert_writable  # noqa: E402

REG = ROOT / "research_artifacts" / "r3" / "regression"
OUT = ROOT / "research_artifacts" / "reanalysis"
ALPHA = 0.01
TARGET_FPR = 0.01
BOOT = 10000
BOOT_SEED = 20261118
METHODS = ["Closed-set XGB", "Closed-set DT (v1.1-style)", "XGB + Energy", "kNN distance", "Isolation Forest",
           "Autoencoder", "Aegis-OSR", "Aegis-OSR w/ max fusion", "Aegis-OSR w/ omnibus fusion",
           "Aegis-OSR w/ AE novelty", "Aegis-OSR w/ IForest novelty"]
FOCUS = ["Closed-set XGB", "Aegis-OSR w/ max fusion", "Aegis-OSR"]  # XGB alone / max fusion / Fisher fusion
ANCHOR_TOL = 1e-6


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tpr_at(benign: np.ndarray, attack: np.ndarray, fpr: float) -> float | None:
    if len(attack) == 0:
        return None
    y = np.r_[np.zeros(len(benign)), np.ones(len(attack))]
    f, t, _ = roc_curve(y, np.r_[benign, attack])
    return float(np.interp(fpr, f, t))


def auroc(benign: np.ndarray, attack: np.ndarray) -> float | None:
    if len(attack) == 0:
        return None
    return float(roc_auc_score(np.r_[np.zeros(len(benign)), np.ones(len(attack))], np.r_[benign, attack]))


def score_file(path: Path) -> dict[str, dict]:
    cols = ["group"] + [c for m in METHODS for c in (f"fused__{m}", f"p__{m}")]
    d = pd.read_parquet(path, columns=cols)
    g = d["group"].to_numpy()
    b, k, u = g == "benign", g == "known", g == "unknown"
    out = {}
    for m in METHODS:
        s = d[f"fused__{m}"].to_numpy(dtype=float)
        p = d[f"p__{m}"].to_numpy(dtype=float)
        alert = p <= ALPHA
        out[m] = {
            "conformal_fpr": float(alert[b].mean()),
            "conformal_known_recall": float(alert[k].mean()) if k.any() else None,
            "conformal_unknown_recall": float(alert[u].mean()) if u.any() else None,
            "tpr_known@1%fpr": tpr_at(s[b], s[k], TARGET_FPR),
            "tpr_unknown@1%fpr": tpr_at(s[b], s[u], TARGET_FPR),
            "auroc_known": auroc(s[b], s[k]),
            "auroc_unknown": auroc(s[b], s[u]),
        }
    return out


def rows_for(protocol: str) -> list[dict]:
    man = json.loads((REG / "scores" / protocol / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    for rel, info in sorted(man["files"].items()):
        res = score_file(REG / "scores" / protocol / rel)
        for m, r in res.items():
            rows.append({"protocol": protocol, "fold": info["fold"], "seed": int(info["seed"]),
                         "variant": info["variant"], "method": m, **r})
    return rows


def anchor(rows: list[dict]) -> dict:
    """Conformal metrics recomputed from the dumps must equal the committed regression records."""
    checked, worst = 0, 0.0
    for protocol in ("loafo", "cross_perday"):
        recs = json.loads((REG / f"{protocol}_records.json").read_text(encoding="utf-8"))["records"]
        for rec in recs:
            blocks = {"none": rec["methods"]}
            for v, a in (rec.get("adaptation") or {}).items():
                blocks[v] = a["methods"]
            for v, methods in blocks.items():
                for m in FOCUS + ["Closed-set DT (v1.1-style)"]:
                    want = methods[m]
                    got = next(r for r in rows if r["protocol"] == protocol and r["fold"] == rec["fold"]
                               and r["seed"] == rec["seed"] and r["variant"] == v and r["method"] == m)
                    pairs = [("fpr", "conformal_fpr"), ("known_recall", "conformal_known_recall"),
                             ("zero_day_recall", "conformal_unknown_recall")]
                    for a_key, b_key in pairs:
                        if want.get(a_key) is None or got[b_key] is None:
                            continue
                        worst = max(worst, abs(round(got[b_key], 6) - want[a_key]))
                        checked += 1
    ok = worst <= ANCHOR_TOL
    if not ok:
        raise SystemExit(f"anchor failed: dumps do not reproduce records (max abs diff {worst})")
    return {"values_checked": checked, "max_abs_diff": worst, "reproduced": ok,
            "note": "records round to 6 decimals; dumps recomputed with p <= alpha"}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def hier_boot(table: dict[str, dict[int, float]], rng: np.random.Generator) -> list[float]:
    """Two-level bootstrap: resample groups (days / families), then seeds within each group."""
    groups = list(table)
    vals = [np.array([table[g][s] for s in sorted(table[g])]) for g in groups]
    est = np.empty(BOOT)
    for i in range(BOOT):
        gi = rng.integers(0, len(groups), len(groups))
        est[i] = np.mean([vals[j][rng.integers(0, len(vals[j]), len(vals[j]))].mean() for j in gi])
    return [float(np.quantile(est, 0.025)), float(np.quantile(est, 0.975))]


def paired(rows: list[dict], protocol: str, variant: str, metric: str, a: str, b: str, rng) -> dict:
    """Difference a - b in `metric`, summarised at seed level, group level and with a hierarchical bootstrap."""
    sel = [r for r in rows if r["protocol"] == protocol and r["variant"] == variant]
    folds = sorted({r["fold"] for r in sel})
    seeds = sorted({r["seed"] for r in sel})
    diff: dict[str, dict[int, float]] = {}
    for f in folds:
        for s in seeds:
            ra = next(r for r in sel if r["fold"] == f and r["seed"] == s and r["method"] == a)
            rb = next(r for r in sel if r["fold"] == f and r["seed"] == s and r["method"] == b)
            if ra[metric] is None or rb[metric] is None:
                continue
            diff.setdefault(f, {})[s] = ra[metric] - rb[metric]
    if not diff:
        return {}
    per_group = {f: float(np.mean(list(v.values()))) for f, v in diff.items()}
    per_seed = {s: float(np.mean([diff[f][s] for f in diff if s in diff[f]])) for s in seeds}
    sv = np.array(list(per_seed.values()))
    gv = np.array(list(per_group.values()))
    t = stats.ttest_1samp(sv, 0.0) if len(sv) > 1 and sv.std() > 0 else None
    w = stats.wilcoxon(gv) if len(gv) > 1 and np.any(gv != 0) else None
    return {
        "a": a, "b": b, "metric": metric, "variant": variant,
        "mean": float(sv.mean()),
        "per_group_mean_over_seeds": per_group,
        "groups_a_better": int((gv > 0).sum()), "groups_b_better": int((gv < 0).sum()), "groups": int(len(gv)),
        "per_seed_mean_over_groups": {str(k): v for k, v in per_seed.items()},
        "seeds_a_better": int((sv > 0).sum()), "seeds": int(len(sv)),
        "seed_level_paired_t_p": (float(t.pvalue) if t is not None else None),
        "group_level_wilcoxon_p": (float(w.pvalue) if w is not None else None),
        "hierarchical_bootstrap_95ci": hier_boot(diff, rng),
        "statistics_note": "seed-level test: groups share the trained model within a seed, so only seeds are "
                           "independent replicates; group-level Wilcoxon and the hierarchical bootstrap (groups, then "
                           "seeds) describe how far the effect generalises across days/families. Unadjusted p-values.",
    }


def per_group_table(rows, protocol, variant, metrics) -> dict:
    sel = [r for r in rows if r["protocol"] == protocol and r["variant"] == variant and r["method"] in FOCUS
           + ["Closed-set DT (v1.1-style)", "kNN distance", "XGB + Energy"]]
    out: dict = {}
    for r in sel:
        out.setdefault(r["fold"], {}).setdefault(r["method"], []).append(r)
    return {f: {m: {k: mean([x[k] for x in xs]) for k in metrics} for m, xs in ms.items()} for f, ms in out.items()}


def temporal_from_records() -> dict:
    """RES-4 support: temporal records (no per-flow dumps exist). Seed-level Aegis-OSR minus XGB."""
    recs = json.loads((ROOT / "research_artifacts" / "openset_temporal_records.json").read_text(encoding="utf-8"))["records"]
    out = {}
    for fold in sorted({r["fold"] for r in recs}):
        fr = [r for r in recs if r["fold"] == fold]
        blocks = {"none": [r["methods"] for r in fr]}
        for v in fr[0].get("adaptation") or {}:
            blocks[v] = [r["adaptation"][v]["methods"] for r in fr]
        res = {}
        for v, ms in blocks.items():
            row = {}
            for metric in ("zero_day_recall", "known_recall", "fpr"):
                a = [m["Aegis-OSR"].get(metric) for m in ms]
                b = [m["Closed-set XGB"].get(metric) for m in ms]
                if any(x is None for x in a + b):
                    continue
                d = np.array(a) - np.array(b)
                row[metric] = {"aegis_mean": float(np.mean(a)), "xgb_mean": float(np.mean(b)),
                               "diff_mean": float(d.mean()), "seeds_aegis_better": int((d > 0).sum()), "seeds": len(d),
                               "paired_t_p": (float(stats.ttest_1samp(d, 0).pvalue) if d.std() > 0 else None)}
            res[v] = row
        out[fold] = res
    return {"source": "research_artifacts/openset_temporal_records.json", "per_fold": out,
            "note": "conformal operating point only; rows with unequal realised FPR must be read with the fpr row. "
                    "The oracle@W variants re-target the threshold on target benign flows."}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    targets = {n: OUT / n for n in ("matched_fpr_rows.json", "matched_fpr_summary.json", "MANIFEST.json")}
    for p in targets.values():
        assert_writable(p)
        if p.exists():
            raise SystemExit(f"refusing to overwrite existing result {p.relative_to(ROOT)}")

    rows = rows_for("loafo") + rows_for("cross_perday")
    anc = anchor(rows)
    rng = np.random.default_rng(BOOT_SEED)
    metrics = ["conformal_fpr", "conformal_known_recall", "conformal_unknown_recall", "tpr_known@1%fpr",
               "tpr_unknown@1%fpr", "auroc_known", "auroc_unknown"]

    loafo = {
        "per_family_mean_over_seeds": per_group_table(rows, "loafo", "none", metrics),
        "aegis_vs_xgb_unknown_conformal": paired(rows, "loafo", "none", "conformal_unknown_recall", "Aegis-OSR", "Closed-set XGB", rng),
        "aegis_vs_xgb_unknown_matched": paired(rows, "loafo", "none", "tpr_unknown@1%fpr", "Aegis-OSR", "Closed-set XGB", rng),
        "aegis_vs_max_unknown_matched": paired(rows, "loafo", "none", "tpr_unknown@1%fpr", "Aegis-OSR", "Aegis-OSR w/ max fusion", rng),
        "aegis_vs_dt_unknown_conformal": paired(rows, "loafo", "none", "conformal_unknown_recall", "Aegis-OSR", "Closed-set DT (v1.1-style)", rng),
        "aegis_vs_dt_unknown_matched": paired(rows, "loafo", "none", "tpr_unknown@1%fpr", "Aegis-OSR", "Closed-set DT (v1.1-style)", rng),
    }
    per_day = {}
    for v in ("none", "recal@2000", "recal@5000", "recal+ref@2000"):
        per_day[v] = {
            "per_day_mean_over_seeds": per_group_table(rows, "cross_perday", v, metrics),
            "aegis_vs_xgb_known_conformal": paired(rows, "cross_perday", v, "conformal_known_recall", "Aegis-OSR", "Closed-set XGB", rng),
            "aegis_vs_xgb_known_matched": paired(rows, "cross_perday", v, "tpr_known@1%fpr", "Aegis-OSR", "Closed-set XGB", rng),
            "max_vs_xgb_known_matched": paired(rows, "cross_perday", v, "tpr_known@1%fpr", "Aegis-OSR w/ max fusion", "Closed-set XGB", rng),
            "aegis_vs_max_known_matched": paired(rows, "cross_perday", v, "tpr_known@1%fpr", "Aegis-OSR", "Aegis-OSR w/ max fusion", rng),
        }
    stamp = {"generated_at": datetime.now(timezone.utc).isoformat(), "version": 1,
             "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}
    summary = {
        **stamp,
        "status": "re-analysis of existing per-flow scores; descriptive. Matched-FPR numbers are oracle ranking "
                  "comparisons (threshold set on the evaluated benign flows), not operational results.",
        "alpha": ALPHA, "target_fpr": TARGET_FPR, "bootstrap": {"replicates": BOOT, "seed": BOOT_SEED},
        "reproduction_anchor": anc,
        "loafo": loafo,
        "cross_perday": per_day,
        "temporal_records": temporal_from_records(),
    }
    for name, obj in (("matched_fpr_rows.json", {**stamp, "rows": rows}), ("matched_fpr_summary.json", summary)):
        assert_writable(targets[name])
        targets[name].write_text(json.dumps(obj, indent=1), encoding="utf-8")
    inputs = [REG / "loafo_records.json", REG / "cross_perday_records.json",
              REG / "scores" / "loafo" / "manifest.json", REG / "scores" / "cross_perday" / "manifest.json",
              ROOT / "research_artifacts" / "openset_temporal_records.json"]
    man = {**stamp, "script": "scripts/72_matched_fpr_reanalysis.py",
           "inputs": {p.relative_to(ROOT).as_posix(): sha256(p) for p in inputs},
           "outputs": {targets[n].relative_to(ROOT).as_posix(): sha256(targets[n]) for n in targets if n != "MANIFEST.json"}}
    targets["MANIFEST.json"].write_text(json.dumps(man, indent=2), encoding="utf-8")

    print("anchor", anc)
    for k, v in loafo.items():
        if k != "per_family_mean_over_seeds":
            print("LOAFO", k, round(v["mean"], 4), v["hierarchical_bootstrap_95ci"], f'{v["seeds_a_better"]}/{v["seeds"]} seeds',
                  f'{v["groups_a_better"]}/{v["groups"]} fams')
    for var, blk in per_day.items():
        for k, v in blk.items():
            if k != "per_day_mean_over_seeds" and v:
                print("PERDAY", var, k, round(v["mean"], 4), [round(x, 3) for x in v["hierarchical_bootstrap_95ci"]],
                      f'{v["seeds_a_better"]}/{v["seeds"]} seeds', f'{v["groups_a_better"]}-{v["groups_b_better"]}/{v["groups"]} days')


if __name__ == "__main__":
    main()
