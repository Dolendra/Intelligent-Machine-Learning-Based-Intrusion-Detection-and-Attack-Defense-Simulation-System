"""Machine-readable JSON operational event logging."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from backend.observability.context import get_correlation
from backend.observability.redact import redact_mapping
from ids_config import load_config

logger = logging.getLogger("aegis.ops")


def _service_name() -> str:
    return os.getenv("AEGIS_SERVICE", "aegis-api")


def _environment() -> str:
    cfg = load_config().get("observability", {}) or {}
    return str(os.getenv("AEGIS_ENV") or cfg.get("environment") or "development")


def log_event(
    event_type: str,
    *,
    level: str = "info",
    endpoint: str | None = None,
    method: str | None = None,
    status: int | str | None = None,
    duration_ms: float | None = None,
    error_code: str | None = None,
    message: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """Emit one JSON operational log line (not an audit DB row)."""
    corr = get_correlation()
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.lower(),
        "service": _service_name(),
        "environment": _environment(),
        "event_type": event_type,
        "request_id": corr.get("request_id"),
        "job_id": corr.get("job_id"),
        "incident_id": corr.get("incident_id"),
        "action_id": corr.get("action_id"),
        "user": corr.get("user"),
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "duration_ms": round(duration_ms, 3) if duration_ms is not None else None,
        "error_code": error_code,
        "message": message,
        "phase": "P7",
    }
    for key, val in fields.items():
        if val is not None and key not in payload:
            payload[key] = val
    clean = {k: v for k, v in payload.items() if v is not None}
    clean = redact_mapping(clean)
    line = json.dumps(clean, separators=(",", ":"), default=str)
    log_fn = getattr(logger, level.lower(), logger.info)
    log_fn(line)
    return clean
