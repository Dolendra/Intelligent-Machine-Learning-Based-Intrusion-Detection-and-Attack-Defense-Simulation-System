"""In-process request metrics (Stage-2 Phase E — single-process prototype)."""
from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Keep a bounded latency sample for approximate percentiles.
_LATENCY_SAMPLE_MAX = 500


class ProcessMetrics:
    """Thread-safe counters for one API process. Resets on restart."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.started_at = time.time()
        self.requests_total = 0
        self.errors_5xx = 0
        self.errors_4xx = 0
        self._by_status: dict[int, int] = defaultdict(int)
        self._by_path: dict[str, int] = defaultdict(int)
        self._latencies_ms: deque[float] = deque(maxlen=_LATENCY_SAMPLE_MAX)
        self._total_duration_ms = 0.0

    def record(self, *, method: str, path: str, status: int, duration_ms: float) -> None:
        # Collapse path params-ish noise for high-cardinality routes
        bucket = path
        if path.startswith("/api/ingest/queue/") and path != "/api/ingest/queue":
            bucket = "/api/ingest/queue/{job_id}"
        elif path.startswith("/api/incidents/") and path.count("/") >= 3:
            bucket = "/api/incidents/{id}"
        elif path.startswith("/api/simulation/") and path not in {
            "/api/simulation/start",
            "/api/simulation/from-prediction",
        }:
            if path != "/api/simulation":
                bucket = "/api/simulation/{id}"

        with self._lock:
            self.requests_total += 1
            self._by_status[int(status)] += 1
            self._by_path[f"{method} {bucket}"] += 1
            self._latencies_ms.append(float(duration_ms))
            self._total_duration_ms += float(duration_ms)
            if 500 <= status <= 599:
                self.errors_5xx += 1
            elif 400 <= status <= 499:
                self.errors_4xx += 1

    def _percentile(self, samples: list[float], p: float) -> float | None:
        if not samples:
            return None
        ordered = sorted(samples)
        if len(ordered) == 1:
            return round(ordered[0], 3)
        rank = (len(ordered) - 1) * p
        lo = math.floor(rank)
        hi = math.ceil(rank)
        if lo == hi:
            return round(ordered[lo], 3)
        w = rank - lo
        return round(ordered[lo] * (1 - w) + ordered[hi] * w, 3)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            samples = list(self._latencies_ms)
            by_status = dict(sorted(self._by_status.items()))
            # Top paths only — keep payload small
            top_paths = sorted(self._by_path.items(), key=lambda kv: kv[1], reverse=True)[:20]
            total = self.requests_total
            total_ms = self._total_duration_ms
            err4 = self.errors_4xx
            err5 = self.errors_5xx
            started = self.started_at

        uptime = max(0.0, time.time() - started)
        return {
            "scope": "single_process",
            "resets_on_restart": True,
            "uptime_seconds": round(uptime, 1),
            "requests_total": total,
            "errors_4xx": err4,
            "errors_5xx": err5,
            "mean_latency_ms": round(total_ms / total, 3) if total else None,
            "p50_latency_ms": self._percentile(samples, 0.50),
            "p95_latency_ms": self._percentile(samples, 0.95),
            "latency_samples": len(samples),
            "by_status": {str(k): v for k, v in by_status.items()},
            "top_paths": [{"path": p, "count": c} for p, c in top_paths],
            "notes": [
                "In-process counters only — not Prometheus/OpenTelemetry.",
                "Not multi-node; each uvicorn worker has its own metrics.",
                "Use scripts/26_api_load_smoke.py for a local latency smoke check.",
            ],
        }


process_metrics = ProcessMetrics()


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            ms = (time.perf_counter() - start) * 1000
            status = response.status_code if response is not None else 500
            process_metrics.record(
                method=request.method,
                path=request.url.path,
                status=status,
                duration_ms=ms,
            )


def attach_metrics(app) -> None:
    app.add_middleware(MetricsMiddleware)
