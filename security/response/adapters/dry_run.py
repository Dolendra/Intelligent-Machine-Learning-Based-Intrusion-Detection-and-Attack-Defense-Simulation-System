"""Dry-run adapter — never mutates any network or simulated control plane."""
from __future__ import annotations

from typing import Any

from security.response.adapters.base import AdapterError, ResponseAdapter
from security.response.adapters.reversibility import inverse_action, is_reversible
from security.response.types import ActionType, ExecutionMode, ResponseAction


class DryRunAdapter(ResponseAdapter):
    name = "dry_run"
    touches_real_network = False

    def validate(self, action: ResponseAction) -> dict[str, Any]:
        if not action.target:
            raise AdapterError("INVALID_TARGET", "target required")
        if action.action_type not in {m.value for m in ActionType}:
            raise AdapterError("INVALID_ACTION", f"unsupported {action.action_type}")
        return {"ok": True, "adapter": self.name}

    def preview(self, action: ResponseAction) -> dict[str, Any]:
        msg = self._preview_message(action)
        return {
            "ok": True,
            "adapter": self.name,
            "mode": ExecutionMode.DRY_RUN.value,
            "live_network_change": False,
            "message": msg,
            "reversible": is_reversible(action.action_type),
            "inverse_action": inverse_action(action.action_type),
        }

    def execute(self, action: ResponseAction) -> dict[str, Any]:
        self.validate(action)
        preview = self.preview(action)
        return {
            "ok": True,
            "adapter": self.name,
            "mode": ExecutionMode.DRY_RUN.value,
            "live_network_change": False,
            "message": preview["message"],
            "action_type": action.action_type,
            "target": action.target,
            "duration_minutes": action.duration_minutes,
            "state_applied": False,
        }

    def verify(self, action: ResponseAction) -> dict[str, Any]:
        return {
            "ok": True,
            "verified": True,
            "adapter": self.name,
            "live_network_change": False,
            "message": "Verified dry-run: no real or simulated network change was performed.",
            "action_id": action.action_id,
        }

    def rollback(self, action: ResponseAction) -> dict[str, Any]:
        if not is_reversible(action.action_type):
            raise AdapterError(
                "NOT_REVERSIBLE",
                f"{action.action_type} is not reversible; rollback is not pretend-applied.",
            )
        inv = inverse_action(action.action_type)
        return {
            "ok": True,
            "adapter": self.name,
            "live_network_change": False,
            "message": f"Dry-run rollback: would apply {inv} for {action.target} (no state to clear).",
            "inverse_action": inv,
        }

    def _preview_message(self, action: ResponseAction) -> str:
        t = action.action_type
        target = action.target
        mins = action.duration_minutes
        if t == ActionType.BLOCK_SOURCE.value:
            return f"Would block source {target} for {mins} minutes."
        if t == ActionType.RATE_LIMIT.value:
            return f"Would rate-limit traffic from/to {target} for {mins} minutes."
        if t == ActionType.ISOLATE_HOST.value:
            return f"Would isolate host {target} for {mins} minutes."
        if t == ActionType.MONITOR.value:
            return f"Would increase monitoring on {target} for {mins} minutes."
        if t == ActionType.ESCALATE.value:
            return f"Would escalate incident to SOC queue ({target}); no automatic containment."
        return f"Would apply {t} to {target} (dry-run)."
