"""Controlled response — abstract action types and lifecycle."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    MONITOR = "MONITOR"
    RATE_LIMIT = "RATE_LIMIT"
    BLOCK_SOURCE = "BLOCK_SOURCE"
    ISOLATE_HOST = "ISOLATE_HOST"
    ESCALATE = "ESCALATE"


class ActionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    ROLLED_BACK = "ROLLED_BACK"
    EXPIRED = "EXPIRED"


class ExecutionMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    CONTROLLED = "CONTROLLED"  # TestNetworkAdapter — simulated only
    LIVE = "LIVE"  # forbidden until a later phase


ALLOWED_ACTION_TYPES = {m.value for m in ActionType}
ALLOWED_MODES = {ExecutionMode.DRY_RUN.value, ExecutionMode.CONTROLLED.value}
EXECUTED_STATUSES = {
    ActionStatus.EXECUTING,
    ActionStatus.SUCCEEDED,
    ActionStatus.FAILED,
    ActionStatus.VERIFIED,
    ActionStatus.ACTIVE,
    ActionStatus.ROLLED_BACK,
    ActionStatus.EXPIRED,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


@dataclass
class ResponseAction:
    action_id: str
    action_type: str
    incident_id: str | None
    source: str
    target: str
    reason: str
    risk_score: float | None
    severity: str | None
    duration_minutes: int
    mode: str = ExecutionMode.DRY_RUN.value
    adapter: str = "dry_run"
    status: str = ActionStatus.PROPOSED.value
    created_at: str = field(default_factory=utc_now_iso)
    created_by: str | None = None
    approved_at: str | None = None
    approved_by: str | None = None
    rejected_at: str | None = None
    rejected_by: str | None = None
    rejection_reason: str | None = None
    executed_at: str | None = None
    verified_at: str | None = None
    expires_at: str | None = None
    rolled_back_at: str | None = None
    result: str | None = None
    dry_run_preview: str | None = None
    rollback_status: str | None = None
    reversible: bool = True
    inverse_action: str | None = None
    attack_type: str | None = None
    live_network_change: bool = False
    audit: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["approval_status"] = self._approval_status()
        data["execution_status"] = self.status
        data["pending_approval"] = self.status == ActionStatus.PROPOSED.value
        data["is_active"] = self.status == ActionStatus.ACTIVE.value
        return data

    def _approval_status(self) -> str:
        if self.status == ActionStatus.PROPOSED.value:
            return "PENDING_APPROVAL"
        if self.status == ActionStatus.REJECTED.value:
            return "REJECTED"
        if self.approved_at:
            return "APPROVED"
        return "N/A"

    def compute_expires_at(self) -> str | None:
        if self.duration_minutes <= 0:
            return None
        base = parse_iso(self.executed_at) or utc_now()
        return (base + timedelta(minutes=self.duration_minutes)).isoformat()


@dataclass
class AuditEvent:
    event: str
    action_id: str
    timestamp: str
    actor: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
