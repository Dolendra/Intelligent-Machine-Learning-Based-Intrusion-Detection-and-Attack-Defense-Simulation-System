"""P7 observability — structured logs, metrics, health, alerts (no Prometheus/OTel)."""
from __future__ import annotations

from backend.observability.alerts import evaluate_alerts
from backend.observability.deps import dependency_status, readiness_report
from backend.observability.events import log_event
from backend.observability.ops import ops_snapshot
from backend.observability.registry import domain_metrics

__all__ = [
    "domain_metrics",
    "evaluate_alerts",
    "dependency_status",
    "readiness_report",
    "log_event",
    "ops_snapshot",
]
