#!/usr/bin/env python
"""P8 SHAP vs ML-only latency comparison (offline).

Usage:
  python scripts/32_benchmark_shap.py
  python scripts/32_benchmark_shap.py --n 20
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from performance.harness import latency_summary, new_result, time_calls, write_result
from performance.workloads import resource_snapshot, sample_feature_rows


def main() -> int:
    p = argparse.ArgumentParser(description="P8 ML-only vs ML+SHAP baseline")
    p.add_argument("--n", type=int, default=15)
    p.add_argument("--warmup", type=int, default=1)
    p.add_argument("--scenario", default="component")
    args = p.parse_args()

    from backend.services.pipeline import get_predictor, run_explain, run_prediction

    if get_predictor() is None:
        print(json.dumps({"error": "MODELS_NOT_READY"}))
        return 2

    features = sample_feature_rows(1)[0]

    def _ml():
        run_prediction(features, db=None, persist=False, allow_missing_features=True)

    def _shap():
        run_explain(features, top_k=10, method="shap", allow_missing_features=True)

    ml_s, ml_e = time_calls(_ml, args.n, warmup=args.warmup)
    shap_s, shap_e = time_calls(_shap, args.n, warmup=args.warmup)
    ml = latency_summary(ml_s)
    shap = latency_summary(shap_s)
    ratio = None
    if ml.get("p50_ms") and shap.get("p50_ms") and ml["p50_ms"] > 0:
        ratio = round(shap["p50_ms"] / ml["p50_ms"], 2)

    result = new_result(
        workload="shap_vs_ml",
        scenario=args.scenario,
        configuration={"iterations": args.n, "shap_top_k": 10},
        metrics={"ml_only": ml, "ml_plus_shap": shap, "shap_to_ml_p50_ratio": ratio},
        stages={"ml_only": ml, "ml_plus_shap": shap},
        error_rate=round((ml_e + shap_e) / max(1, 2 * args.n), 6),
        notes=[
            "SHAP is expected to be substantially slower than prediction alone.",
            "Architecture already targets SHAP on high-risk detections, not all traffic.",
            "Models unchanged.",
        ],
    )
    result["resources"] = resource_snapshot()
    path = write_result(result)
    print(json.dumps({"wrote": str(path), "metrics": result["metrics"]}, indent=2))
    return 0 if (ml_e + shap_e) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
