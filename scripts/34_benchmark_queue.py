#!/usr/bin/env python
"""P8 ingest queue benchmark — submit faster than (or equal to) worker capacity.

Usage:
  python scripts/34_benchmark_queue.py
  python scripts/34_benchmark_queue.py --jobs 40 --flows-per-job 20 --saturate
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

from performance.harness import latency_summary, new_result, write_result
from performance.workloads import resource_snapshot, sample_feature_rows


def main() -> int:
    p = argparse.ArgumentParser(description="P8 queue baseline / saturation")
    p.add_argument("--jobs", type=int, default=20)
    p.add_argument("--flows-per-job", type=int, default=10)
    p.add_argument("--saturate", action="store_true", help="Submit until queue-full errors appear")
    p.add_argument("--scenario", default="high")
    args = p.parse_args()

    from backend.services import pipeline as svc
    from database.db import SessionLocal
    from ingestion.queue import IngestDetectQueue

    q = IngestDetectQueue(max_jobs=50, history=50)

    def _predict(flows: list[dict[str, float]]) -> dict:
        db = SessionLocal()
        try:
            return svc.run_prediction_batch(flows, db=db, persist=False, allow_missing_features=True)
        finally:
            db.close()

    q.set_predict_fn(_predict)
    q.start()

    rows = sample_feature_rows(args.flows_per_job)
    submit_ms: list[float] = []
    submit_errors = 0
    submitted = 0
    t_submit0 = time.perf_counter()
    target = args.jobs
    if args.saturate:
        target = 200  # exceed max_jobs intentionally

    for _ in range(target):
        t0 = time.perf_counter()
        try:
            q.submit(rows, source="p8_bench")
            submitted += 1
            submit_ms.append((time.perf_counter() - t0) * 1000)
        except Exception:  # noqa: BLE001
            submit_errors += 1
            submit_ms.append((time.perf_counter() - t0) * 1000)
            if args.saturate:
                break
    submit_elapsed = time.perf_counter() - t_submit0

    # Wait for drain
    t_wait0 = time.perf_counter()
    deadline = time.time() + 120
    while time.time() < deadline:
        st = q.status()
        if st["queued"] == 0 and not (q._worker and any(j.status == "running" for j in q._jobs.values())):
            # allow brief settle
            time.sleep(0.05)
            st = q.status()
            if st["queued"] == 0:
                break
        time.sleep(0.05)
    drain_s = time.perf_counter() - t_wait0
    st = q.status()
    q.stop(wait=True)

    metrics = st.get("metrics") or {}
    result = new_result(
        workload="ingest_queue",
        scenario="saturation" if args.saturate else args.scenario,
        configuration={
            "jobs_attempted": target,
            "flows_per_job": args.flows_per_job,
            "max_jobs": 50,
            "saturate": args.saturate,
        },
        metrics={
            "submit_latency": latency_summary(submit_ms),
            "queue_metrics": metrics,
            "final_status": {
                "queued": st.get("queued"),
                "worker_alive": st.get("worker_alive"),
            },
        },
        throughput={
            "jobs_submitted": submitted,
            "jobs_submit_errors": submit_errors,
            "submit_jobs_per_sec": round(submitted / submit_elapsed, 3) if submit_elapsed else None,
            "jobs_completed": metrics.get("completed"),
            "jobs_failed": metrics.get("failed"),
            "flows_processed": metrics.get("flows_processed"),
            "avg_detect_latency_ms": metrics.get("avg_detect_latency_ms"),
            "drain_seconds": round(drain_s, 3),
        },
        error_rate=round(submit_errors / max(1, target), 6),
        notes=[
            "In-process single-worker queue prototype — not Redis/Kafka.",
            "Saturation mode expects queue-full RuntimeError rather than silent drop.",
        ],
    )
    result["resources"] = resource_snapshot()
    path = write_result(result)
    print(json.dumps({"wrote": str(path), "throughput": result["throughput"]}, indent=2))
    # Saturate path is successful if we observed controlled rejections
    if args.saturate:
        return 0 if submit_errors > 0 else 1
    return 0 if submit_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
