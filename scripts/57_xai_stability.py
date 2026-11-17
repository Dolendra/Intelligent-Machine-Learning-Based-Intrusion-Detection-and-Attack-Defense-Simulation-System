"""E9 — explanation stability study for the frozen v1.1 detector.

Three questions, answered on replay flows that neither v1.1 nor the gate trained or validated on
(leakage-free pool since R1a — see research_artifacts/replay/replay_pool_manifest.json):

1. Consistency   Do flows of the same attack family get the same top-5 SHAP features?
                 (mean pairwise Jaccard of top-5 sets within a family)
2. Robustness    Does a flow's explanation survive ±1% multiplicative noise on every feature
                 (a perturbation far below measurement error)? Jaccard top-5 + Spearman rank on top-10.
3. Agreement     Do SHAP and LIME point at the same features for the same flow? (Jaccard top-5)

Output: models/trained_models/xai_stability_report.json and docs/research/XAI_STABILITY.md
Usage:  python scripts/57_xai_stability.py [--per-family 20] [--seed 7]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from backend.services.pipeline import get_explainer, get_lime_explainer, get_predictor  # noqa: E402

POOL = ROOT / "research_artifacts" / "replay" / "replay_pool.parquet"
OUT_JSON = ROOT / "models" / "trained_models" / "xai_stability_report.json"
OUT_MD = ROOT / "docs" / "research" / "XAI_STABILITY.md"
FAMILIES = ["BENIGN", "Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"]


def jaccard(a, b) -> float:
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 1.0


def top(exp: dict, k: int) -> list[str]:
    return [f["feature"] for f in exp.get("top_features", [])[:k]]


def rank_corr(e1: dict, e2: dict) -> float:
    a = {f["feature"]: abs(f["contribution"]) for f in e1.get("top_features", [])}
    b = {f["feature"]: abs(f["contribution"]) for f in e2.get("top_features", [])}
    keys = sorted(set(a) | set(b))
    if len(keys) < 3:
        return float("nan")
    r = spearmanr([a.get(k, 0.0) for k in keys], [b.get(k, 0.0) for k in keys]).correlation
    return float(r)


def summary(v) -> dict:
    v = np.array([x for x in v if x == x], dtype=float)
    if not v.size:
        return {"mean": None, "sd": None, "n": 0}
    return {"mean": round(float(v.mean()), 4), "sd": round(float(v.std(ddof=1)) if v.size > 1 else 0.0, 4), "n": int(v.size)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-family", type=int, default=20)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    shap_eng, lime_eng, pred = get_explainer(), get_lime_explainer(), get_predictor()
    if shap_eng is None or pred is None:
        raise SystemExit("Models not loaded")
    names = list(shap_eng.bundle.feature_names)
    pool = pd.read_parquet(POOL)

    def feats(row) -> dict[str, float]:
        return {n: float(row[n]) if n in row.index else float(row.get("Fwd Header Length", 0.0)) for n in names}

    t0 = time.time()
    per_family: dict[str, dict] = {}
    all_robust_j, all_robust_r, all_agree = [], [], []
    for fam in FAMILIES:
        g = pool[pool["family"] == fam]
        if g.empty:
            continue
        rows = g.iloc[rng.choice(len(g), size=min(args.per_family, len(g)), replace=False)]
        shap_tops, robust_j, robust_r, agree, predicted = [], [], [], [], []
        for _, row in rows.iterrows():
            x = feats(row)
            e = shap_eng.explain(x, top_k=10)
            predicted.append(e["prediction"])
            shap_tops.append(top(e, 5))
            noisy = {k: v * (1.0 + rng.uniform(-0.01, 0.01)) for k, v in x.items()}
            e2 = shap_eng.explain(noisy, top_k=10)
            robust_j.append(jaccard(top(e, 5), top(e2, 5)))
            robust_r.append(rank_corr(e, e2))
            if lime_eng is not None:
                try:
                    el = lime_eng.explain(x, top_k=10)
                    agree.append(jaccard(top(e, 5), top(el, 5)))
                except Exception:  # noqa: BLE001
                    pass
        consistency = [jaccard(a, b) for a, b in combinations(shap_tops, 2)]
        freq: dict[str, int] = {}
        for t in shap_tops:
            for f in t:
                freq[f] = freq.get(f, 0) + 1
        per_family[fam] = {
            "n_flows": len(rows),
            "predicted_as": {k: predicted.count(k) for k in sorted(set(predicted))},
            "consistency_jaccard_top5": summary(consistency),
            "robustness_jaccard_top5": summary(robust_j),
            "robustness_spearman_top10": summary(robust_r),
            "shap_lime_jaccard_top5": summary(agree),
            "most_frequent_top5": sorted(freq.items(), key=lambda kv: -kv[1])[:5],
        }
        all_robust_j += robust_j
        all_robust_r += robust_r
        all_agree += agree
        print(f"{fam:10s} consistency={per_family[fam]['consistency_jaccard_top5']['mean']} "
              f"robust={per_family[fam]['robustness_jaccard_top5']['mean']} agree={per_family[fam]['shap_lime_jaccard_top5']['mean']}")

    report = {
        "experiment": "E9_xai_stability",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "per_family_flows": args.per_family,
        "perturbation": "independent multiplicative noise U(-1%, +1%) on every feature",
        "overall": {"robustness_jaccard_top5": summary(all_robust_j), "robustness_spearman_top10": summary(all_robust_r),
                    "shap_lime_jaccard_top5": summary(all_agree)},
        "per_family": per_family,
        "runtime_seconds": round(time.time() - t0, 1),
        "notes": ["Jaccard 1.0 = identical top-5 sets; 0.0 = disjoint.",
                  "Consistency measures whether one family has one 'explanation signature'; low values mean explanations are flow-specific.",
                  "Attributions explain the model, not the attack; they are decision support, not causal proof."],
    }
    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = ["# E9 — Explanation stability (auto-generated)", "",
          f"_Generated {report['generated_at'][:19]}Z by `scripts/57_xai_stability.py`; {args.per_family} replay flows per family (frozen-test ∩ gate-test, zero train overlap; pool v2); seed {args.seed}._", "",
          "| Family | Flows | Consistency (Jaccard top-5, within family) | Robustness to ±1% noise (Jaccard top-5) | Rank stability (Spearman top-10) | SHAP–LIME agreement (Jaccard top-5) |",
          "|---|---|---|---|---|---|"]
    for fam, d in per_family.items():
        def m(k):
            s = d[k]
            return "—" if s["mean"] is None else f"{s['mean']:.2f} ± {s['sd']:.2f}"
        md.append(f"| {fam} | {d['n_flows']} | {m('consistency_jaccard_top5')} | {m('robustness_jaccard_top5')} | "
                  f"{m('robustness_spearman_top10')} | {m('shap_lime_jaccard_top5')} |")
    o = report["overall"]
    md += ["", f"Overall: robustness Jaccard {o['robustness_jaccard_top5']['mean']}, rank stability "
               f"{o['robustness_spearman_top10']['mean']}, SHAP–LIME agreement {o['shap_lime_jaccard_top5']['mean']}.", "",
           "Most frequent top-5 features per family:", ""]
    for fam, d in per_family.items():
        md.append(f"* **{fam}** — " + ", ".join(f"{f} ({c}/{d['n_flows']})" for f, c in d["most_frequent_top5"]))
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("wrote", OUT_JSON, OUT_MD, f"{report['runtime_seconds']}s")


if __name__ == "__main__":
    main()
