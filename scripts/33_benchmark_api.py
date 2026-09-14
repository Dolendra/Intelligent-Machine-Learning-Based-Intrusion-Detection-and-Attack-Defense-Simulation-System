#!/usr/bin/env python
"""P8 API concurrency benchmark (requires running uvicorn).

Usage:
  python scripts/33_benchmark_api.py --base http://127.0.0.1:8000
  python scripts/33_benchmark_api.py --include-predict --workers 8 --requests 40

Disable rate limits for meaningful benches: DISABLE_RATE_LIMIT=true on the API process.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from performance.harness import latency_summary, new_result, write_result
from performance.workloads import resource_snapshot, sample_feature_rows


def _request(method: str, url: str, body: bytes | None = None, timeout: float = 60.0) -> tuple[int, float]:
    start = time.perf_counter()
    req = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return int(resp.status), (time.perf_counter() - start) * 1000
    except urllib.error.HTTPError as exc:
        try:
            exc.read()
        except Exception:  # noqa: BLE001
            pass
        return int(exc.code), (time.perf_counter() - start) * 1000
    except Exception:  # noqa: BLE001
        return 0, (time.perf_counter() - start) * 1000


def main() -> int:
    p = argparse.ArgumentParser(description="P8 API concurrency baseline")
    p.add_argument("--base", default=os.getenv("PERF_API_BASE", "http://127.0.0.1:8000"))
    p.add_argument("--requests", type=int, default=40)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--include-predict", action="store_true")
    p.add_argument("--scenario", default="high")
    args = p.parse_args()
    base = args.base.rstrip("/")

    # Probe readiness first
    code, _ = _request("GET", f"{base}/api/health")
    if code == 0:
        print(json.dumps({"error": "API_UNREACHABLE", "base": base}))
        return 2

    jobs: list[tuple[str, str, bytes | None]] = []
    light = [
        ("GET", f"{base}/api/health", None),
        ("GET", f"{base}/api/ready", None),
        ("GET", f"{base}/api/metrics", None),
        ("GET", f"{base}/api/incidents?limit=10", None),
    ]
    for i in range(args.requests):
        jobs.append(light[i % len(light)])

    if args.include_predict:
        try:
            feats = sample_feature_rows(1)[0]
        except Exception:  # noqa: BLE001
            feats = {}
        body = json.dumps({"features": feats, "persist": False}).encode()
        batch_body = json.dumps({"flows": [feats] * 10, "persist": False}).encode()
        for i in range(min(20, args.requests)):
            jobs.append(("POST", f"{base}/api/predict", body))
            if i % 2 == 0:
                jobs.append(("POST", f"{base}/api/predict/batch", batch_body))

    latencies: list[float] = []
    statuses: list[int] = []
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futs = [pool.submit(_request, m, u, b) for m, u, b in jobs]
        for fut in as_completed(futs):
            status, ms = fut.result()
            statuses.append(status)
            latencies.append(ms)
    elapsed = time.perf_counter() - t0
    ok = sum(1 for s in statuses if 200 <= s < 300)
    fail = len(statuses) - ok
    result = new_result(
        workload="api_concurrency",
        scenario=args.scenario,
        configuration={
            "base": base,
            "requests": len(jobs),
            "workers": args.workers,
            "include_predict": args.include_predict,
        },
        metrics=latency_summary(latencies),
        throughput={
            "approx_rps": round(len(jobs) / elapsed, 3) if elapsed else None,
            "ok": ok,
            "fail": fail,
            "status_counts": {str(s): statuses.count(s) for s in sorted(set(statuses))},
        },
        error_rate=round(fail / max(1, len(jobs)), 6),
        notes=[
            "Requires a running API. Set DISABLE_RATE_LIMIT=true on the server for predict-heavy runs.",
            "Not a multi-node or production SLA claim.",
        ],
    )
    result["resources"] = resource_snapshot()
    path = write_result(result)
    print(json.dumps({"wrote": str(path), "throughput": result["throughput"], "metrics": result["metrics"]}, indent=2))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
