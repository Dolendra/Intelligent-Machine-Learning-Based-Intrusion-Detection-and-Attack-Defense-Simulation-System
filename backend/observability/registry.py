"""Domain metrics registry (API / detection / queue / PCAP / response / security)."""
from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any


class DomainMetrics:
    """In-process counters — resets on restart (honest Stage-2 limit)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.started_at = time.time()
        self._counters: dict[str, int] = defaultdict(int)
        self._latency: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=500))

    def incr(self, name: str, amount: int = 1, **labels: str) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._counters[key] += int(amount)

    def observe_ms(self, name: str, duration_ms: float, **labels: str) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._latency[key].append(float(duration_ms))
            self._counters[f"{key}__count"] += 1

    @staticmethod
    def _key(name: str, labels: dict[str, str]) -> str:
        if not labels:
            return name
        parts = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}|{parts}"

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
            counters = dict(self._counters)
            latency = {k: list(v) for k, v in self._latency.items()}

        latency_summary = {}
        for name, samples in latency.items():
            latency_summary[name] = {
                "count": len(samples),
                "p50_ms": self._percentile(samples, 0.50),
                "p95_ms": self._percentile(samples, 0.95),
                "last_ms": round(samples[-1], 3) if samples else None,
            }

        def c(name: str) -> int:
            return int(counters.get(name, 0))

        return {
            "phase": "P7",
            "scope": "single_process",
            "resets_on_restart": True,
            "uptime_seconds": round(max(0.0, time.time() - self.started_at), 1),
            "api": {
                "requests_total": c("api.requests_total"),
                "request_errors_total": c("api.request_errors_total"),
            },
            "detection": {
                "flows_processed_total": c("detection.flows_processed_total"),
                "detections_total": c("detection.detections_total"),
                "attacks_detected_total": c("detection.attacks_detected_total"),
                "normal_flows_total": c("detection.normal_flows_total"),
                "prediction_latency": latency_summary.get("detection.prediction_latency_ms"),
            },
            "queue": {
                "jobs_submitted": c("queue.jobs_submitted"),
                "jobs_completed": c("queue.jobs_completed"),
                "jobs_failed": c("queue.jobs_failed"),
            },
            "pcap": {
                "uploads": c("pcap.uploads"),
                "rejections": c("pcap.rejections"),
                "bytes": c("pcap.bytes"),
                "extraction_success": c("pcap.extraction_success"),
                "extraction_failure": c("pcap.extraction_failure"),
            },
            "response": {
                "actions_proposed": c("response.actions_proposed"),
                "actions_approved": c("response.actions_approved"),
                "actions_rejected": c("response.actions_rejected"),
                "actions_failed": c("response.actions_failed"),
                "actions_verified": c("response.actions_verified"),
                "actions_rolled_back": c("response.actions_rolled_back"),
            },
            "security": {
                "authentication_failures": c("security.authentication_failures"),
                "authorization_denials": c("security.authorization_denials"),
                "rate_limit_hits": c("security.rate_limit_hits"),
                "invalid_uploads": c("security.invalid_uploads"),
                "validation_failures": c("security.validation_failures"),
                "blocked_requests": c("security.blocked_requests"),
                "security_events": c("security.security_events"),
            },
            "latency": latency_summary,
            "raw_counters": counters,
        }

    def reset(self) -> None:
        """Test helper."""
        with self._lock:
            self._counters.clear()
            self._latency.clear()
            self.started_at = time.time()


domain_metrics = DomainMetrics()
