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
        "phase": "P5",
    }
    if detail:
        payload["detail"] = detail
    clean = {k: v for k, v in payload.items() if v is not None}
    logger.warning("security_event %s", json.dumps(clean, separators=(",", ":")))
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
                    phase="P5",
                    detail_json=json.dumps(detail, separators=(",", ":")) if detail else None,
                )
            )
            db.commit()
    except Exception:  # noqa: BLE001
        # Never fail the request path if audit persistence is unavailable
        logger.debug("security_event persistence skipped", exc_info=True)
    return clean
