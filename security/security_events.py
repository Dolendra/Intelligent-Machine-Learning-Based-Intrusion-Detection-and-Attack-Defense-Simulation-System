"""Structured security-boundary audit events (P5) — durable append-only rows (P6)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("aegis.security")


def security_event(
    event: str,
    *,
    request_id: str | None = None,
    path: str | None = None,
    method: str | None = None,
    code: str | None = None,
    user: str | None = None,
    role: str | None = None,
    client: str | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "request_id": request_id,
        "path": path,
        "method": method,
        "code": code,
        "user": user,
        "role": role,
        "client": client,
        "phase": "P7",
    }
    if detail:
        payload["detail"] = detail
    clean = {k: v for k, v in payload.items() if v is not None}
    logger.warning("security_event %s", json.dumps(clean, separators=(",", ":")))
    try:
        from backend.observability.registry import domain_metrics

        domain_metrics.incr("security.security_events")
        ev = event.lower()
        if "auth" in ev and ("fail" in ev or "unauth" in ev):
            domain_metrics.incr("security.authentication_failures")
        if "forbidden" in ev or "denied" in ev or code in {"FORBIDDEN", "RBAC_DENIED"}:
            domain_metrics.incr("security.authorization_denials")
        if "rate" in ev or code == "RATE_LIMITED":
            domain_metrics.incr("security.rate_limit_hits")
            domain_metrics.incr("security.blocked_requests")
        if code in {"REQUEST_TOO_LARGE", "PCAP_REJECTED", "INVALID_UPLOAD"}:
            domain_metrics.incr("security.invalid_uploads")
            domain_metrics.incr("security.blocked_requests")
        if code == "VALIDATION_ERROR":
            domain_metrics.incr("security.validation_failures")
    except Exception:  # noqa: BLE001
        pass
    try:
        from database.db import SecurityAuditEvent, SessionLocal

        with SessionLocal() as db:
            db.add(
                SecurityAuditEvent(
                    event=event,
                    timestamp=str(payload["ts"]),
                    request_id=request_id,
                    path=path,
                    method=method,
                    code=code,
                    user=user,
                    role=role,
                    client=client,
                    phase="P7",
                    detail_json=json.dumps(detail, separators=(",", ":")) if detail else None,
                )
            )
            db.commit()
    except Exception:  # noqa: BLE001
        logger.debug("security_event persistence skipped", exc_info=True)
    return clean
