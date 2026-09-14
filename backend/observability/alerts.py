"""In-process operational alert conditions (no external paging)."""
from __future__ import annotations

from typing import Any

from ids_config import load_config


DEFAULT_THRESHOLDS = {
    "queue_depth_warn": 25,
    "queue_depth_critical": 80,
    "error_5xx_rate_warn": 0.05,
    "min_requests_for_error_rate": 20,
    "auth_failures_warn": 20,
    "rate_limit_hits_warn": 50,
    "pcap_extract_failures_warn": 5,
    "response_verify_failures_warn": 3,
}


def thresholds() -> dict[str, Any]:
    cfg = (load_config().get("observability") or {}).get("alerts") or {}
    out = dict(DEFAULT_THRESHOLDS)
    for key, default in DEFAULT_THRESHOLDS.items():
        if key in cfg and cfg[key] is not None:
            out[key] = type(default)(cfg[key])
    return out


def evaluate_alerts(
    *,
    deps: dict[str, Any],
    http_metrics: dict[str, Any],
    domain: dict[str, Any],
    queue_depth: int | None = None,
) -> list[dict[str, Any]]:
    """Return active alert conditions that require operator attention."""
    t = thresholds()
    alerts: list[dict[str, Any]] = []

    if (deps.get("database") or {}).get("status") not in {None, "ok"}:
        alerts.append(
            {
                "id": "database_unavailable",
                "severity": "critical",
                "message": "Database unavailable",
                "component": "database",
            }
        )

    if (deps.get("models") or {}).get("status") not in {None, "ok"}:
        alerts.append(
            {
                "id": "model_unavailable",
                "severity": "critical",
                "message": "Model artifacts unavailable",
                "component": "models",
            }
        )

    queue = deps.get("queue") or {}
    if queue.get("status") == "down":
        alerts.append(
            {
                "id": "queue_worker_down",
                "severity": "warning",
                "message": "Ingest queue worker not running",
                "component": "queue",
            }
        )

    depth = queue_depth if queue_depth is not None else queue.get("depth")
    if isinstance(depth, int):
        if depth >= int(t["queue_depth_critical"]):
            alerts.append(
                {
                    "id": "queue_backlog_critical",
                    "severity": "critical",
                    "message": f"Queue backlog excessive ({depth})",
                    "component": "queue",
                    "value": depth,
                }
            )
        elif depth >= int(t["queue_depth_warn"]):
            alerts.append(
                {
                    "id": "queue_backlog_warn",
                    "severity": "warning",
                    "message": f"Queue backlog elevated ({depth})",
                    "component": "queue",
                    "value": depth,
                }
            )

    total = int(http_metrics.get("requests_total") or 0)
    err5 = int(http_metrics.get("errors_5xx") or 0)
    min_req = int(t["min_requests_for_error_rate"])
    if total >= min_req and (err5 / total) >= float(t["error_5xx_rate_warn"]):
        alerts.append(
            {
                "id": "api_5xx_rate_elevated",
                "severity": "warning",
                "message": "5xx error rate elevated",
                "component": "api",
                "value": round(err5 / total, 4),
            }
        )

    sec = domain.get("security") or {}
    if int(sec.get("authentication_failures") or 0) >= int(t["auth_failures_warn"]):
        alerts.append(
            {
                "id": "auth_failures_spike",
                "severity": "warning",
                "message": "Authentication failures spike",
                "component": "security",
                "value": sec.get("authentication_failures"),
            }
        )
    if int(sec.get("rate_limit_hits") or 0) >= int(t["rate_limit_hits_warn"]):
        alerts.append(
            {
                "id": "rate_limit_spike",
                "severity": "warning",
                "message": "Rate-limit violations spike",
                "component": "security",
                "value": sec.get("rate_limit_hits"),
            }
        )

    pcap = domain.get("pcap") or {}
    if int(pcap.get("extraction_failure") or 0) >= int(t["pcap_extract_failures_warn"]):
        alerts.append(
            {
                "id": "pcap_extraction_failing",
                "severity": "warning",
                "message": "PCAP extraction repeatedly failing",
                "component": "pcap",
                "value": pcap.get("extraction_failure"),
            }
        )

    resp = domain.get("response") or {}
    if int(resp.get("actions_failed") or 0) >= int(t["response_verify_failures_warn"]):
        alerts.append(
            {
                "id": "response_failures",
                "severity": "warning",
                "message": "Response verification/execution failures elevated",
                "component": "response",
                "value": resp.get("actions_failed"),
            }
        )

    return alerts
