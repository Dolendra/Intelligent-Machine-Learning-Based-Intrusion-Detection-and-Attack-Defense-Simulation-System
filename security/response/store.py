"""In-memory response-action store + structured audit trail (P2 prototype)."""
from __future__ import annotations

import logging
import threading
import uuid
from typing import Any

from security.response.types import AuditEvent, ResponseAction, utc_now_iso

logger = logging.getLogger("aegis.response.audit")


class ResponseActionStore:
    def __init__(self, *, max_actions: int = 500) -> None:
        self._max = max_actions
        self._lock = threading.RLock()
        self._actions: dict[str, ResponseAction] = {}
        self._order: list[str] = []

    def create(self, action: ResponseAction) -> ResponseAction:
        with self._lock:
            if len(self._order) >= self._max:
                # Drop oldest terminal-ish entries first
                drop = self._order.pop(0)
                self._actions.pop(drop, None)
            self._actions[action.action_id] = action
            self._order.append(action.action_id)
            return action

    def get(self, action_id: str) -> ResponseAction | None:
        with self._lock:
            return self._actions.get(action_id)

    def list(
        self,
        *,
        incident_id: str | None = None,
        limit: int = 50,
    ) -> list[ResponseAction]:
        with self._lock:
            items = list(reversed([self._actions[i] for i in self._order if i in self._actions]))
        if incident_id:
            items = [a for a in items if a.incident_id == incident_id]
        return items[:limit]

    def append_audit(
        self,
        action: ResponseAction,
        *,
        event: str,
        actor: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry = AuditEvent(
            event=event,
            action_id=action.action_id,
            timestamp=utc_now_iso(),
            actor=actor,
            detail=detail or {},
        ).as_dict()
        with self._lock:
            action.audit.append(entry)
        logger.info(
            "response_audit action_id=%s event=%s actor=%s detail=%s",
            action.action_id,
            event,
            actor,
            detail or {},
        )
        return entry


def new_action_id() -> str:
    return f"ra-{uuid.uuid4().hex[:12]}"


# Process-wide singleton (same pattern as ingest queue)
response_store = ResponseActionStore()
