"""Dry-run executor — never touches the network (P2 safety boundary)."""
from __future__ import annotations

from typing import Any

from security.response.types import ActionType, ExecutionMode, ResponseAction


class LiveAdapterForbiddenError(RuntimeError):
    """Raised if any code path attempts a live network change during P2."""


class LiveNetworkAdapter:
    """Stub for future firewall/EDR adapters — intentionally unusable in P2."""

    def apply(self, action: ResponseAction) -> dict[str, Any]:
        raise LiveAdapterForbiddenError(
            "Live network adapters are disabled in productionization P2. "
            "Use DRY_RUN mode only."
        )

    def rollback(self, action: ResponseAction) -> dict[str, Any]:
        raise LiveAdapterForbiddenError("Live rollback adapters are disabled in P2.")


class DryRunExecutor:
    """Produces human-readable would-be effects without side effects."""

    def execute(self, action: ResponseAction) -> dict[str, Any]:
        if action.mode != ExecutionMode.DRY_RUN.value:
            raise LiveAdapterForbiddenError(
                f"Executor refused mode={action.mode}; only DRY_RUN is allowed in P2"
            )
        preview = self.preview(action)
        return {
            "ok": True,
            "mode": ExecutionMode.DRY_RUN.value,
            "live_network_change": False,
            "message": preview,
            "action_type": action.action_type,
            "target": action.target,
            "duration_minutes": action.duration_minutes,
        }

    def preview(self, action: ResponseAction) -> str:
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

    def verify(self, action: ResponseAction) -> dict[str, Any]:
        """Dry-run verification always confirms no network change occurred."""
        return {
            "ok": True,
            "verified": True,
            "live_network_change": False,
            "message": "Verified dry-run: no real network change was performed.",
            "action_id": action.action_id,
        }
