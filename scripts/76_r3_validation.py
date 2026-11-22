"""Phase 8: robustness validation of the pre-registered R3 findings (the Phase 7 gate stayed closed).

    python scripts/76_r3_validation.py [--analysis campaign]

Reads only the R3 analysis outputs (scripts/74) and the Phase 2 re-analysis; trains nothing. Checks:
  V1  leave-one-fold-out: each confirmatory hypothesis (A1, A5, A6, A7) re-decided with its rule after dropping
      each held-out family / day in turn — does any single fold drive the verdict?
  V2  replication: the xgb_ref LOAFO matched-FPR gain on the new seeds (101-105) vs the Phase 2 re-analysis
      on seeds 1-5 (research_artifacts/reanalysis/matched_fpr_summary.json);
  V3  p-value rule: realised FPR and conformal-recall effects under the smoothed (primary) and deterministic rule;
  V4  metric agreement: the sign of each A1/A5 effect under matched-FPR TPR vs conformal recall at alpha = 1 %;
  V5  2018-02-21 (the anomalous-benign day, see the paper) excluded from A5.

All of this is post hoc robustness analysis of pre-registered hypotheses; it changes no verdict.
Output: research_artifacts/r3/validation/<analysis>_validation.json (never overwritten).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

_spec = importlib.util.spec_from_file_location("r3a", ROOT / "scripts" / "74_r3_analysis.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

ANOMALY_DAY = "2018-02-21"
RULES = {  # hypothesis -> (protocol, variant, metric, method a, method b, direction, use_holm, kind)
    "A1": ("loafo", "none", "tpr_unknown", A.F, A.B, "pos", True, "count"),
    "A5": ("cross_perday", A.ADAPT, "tpr_known", A.F, A.B, "neg", False, "count"),
    "A6": ("cross_loafo", A.ADAPT, "tpr_unknown", A.F, A.B, None, True, "a6"),
    "A7": ("cross_perday", A.ADAPT, "tpr_known", A.MAX, A.B, None, False, "noninf"),
}


def seed_stats(table: dict) -> dict:
    from scipy import stats

    seeds = sorted({s for v in table.values() for s in v})
    ps = np.array([np.mean([table[f][s] for f in table if s in table[f]]) for s in seeds])
    t = stats.ttest_1samp(ps, 0.0) if len(ps) > 1 and ps.std(ddof=1) > 0 else None
    return {"mean": float(ps.mean()), "per_seed": ps, "t_p": None if t is None else float(t.pvalue)}


def decide(hyp: str, tables: dict[str, dict]) -> dict:
    _, _, _, _, _, direction, use_holm, kind = RULES[hyp]
    res = {m: seed_stats(t) for m, t in tables.items() if t}
    hp = A.holm({m: r["t_p"] for m, r in res.items()})
    means = {m: round(r["mean"], 4) for m, r in res.items()}
    if kind == "count":
        ok = [m for m, r in res.items() if (r["mean"] > 0 if direction == "pos" else r["mean"] < 0)
              and (not use_holm or (hp[m] is not None and hp[m] < 0.05))]
        n_dir = sum((r["mean"] > 0 if direction == "pos" else r["mean"] < 0) for r in res.values())
        verdict = "supported" if len(ok) >= 5 else "rejected" if (len(ok) if use_holm else n_dir) <= 2 else "inconclusive"
        return {"verdict": verdict, "n_meeting": len(ok), "means": means}
    if kind == "a6":
        pos = sum(r["mean"] > 0 and hp[m] is not None and hp[m] < 0.05 for m, r in res.items())
        neg = sum(r["mean"] < 0 and hp[m] is not None and hp[m] < 0.05 for m, r in res.items())
        verdict = "LOAFO gain transfers" if pos >= 5 else "reverses" if neg >= 5 else "setting- and model-dependent"
        return {"verdict": verdict, "n_sig_positive": int(pos), "n_sig_negative": int(neg), "means": means}
    ok = [m for m, r in res.items() if (p := A.noninferior_p(r["per_seed"], A.TOST_MARGIN)) is not None and p < 0.05]
    return {"verdict": "supported" if len(ok) >= 5 else "rejected" if len(ok) <= 2 else "inconclusive",
            "n_noninferior": len(ok), "means": means}


def tables_for(rows, hyp: str, models, metric: str | None = None, fold_filter=None) -> dict[str, dict]:
    proto, variant, met, a, b, *_ = RULES[hyp]
    return {m: A.diff_table(rows, m, proto, variant, metric or met, a, b, fold_filter=fold_filter) for m in models}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", default="campaign")
    a = ap.parse_args()
    src = ROOT / "research_artifacts" / "r3" / "analysis" / a.analysis
    out = ROOT / "research_artifacts" / "r3" / "validation" / f"{a.analysis}_validation.json"
    if out.exists():
        raise SystemExit(f"{out.relative_to(ROOT)} exists; validation outputs are never overwritten")
    rows = json.loads((src / "rows.json").read_text(encoding="utf-8"))["rows"]
    hyp = json.loads((src / "hypotheses.json").read_text(encoding="utf-8"))
    models = [m for m in A.MODELS if any(r["model"] == m for r in rows)]
    rep: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "analysis": a.analysis,
                 "status": "post hoc robustness of pre-registered hypotheses; descriptive, changes no verdict"}

    # V1 leave-one-fold-out
    v1 = {}
    for h in RULES:
        full = tables_for(rows, h, models)
        folds = sorted({f for t in full.values() for f in t})
        per_drop = {}
        for f in folds:
            per_drop[f] = decide(h, {m: {k: v for k, v in t.items() if k != f} for m, t in full.items()})
        verdicts = {d["verdict"] for d in per_drop.values()}
        v1[h] = {"preregistered_verdict": hyp[h]["verdict"], "recomputed_full": decide(h, full)["verdict"],
                 "drop_one": {f: {k: v for k, v in d.items() if k != "means"} for f, d in per_drop.items()},
                 "verdict_stable": verdicts == {hyp[h]["verdict"]}, "verdicts_seen": sorted(verdicts)}
        print(f"V1 {h}: pre-registered={hyp[h]['verdict']} stable={v1[h]['verdict_stable']} seen={sorted(verdicts)}")
    rep["V1_leave_one_fold_out"] = v1

    # V2 replication of the Phase 2 xgb LOAFO gain on new seeds
    p2 = json.loads((ROOT / "research_artifacts" / "reanalysis" / "matched_fpr_summary.json").read_text(encoding="utf-8"))
    old = p2["loafo"]["aegis_vs_xgb_unknown_matched"]
    new = hyp["A1"]["per_model"]["xgb_ref"]
    rep["V2_replication"] = {
        "phase2_seeds_1_5": {"mean": old["mean"], "hierarchical_bootstrap_95ci": old["hierarchical_bootstrap_95ci"],
                             "source": "research_artifacts/reanalysis/matched_fpr_summary.json:loafo.aegis_vs_xgb_unknown_matched"},
        "r3_seeds_101_105": {"mean": new["mean"], "hierarchical_bootstrap_95ci": new["hierarchical_bootstrap_95ci"],
                             "source": f"research_artifacts/r3/analysis/{a.analysis}/hypotheses.json:A1.per_model.xgb_ref"},
        "difference": new["mean"] - old["mean"],
        "new_mean_inside_old_ci": old["hierarchical_bootstrap_95ci"][0] <= new["mean"] <= old["hierarchical_bootstrap_95ci"][1],
        "per_family": {f: {"phase2": old["per_group_mean_over_seeds"].get(f), "r3": v} for f, v in new["per_fold"].items()},
    }
    print(f"V2 xgb_ref LOAFO gain: phase2 {old['mean']:+.3f} -> R3 {new['mean']:+.3f}")

    # V3 p-value rule sensitivity
    a4 = hyp["A4"]["per_model_method"]
    v3 = {"realised_fpr": a4,
          "largest_gap": max(a4.items(), key=lambda kv: abs(kv[1]["realised_fpr_smoothed"] - kv[1]["realised_fpr_deterministic"]))[0]}
    conf = {}
    for rule, met in (("smoothed", "recall_unknown"), ("deterministic", "recall_unknown_det")):
        t = tables_for(rows, "A1", models, metric=met)
        conf[rule] = {m: round(seed_stats(tt)["mean"], 4) for m, tt in t.items() if tt}
    v3["loafo_fisher_minus_B_conformal_recall"] = conf
    rep["V3_pvalue_rule"] = v3
    print("V3 conformal-recall Fisher-B by rule:", conf)

    # V4 metric agreement (matched TPR vs conformal recall at alpha)
    v4 = {}
    for h, met in (("A1", "recall_unknown"), ("A5", "recall_known")):
        t = tables_for(rows, h, models, metric=met)
        conf_means = {m: seed_stats(tt)["mean"] for m, tt in t.items() if tt}
        v4[h] = {m: {"matched_tpr": hyp[h]["per_model"][m]["mean"], "conformal_recall": conf_means.get(m),
                     "same_sign": conf_means.get(m) is not None
                     and np.sign(conf_means[m]) == np.sign(hyp[h]["per_model"][m]["mean"])} for m in models}
        print(f"V4 {h} same sign:", sum(v["same_sign"] for v in v4[h].values()), "/", len(models))
    rep["V4_metric_agreement"] = v4

    # V5 A5 without the anomalous day
    t = tables_for(rows, "A5", models, fold_filter=lambda f: f != ANOMALY_DAY)
    rep["V5_A5_without_anomaly_day"] = {"excluded": ANOMALY_DAY, **decide("A5", t)}
    print("V5 A5 without", ANOMALY_DAY, rep["V5_A5_without_anomaly_day"]["verdict"])

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)),
                   encoding="utf-8")
    print("->", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
