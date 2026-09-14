"""Durable response-action store + append-only audit (P6)."""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import update

from database.db import ResponseActionRecord, ResponseAuditEvent, SessionLocal
from security.response.types import AuditEvent, ResponseAction, utc_now_iso

logger = logging.getLogger("aegis.response.audit")

_ACTION_COLUMNS = (
    "action_id",
    "action_type",
    "incident_id",
    "source",
    "target",
    "reason",
    "risk_score",
    "severity",
    "duration_minutes",
    "mode",
    "adapter",
    "status",
    "created_at",
    "created_by",
    "approved_at",
    "approved_by",
    "rejected_at",
    "rejected_by",
    "rejection_reason",
    "executed_at",
    "verified_at",
    "expires_at",
    "rolled_back_at",
    "result",
    "dry_run_preview",
    "rollback_status",
    "inverse_action",
    "attack_type",
)


class ResponseStoreError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _row_values(action: ResponseAction) -> dict[str, Any]:
    return {
        "action_id": action.action_id,
        "action_type": action.action_type,
        "incident_id": action.incident_id,
        "source": action.source,
        "target": action.target,
        "reason": action.reason,
        "risk_score": action.risk_score,
        "severity": action.severity,
        "duration_minutes": int(action.duration_minutes or 0),
        "mode": action.mode,
        "adapter": action.adapter,
        "status": action.status,
        "created_at": action.created_at,
        "created_by": action.created_by,
        "approved_at": action.approved_at,
        "approved_by": action.approved_by,
        "rejected_at": action.rejected_at,
        "rejected_by": action.rejected_by,
        "rejection_reason": action.rejection_reason,
        "executed_at": action.executed_at,
        "verified_at": action.verified_at,
        "expires_at": action.expires_at,
        "rolled_back_at": action.rolled_back_at,
        "result": action.result,
        "dry_run_preview": action.dry_run_preview,
        "rollback_status": action.rollback_status,
        "reversible": 1 if action.reversible else 0,
        "inverse_action": action.inverse_action,
        "attack_type": action.attack_type,
        "live_network_change": 1 if action.live_network_change else 0,
        "updated_at": datetime.now(timezone.utc),
    }


def _action_from_row(row: ResponseActionRecord, audits: list[dict[str, Any]]) -> ResponseAction:
    return ResponseAction(
        action_id=row.action_id,
        action_type=row.action_type,
        incident_id=row.incident_id,
        source=row.source or "api",
        target=row.target,
        reason=row.reason or "",
        risk_score=row.risk_score,
        severity=row.severity,
        duration_minutes=int(row.duration_minutes or 0),
        mode=row.mode or "DRY_RUN",
        adapter=row.adapter or "dry_run",
        status=row.status or "PROPOSED",
        created_at=row.created_at or utc_now_iso(),
        created_by=row.created_by,
        approved_at=row.approved_at,
        approved_by=row.approved_by,
        rejected_at=row.rejected_at,
        rejected_by=row.rejected_by,
        rejection_reason=row.rejection_reason,
        executed_at=row.executed_at,
        verified_at=row.verified_at,
        expires_at=row.expires_at,
        rolled_back_at=row.rolled_back_at,
        result=row.result,
        dry_run_preview=row.dry_run_preview,
        rollback_status=row.rollback_status,
        reversible=bool(row.reversible if row.reversible is not None else 1),
        inverse_action=row.inverse_action,
        attack_type=row.attack_type,
        live_network_change=bool(row.live_network_change),
        audit=list(audits),
    )


