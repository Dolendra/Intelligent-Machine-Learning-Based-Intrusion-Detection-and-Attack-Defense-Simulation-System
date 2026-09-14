"""P9 startup recovery — reclaim unsafe in-flight response states safely."""
from __future__ import annotations

import logging
from typing import Any

from database.db import ResponseActionRecord, SessionLocal
from security.response.store import response_store
from security.response.types import ActionStatus, utc_now_iso

logger = logging.getLogger("aegis.recovery")

_LAST_SUMMARY: dict[str, Any] = {
    "ran_at": None,
    "reclaimed_executing": 0,
    "reclaimed_approved": 0,
    "expired_swept": 0,
    "notes": [],
}


def recovery_summary() -> dict[str, Any]:
    return dict(_LAST_SUMMARY)


def reclaim_stale_response_actions(*, actor: str = "system-recovery") -> dict[str, Any]:
    """On restart: never leave EXECUTING (or orphan APPROVED) as success paths.

    Safe policy for DRY_RUN / CONTROLLED:
    - EXECUTING → FAILED (do not auto-re-execute)
    - APPROVED with no executed_at → FAILED (incomplete approve→execute)
    - ACTIVE past expires_at → handled by sweep_expired
    """
    reclaimed_executing = 0
    reclaimed_approved = 0
    details: list[dict[str, str]] = []

    with SessionLocal() as db:
        rows = (
            db.query(ResponseActionRecord)
            .filter(
                ResponseActionRecord.status.in_(
                    [ActionStatus.EXECUTING.value, ActionStatus.APPROVED.value]
                )
            )
            .all()
        )
        action_ids = [r.action_id for r in rows]

    for aid in action_ids:
        action = response_store.get(aid)
        if action is None:
            continue
        if action.status == ActionStatus.EXECUTING.value:
            action.status = ActionStatus.FAILED.value
            action.result = "Recovered after process crash during EXECUTING (not re-executed)"
            response_store.append_audit(
                action,
                event="recovered_stale_executing",
                actor=actor,
                detail={
                    "previous_status": ActionStatus.EXECUTING.value,
                    "new_status": ActionStatus.FAILED.value,
                    "auto_reexecute": False,
                },
            )
            reclaimed_executing += 1
            details.append({"action_id": aid, "from": "EXECUTING", "to": "FAILED"})
        elif action.status == ActionStatus.APPROVED.value and not action.executed_at:
            action.status = ActionStatus.FAILED.value
            action.result = "Recovered after process crash before execution completed"
            response_store.append_audit(
                action,
                event="recovered_stale_approved",
                actor=actor,
                detail={
                    "previous_status": ActionStatus.APPROVED.value,
                    "new_status": ActionStatus.FAILED.value,
                    "auto_reexecute": False,
                },
            )
            reclaimed_approved += 1
            details.append({"action_id": aid, "from": "APPROVED", "to": "FAILED"})

    expired_swept = 0
    try:
        from security.response.service import sweep_expired

        swept = sweep_expired(actor=actor)
        expired_swept = len(swept.get("expired") or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("expire sweep during recovery failed: %s", exc)

    summary = {
        "ran_at": utc_now_iso(),
        "reclaimed_executing": reclaimed_executing,
        "reclaimed_approved": reclaimed_approved,
        "expired_swept": expired_swept,
        "details": details,
        "notes": [
            "In-flight EXECUTING/APPROVED actions are marked FAILED — never auto-replayed.",
            "In-process ingest queue jobs are ephemeral and are not recovered across restarts.",
            "LIVE adapters remain forbidden; recovery does not invent network rollback.",
        ],
        "phase": "P9",
    }
    _LAST_SUMMARY.clear()
    _LAST_SUMMARY.update(summary)
    logger.warning(
        "startup_recovery reclaimed_executing=%s reclaimed_approved=%s expired_swept=%s",
        reclaimed_executing,
        reclaimed_approved,
        expired_swept,
    )
    try:
        from backend.observability.events import log_event

        log_event(
            "startup_recovery",
            level="warning",
            status="ok",
            reclaimed_executing=reclaimed_executing,
            reclaimed_approved=reclaimed_approved,
            expired_swept=expired_swept,
        )
    except Exception:  # noqa: BLE001
        pass
    return summary


def run_startup_recovery() -> dict[str, Any]:
    return reclaim_stale_response_actions()
