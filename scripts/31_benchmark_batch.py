#!/usr/bin/env python
"""P8 batch prediction benchmark across sizes (offline).

API caps batch at 500; larger sizes use IDSPredictor.predict_many_vectorized directly
and are labeled as predictor_only.

Usage:
  python scripts/31_benchmark_batch.py
  python scripts/31_benchmark_batch.py --sizes 100,500,1000
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from performance.harness import flows_per_sec, latency_summary, new_result, write_result
from performance.workloads import resource_snapshot, sample_feature_rows


def main() -> int:
    p = argparse.ArgumentParser(description="P8 batch prediction baseline")
    p.add_argument("--sizes", default="100,500,1000,5000", help="Comma-separated batch sizes")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--scenario", default="normal")
    args = p.parse_args()
    sizes = [int(x.strip()) for x in args.sizes.split(",") if x.strip()]

    from backend.services.pipeline import get_predictor, run_prediction_batch

    predictor = get_predictor()
    if predictor is None:
        print(json.dumps({"error": "MODELS_NOT_READY"}))
        return 2

    by_size: dict[str, Any] = {}
    import pandas as pd

    for size in sizes:
        rows = sample_feature_rows(size)
        samples: list[float] = []
        mode = "pipeline_batch" if size <= 500 else "predictor_vectorized"
        for _ in range(max(1, args.repeats)):
            t0 = time.perf_counter()
            if size <= 500:
                run_prediction_batch(rows, db=None, persist=False, allow_missing_features=True)
            else:
                df = pd.DataFrame(rows)
                predictor.predict_many_vectorized(df, allow_missing=True)
            samples.append((time.perf_counter() - t0) * 1000.0)
        lat = latency_summary(samples)
        mean_s = (lat["mean_ms"] or 0) / 1000.0
        by_size[str(size)] = {
            "mode": mode,
            "api_batch_limit": 500,
            "latency": lat,
            "flows_per_sec": flows_per_sec(size, mean_s) if mean_s else None,
        }

    result = new_result(
        workload="prediction_batch",
        scenario=args.scenario,
        configuration={"sizes": sizes, "repeats": args.repeats, "api_batch_cap": 500},
        metrics={"by_size": by_size},
        throughput={
            "best_flows_per_sec": max((v["flows_per_sec"] or 0) for v in by_size.values()),
        },
        notes=[
            "Sizes >500 use predictor.predict_many_vectorized (API rejects >500).",
            "Does not include SHAP or HTTP overhead.",
        ],
    )
    result["resources"] = resource_snapshot()
    path = write_result(result)
    print(json.dumps({"wrote": str(path), "by_size": by_size}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
