#!/usr/bin/env python
"""P8 database / response-action concurrency baseline.

Usage:
  python scripts/35_benchmark_db.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from performance.harness import latency_summary, new_result, time_calls, write_result
from performance.workloads import resource_snapshot


def main() -> int:
    p = argparse.ArgumentParser(description="P8 DB insert/query + concurrent approve claim")
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--scenario", default="component")
    args = p.parse_args()

    from database.db import Incident, SessionLocal, init_db
    from security.response.service import approve_action, propose_action
    from security.response.store import response_store

    init_db()
    response_store.clear()

    # Incident insert latency
    def _insert():
        code = f"PERF-{time.time_ns()}"
        with SessionLocal() as db:
            db.add(
                Incident(
                    incident_code=code,
                    attack_type="DDoS",
                    is_attack=1,
                    confidence=0.9,
                    risk_score=0.8,
                    severity="High",
                    status="Detected",
                    hit_count=1,
                )
            )
            db.commit()

    insert_s, insert_e = time_calls(_insert, args.n, warmup=1)

    def _query():
        with SessionLocal() as db:
            db.query(Incident).order_by(Incident.id.desc()).limit(20).all()

    query_s, query_e = time_calls(_query, args.n, warmup=1)

    # Concurrent duplicate approve — exactly one success
    proposed = propose_action(attack_type="DDoS", source_ip="203.0.113.10", mode="DRY_RUN")
    aid = proposed["action_id"]
    outcomes: list[str] = []

    def _approve():
        try:
            approve_action(aid, actor="responder")
            return "ok"
        except Exception as exc:  # noqa: BLE001
            return getattr(exc, "code", type(exc).__name__)

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(_approve) for _ in range(8)]
        for fut in as_completed(futs):
            outcomes.append(fut.result())
    claim_ms = (time.perf_counter() - t0) * 1000

    result = new_result(
        workload="database_response",
        scenario=args.scenario,
        configuration={"iterations": args.n, "concurrent_approves": 8},
        metrics={
            "incident_insert": latency_summary(insert_s),
            "incident_query": latency_summary(query_s),
            "concurrent_approve_claim_ms": round(claim_ms, 3),
            "approve_outcomes": {k: outcomes.count(k) for k in sorted(set(outcomes))},
        },
        stages={
            "insert": latency_summary(insert_s),
            "query": latency_summary(query_s),
        },
        error_rate=round((insert_e + query_e) / max(1, 2 * args.n), 6),
        notes=[
            "Atomic response status claim must yield a single ok under concurrency.",
            "SQLite/default local DB — not a Postgres cluster benchmark.",
        ],
    )
    result["resources"] = resource_snapshot()
    ok_claims = outcomes.count("ok")
    result["throughput"] = {"approve_ok": ok_claims, "approve_rejected": len(outcomes) - ok_claims}
    path = write_result(result)
    print(json.dumps({"wrote": str(path), "metrics": result["metrics"]}, indent=2))
    return 0 if ok_claims == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
