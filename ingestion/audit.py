"""Structured ingest audit events (prototype — log sink, not full SIEM)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("aegis.ingest.audit")


def audit_ingest_event(
    *,
    event: str,
    source: str,
    request_id: str | None = None,
    filename: str | None = None,
    sha256: str | None = None,
    size_bytes: int | None = None,
    code: str | None = None,
    flow_count: int | None = None,
    schema_version: str | None = None,
    predict: bool | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Emit a single-line JSON audit record for PCAP/CSV ingest."""
    payload: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "source": source,
        "request_id": request_id,
        "filename": filename,
        "sha256": sha256,
        "size_bytes": size_bytes,
        "code": code,
        "flow_count": flow_count,
        "schema_version": schema_version,
        "predict": predict,
        "baseline": "v1.1-research",
    }
    if extra:
        payload["extra"] = extra
    # Drop Nones for cleaner logs
    clean = {k: v for k, v in payload.items() if v is not None}
    logger.info("ingest_audit %s", json.dumps(clean, separators=(",", ":")))
    return clean
