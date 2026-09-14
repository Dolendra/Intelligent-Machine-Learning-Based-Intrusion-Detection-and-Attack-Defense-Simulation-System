"""Local API load smoke (Stage-2 Phase E) — latency/RPS check, not a capacity claim.

Usage (API already running, e.g. uvicorn or docker compose):
  python scripts/26_api_load_smoke.py
  python scripts/26_api_load_smoke.py --base http://127.0.0.1:8000 --requests 40 --workers 4

Environment:
  LOAD_SMOKE_BASE   default http://127.0.0.1:8000
  LOAD_SMOKE_N      request count (default 30)
  LOAD_SMOKE_WORKERS concurrent workers (default 4)
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def _get(url: str, timeout: float = 10.0) -> tuple[int, float]:
    start = time.perf_counter()
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return int(resp.status), (time.perf_counter() - start) * 1000
    except urllib.error.HTTPError as exc:
        return int(exc.code), (time.perf_counter() - start) * 1000


def main() -> int:
    parser = argparse.ArgumentParser(description="Aegis IDS API load smoke (prototype)")
    parser.add_argument("--base", default=os.getenv("LOAD_SMOKE_BASE", "http://127.0.0.1:8000"))
    parser.add_argument("--requests", type=int, default=int(os.getenv("LOAD_SMOKE_N", "30")))
    parser.add_argument("--workers", type=int, default=int(os.getenv("LOAD_SMOKE_WORKERS", "4")))
    args = parser.parse_args()

    targets = [
        f"{args.base.rstrip('/')}/api/health",
        f"{args.base.rstrip('/')}/api/ready",
        f"{args.base.rstrip('/')}/api/metrics",
        f"{args.base.rstrip('/')}/api/security/status",
    ]
    # Round-robin across light GET probes (avoid heavy predict load in CI-ish smoke)
    urls = [targets[i % len(targets)] for i in range(max(1, args.requests))]

    latencies: list[float] = []
    statuses: list[int] = []
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(_get, u) for u in urls]
        for fut in as_completed(futures):
            status, ms = fut.result()
            statuses.append(status)
            latencies.append(ms)
    elapsed = time.perf_counter() - t0

    ok = sum(1 for s in statuses if 200 <= s < 300)
    fail = len(statuses) - ok
    summary = {
        "tool": "26_api_load_smoke",
        "prototype_only": True,
        "not_a_capacity_claim": True,
        "base": args.base,
        "requests": len(statuses),
        "workers": args.workers,
        "ok": ok,
        "fail": fail,
        "elapsed_s": round(elapsed, 3),
        "approx_rps": round(len(statuses) / elapsed, 2) if elapsed > 0 else None,
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2) if latencies else None,
            "p50": round(statistics.median(latencies), 2) if latencies else None,
            "max": round(max(latencies), 2) if latencies else None,
        },
        "notes": [
            "Hits health/ready/metrics/security only — not a soak or soak+predict benchmark.",
            "Results vary by machine; do not cite as production SLA evidence.",
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
