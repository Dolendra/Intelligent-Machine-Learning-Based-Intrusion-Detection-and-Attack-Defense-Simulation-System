"""Aggregated operational snapshot for /api/ops/status and System UI."""
from __future__ import annotations

from typing import Any

from backend.observability.alerts import evaluate_alerts, thresholds
from backend.observability.deps import dependency_status, readiness_report
from backend.observability.registry import domain_metrics
from ids_config import load_config


def ops_snapshot() -> dict[str, Any]:
    from backend.middleware.metrics_mw import process_metrics

    http = process_metrics.snapshot()
    domain = domain_metrics.snapshot()
    deps = dependency_status(include_optional=True)
    ready = readiness_report()

    queue_depth = None
    queue_metrics = None
    try:
        from ingestion.queue import ingest_queue

        q = ingest_queue.status()
        queue_depth = int(q.get("queued") or 0)
        queue_metrics = q.get("metrics")
        # Prefer live queue counters when available
        if queue_metrics:
            domain = dict(domain)
            domain["queue"] = {
                "jobs_submitted": queue_metrics.get("submitted", domain["queue"]["jobs_submitted"]),
                "jobs_completed": queue_metrics.get("completed", domain["queue"]["jobs_completed"]),
                "jobs_failed": queue_metrics.get("failed", domain["queue"]["jobs_failed"]),
                "flows_processed": queue_metrics.get("flows_processed"),
                "avg_detect_latency_ms": queue_metrics.get("avg_detect_latency_ms"),
                "queue_depth": queue_depth,
            }
    except Exception:  # noqa: BLE001
        pass

    # Pending response approvals from durable store
    pending_approvals = 0
    failed_actions = 0
    verified_actions = 0
    rolled_back = 0
    try:
        from security.response.store import response_store

        for action in response_store.list(limit=200):
            if action.status == "PROPOSED":
                pending_approvals += 1
            elif action.status == "FAILED":
                failed_actions += 1
            elif action.status in {"VERIFIED", "ACTIVE"}:
                verified_actions += 1
            elif action.status in {"ROLLED_BACK", "EXPIRED"}:
                rolled_back += 1
    except Exception:  # noqa: BLE001
        pass

    alerts = evaluate_alerts(
        deps=deps,
        http_metrics=http,
        domain=domain,
        queue_depth=queue_depth,
    )
    cfg = load_config()
    obs = cfg.get("observability") or {}
    retention = (cfg.get("database") or {}).get("retention") or {}

    return {
        "phase": "P7",
        "service": "aegis-api",
        "environment": obs.get("environment") or "development",
        "liveness": {"status": "ok", "endpoint": "/api/health"},
        "readiness": ready,
        "dependencies": deps,
        "performance": {
            "requests_total": http.get("requests_total"),
            "p50_latency_ms": http.get("p50_latency_ms"),
            "p95_latency_ms": http.get("p95_latency_ms"),
            "errors_4xx": http.get("errors_4xx"),
            "errors_5xx": http.get("errors_5xx"),
            "uptime_seconds": http.get("uptime_seconds"),
        },
        "detection": domain.get("detection"),
        "queue": domain.get("queue"),
        "pcap": domain.get("pcap"),
        "response": {
            **(domain.get("response") or {}),
            "pending_approvals": pending_approvals,
            "verified_actions": verified_actions,
            "failed_actions_open": failed_actions,
            "rolled_back_or_expired": rolled_back,
        },
        "security": domain.get("security"),
        "alerts": alerts,
        "alert_thresholds": thresholds(),
        "retention": {
            "audit_days": retention.get("audit_days"),
            "incidents_days": retention.get("incidents_days"),
            "simulations_days": retention.get("simulations_days"),
            "application_logs": obs.get("log_retention_days", 14),
            "notes": [
                "Audit DB rows follow database.retention (P6).",
                "Application/ops logs are process stdout — rotate via process manager/container log driver.",
            ],
        },
        "prometheus": False,
        "opentelemetry": False,
        "notes": [
            "Operational view — separate from SOC incident dashboard.",
            "In-process metrics reset on restart; not a multi-node SRE stack.",
        ],
    }
