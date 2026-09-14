#!/usr/bin/env python
"""P8 offline single-flow prediction benchmark (no FastAPI).

Usage:
  python scripts/30_benchmark_prediction.py
  python scripts/30_benchmark_prediction.py --n 100 --scenario normal
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from performance.harness import flows_per_sec, latency_summary, new_result, time_calls, write_result
from performance.workloads import resource_snapshot, sample_feature_rows


def main() -> int:
    p = argparse.ArgumentParser(description="P8 prediction latency/throughput baseline")
    p.add_argument("--n", type=int, default=50, help="Timed iterations")
    p.add_argument("--warmup", type=int, default=3)
    p.add_argument("--scenario", default="normal", choices=["normal", "high", "saturation", "component"])
    p.add_argument("--persist", action="store_true", help="Also time DB-persisting path")
    args = p.parse_args()

    from backend.services.pipeline import get_predictor, run_prediction

    if get_predictor() is None:
        print(json.dumps({"error": "MODELS_NOT_READY"}))
        return 2

    rows = sample_feature_rows(1)
    features = rows[0]

    def _once():
        run_prediction(features, db=None, persist=False, allow_missing_features=True)

    samples, errors = time_calls(_once, args.n, warmup=args.warmup)
    elapsed_s = sum(samples) / 1000.0
    summary = latency_summary(samples)
    result = new_result(
        workload="prediction_single",
        scenario=args.scenario,
        configuration={"iterations": args.n, "warmup": args.warmup, "persist": False},
        metrics=summary,
        throughput={
            "flows_per_sec": flows_per_sec(args.n - errors, elapsed_s),
            "errors": errors,
        },
        error_rate=round(errors / max(1, args.n), 6),
        notes=[
            "Offline pipeline.run_prediction (DT+RF+risk); no HTTP, no SHAP.",
            "Research baseline models unchanged.",
        ],
    )
    result["resources"] = resource_snapshot()

    if args.persist:
        from database.db import SessionLocal, init_db

        init_db()

        def _persist_once():
            db = SessionLocal()
            try:
                run_prediction(features, db=db, persist=True, allow_missing_features=True)
            finally:
                db.close()

        ps, pe = time_calls(_persist_once, min(20, args.n), warmup=1)
        result.setdefault("stages_ms", {})
        result["stages_ms"]["predict_no_persist"] = summary
        result["stages_ms"]["predict_with_persist"] = latency_summary(ps)
        result["throughput"]["persist_errors"] = pe

    path = write_result(result)
    print(json.dumps({"wrote": str(path), **{k: result[k] for k in ("experiment_id", "metrics", "throughput", "error_rate")}}, indent=2))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