def _load_audits(db, action_id: str) -> list[dict[str, Any]]:
    rows = (
        db.query(ResponseAuditEvent)
        .filter(ResponseAuditEvent.action_id == action_id)
        .order_by(ResponseAuditEvent.id.asc())
        .all()
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        detail: dict[str, Any] = {}
        if r.detail_json:
            try:
                detail = json.loads(r.detail_json)
            except json.JSONDecodeError:
                detail = {"raw": r.detail_json}
        out.append(
            {
                "event": r.event,
                "action_id": r.action_id,
                "timestamp": r.timestamp,
                "actor": r.actor,
                "detail": detail,
            }
        )
    return out


class ResponseActionStore:
    """SQLite/Postgres-backed store with atomic status transitions."""

    def __init__(self, *, max_actions: int = 500) -> None:
        self._max = max_actions
        self._lock = threading.RLock()

    def create(self, action: ResponseAction) -> ResponseAction:
        with self._lock:
            with SessionLocal() as db:
                db.add(ResponseActionRecord(**_row_values(action)))
                # Soft retention: drop oldest terminal rows beyond max
                count = db.query(ResponseActionRecord).count()
                if count > self._max:
                    oldest = (
                        db.query(ResponseActionRecord)
                        .order_by(ResponseActionRecord.id.asc())
                        .limit(count - self._max)
                        .all()
                    )
                    for row in oldest:
                        if row.status in {"PROPOSED", "APPROVED", "EXECUTING", "ACTIVE"}:
                            continue
                        db.query(ResponseAuditEvent).filter(
                            ResponseAuditEvent.action_id == row.action_id
                        ).delete()
                        db.delete(row)
                db.commit()
        return action

    def get(self, action_id: str) -> ResponseAction | None:
        with SessionLocal() as db:
            row = (
                db.query(ResponseActionRecord)
                .filter(ResponseActionRecord.action_id == action_id)
                .first()
            )
            if row is None:
                return None
            return _action_from_row(row, _load_audits(db, action_id))

    def list(
        self,
        *,
        incident_id: str | None = None,
        limit: int = 50,
    ) -> list[ResponseAction]:
        with SessionLocal() as db:
            q = db.query(ResponseActionRecord).order_by(ResponseActionRecord.id.desc())
            if incident_id:
                q = q.filter(ResponseActionRecord.incident_id == incident_id)
            rows = q.limit(limit).all()
            return [_action_from_row(r, _load_audits(db, r.action_id)) for r in rows]

    def save(self, action: ResponseAction) -> ResponseAction:
        """Persist full action row (audit rows are separate / append-only)."""
        with self._lock:
            with SessionLocal() as db:
                row = (
                    db.query(ResponseActionRecord)
                    .filter(ResponseActionRecord.action_id == action.action_id)
                    .first()
                )
                values = _row_values(action)
                if row is None:
                    db.add(ResponseActionRecord(**values))
                else:
                    for key, val in values.items():
                        if key == "action_id":
                            continue
                        setattr(row, key, val)
                db.commit()
        return action

    def append_audit(
        self,
        action: ResponseAction,
        *,
        event: str,
        actor: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Write action snapshot + append-only audit event in one transaction."""
        entry = AuditEvent(
            event=event,
            action_id=action.action_id,
            timestamp=utc_now_iso(),
            actor=actor,
            detail=detail or {},
        ).as_dict()
        action.audit.append(entry)
        with self._lock:
            with SessionLocal() as db:
                row = (
                    db.query(ResponseActionRecord)
                    .filter(ResponseActionRecord.action_id == action.action_id)
                    .first()
                )
                values = _row_values(action)
                if row is None:
                    db.add(ResponseActionRecord(**values))
                else:
                    for key, val in values.items():
                        if key == "action_id":
                            continue
                        setattr(row, key, val)
                db.add(
                    ResponseAuditEvent(
                        action_id=action.action_id,
                        event=event,
                        timestamp=entry["timestamp"],
                        actor=actor,
                        detail_json=json.dumps(detail or {}, separators=(",", ":")),
                    )
                )
                db.commit()
        logger.info(
            "response_audit action_id=%s event=%s actor=%s detail=%s",
            action.action_id,
            event,
            actor,
            detail or {},
        )
        return entry

    def claim_status(
        self,
        action_id: str,
        *,
        expected: str,
        new_status: str,
        audit_event: str | None = None,
        actor: str | None = None,
        detail: dict[str, Any] | None = None,
        **fields: Any,
    ) -> ResponseAction:
        """Atomically transition status (prevents duplicate approve/reject)."""
        with self._lock:
            with SessionLocal() as db:
                values: dict[str, Any] = {
                    "status": new_status,
                    "updated_at": datetime.now(timezone.utc),
                }
                for key, val in fields.items():
                    if key in _ACTION_COLUMNS or key in {
                        "reversible",
                        "live_network_change",
                    }:
                        values[key] = val
                result = db.execute(
                    update(ResponseActionRecord)
                    .where(
                        ResponseActionRecord.action_id == action_id,
                        ResponseActionRecord.status == expected,
                    )
                    .values(**values)
                )
                if result.rowcount != 1:
                    row = (
                        db.query(ResponseActionRecord)
                        .filter(ResponseActionRecord.action_id == action_id)
                        .first()
                    )
                    db.rollback()
                    if row is None:
                        raise ResponseStoreError("NOT_FOUND", f"Unknown action {action_id}")
                    raise ResponseStoreError(
                        "ALREADY_DECIDED",
                        f"Action is '{row.status}'; cannot transition from '{expected}'",
                    )
                if audit_event:
                    ts = utc_now_iso()
                    db.add(
                        ResponseAuditEvent(
                            action_id=action_id,
                            event=audit_event,
                            timestamp=ts,
                            actor=actor,
                            detail_json=json.dumps(detail or {}, separators=(",", ":")),
                        )
                    )
                db.commit()
        action = self.get(action_id)
        if action is None:
            raise ResponseStoreError("NOT_FOUND", f"Unknown action {action_id}")
        return action

    def clear(self) -> None:
        """Test helper — wipe response actions and their audit rows."""
        with self._lock:
            with SessionLocal() as db:
                db.query(ResponseAuditEvent).delete()
                db.query(ResponseActionRecord).delete()
                db.commit()


def new_action_id() -> str:
    return f"ra-{uuid.uuid4().hex[:12]}"


# Process-wide singleton (same pattern as ingest queue)
response_store = ResponseActionStore()
