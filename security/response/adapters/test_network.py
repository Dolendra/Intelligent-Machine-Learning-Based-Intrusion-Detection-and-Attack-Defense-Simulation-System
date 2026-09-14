"""Controlled test adapter — simulated control-plane state, not a real network."""
from __future__ import annotations

import threading
from typing import Any

from security.response.adapters.base import AdapterError, ResponseAdapter
from security.response.adapters.reversibility import inverse_action, is_reversible
from security.response.types import ActionType, ResponseAction


class TestNetworkAdapter(ResponseAdapter):
    """In-memory simulated blocks/rate-limits for lifecycle testing (P3)."""

    name = "test_network"
    touches_real_network = False

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # key: (action_type, target) -> meta
        self._controls: dict[tuple[str, str], dict[str, Any]] = {}
        # Test hooks (unit tests only)
        self.fail_next_execute = False
        self.fail_next_verify = False
        self.fail_next_rollback = False

    def reset(self) -> None:
        with self._lock:
            self._controls.clear()
            self.fail_next_execute = False
            self.fail_next_verify = False
            self.fail_next_rollback = False

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active_controls": [
                    {"action_type": k[0], "target": k[1], **v} for k, v in self._controls.items()
                ],
                "count": len(self._controls),
            }

    def validate(self, action: ResponseAction) -> dict[str, Any]:
        if not action.target or len(action.target) > 256:
            raise AdapterError("INVALID_TARGET", "invalid target")
        if action.action_type not in {m.value for m in ActionType}:
            raise AdapterError("INVALID_ACTION", f"unsupported {action.action_type}")
        if any(x in action.target for x in ("\n", "\r", ";", "|", "`")):
            raise AdapterError("INVALID_TARGET", "forbidden characters in target")
        return {"ok": True, "adapter": self.name}

    def preview(self, action: ResponseAction) -> dict[str, Any]:
        inv = inverse_action(action.action_type)
        return {
            "ok": True,
            "adapter": self.name,
            "live_network_change": False,
            "message": (
                f"[TEST] Would apply {action.action_type} to {action.target} "
                f"for {action.duration_minutes} minutes in simulated control plane."
            ),
            "reversible": is_reversible(action.action_type),
            "inverse_action": inv,
        }

    def execute(self, action: ResponseAction) -> dict[str, Any]:
        self.validate(action)
        if self.fail_next_execute:
            self.fail_next_execute = False
            raise AdapterError("ADAPTER_UNAVAILABLE", "TestNetworkAdapter simulated execute failure")

        if action.action_type == ActionType.ESCALATE.value:
            # Non-mutating escalation ticket in the test plane
            return {
                "ok": True,
                "adapter": self.name,
                "live_network_change": False,
                "message": f"[TEST] Escalated {action.target} to simulated SOC queue.",
                "state_applied": False,
                "reversible": False,
            }

        key = (action.action_type, action.target)
        with self._lock:
            self._controls[key] = {
                "action_id": action.action_id,
                "duration_minutes": action.duration_minutes,
                "active": True,
            }
        return {
            "ok": True,
            "adapter": self.name,
            "live_network_change": False,
            "message": (
                f"[TEST] Applied {action.action_type} to {action.target} "
                f"for {action.duration_minutes} minutes (simulated)."
            ),
            "state_applied": True,
            "state_key": {"action_type": action.action_type, "target": action.target},
            "reversible": is_reversible(action.action_type),
            "inverse_action": inverse_action(action.action_type),
        }

    def verify(self, action: ResponseAction) -> dict[str, Any]:
        if self.fail_next_verify:
            self.fail_next_verify = False
            raise AdapterError("VERIFY_FAILED", "TestNetworkAdapter simulated verification failure")

        if action.action_type == ActionType.ESCALATE.value:
            return {
                "ok": True,
                "verified": True,
                "adapter": self.name,
                "live_network_change": False,
                "message": "[TEST] Escalation recorded (no control-plane state).",
            }

        key = (action.action_type, action.target)
        with self._lock:
            meta = self._controls.get(key)
            present = bool(meta and meta.get("active") and meta.get("action_id") == action.action_id)
        if not present:
            raise AdapterError(
                "VERIFY_FAILED",
                f"Expected simulated control {action.action_type}/{action.target} not found",
            )
        return {
            "ok": True,
            "verified": True,
            "adapter": self.name,
            "live_network_change": False,
            "message": f"[TEST] Verified {action.action_type} active on {action.target}.",
            "state": meta,
        }

    def rollback(self, action: ResponseAction) -> dict[str, Any]:
        if self.fail_next_rollback:
            self.fail_next_rollback = False
            raise AdapterError("ROLLBACK_FAILED", "TestNetworkAdapter simulated rollback failure")
        if not is_reversible(action.action_type):
            raise AdapterError(
                "NOT_REVERSIBLE",
                f"{action.action_type} cannot be rolled back in the test adapter",
            )
        key = (action.action_type, action.target)
        inv = inverse_action(action.action_type)
        with self._lock:
            existed = key in self._controls
            self._controls.pop(key, None)
        return {
            "ok": True,
            "adapter": self.name,
            "live_network_change": False,
            "message": f"[TEST] Applied {inv} for {action.target} (cleared simulated control).",
            "inverse_action": inv,
            "cleared": existed,
        }

    def traffic_decision(self, source: str) -> dict[str, Any]:
        """Gate a simulated connection attempt against active CONTROLLED state.

        Used by the P11 empirical test plane — does **not** touch a real network.
        Precedence: BLOCK_SOURCE / ISOLATE_HOST → deny; RATE_LIMIT → throttle;
        otherwise allow.
        """
        src = (source or "").strip()
        with self._lock:
            for action_type, target in list(self._controls.keys()):
                meta = self._controls.get((action_type, target)) or {}
                if not meta.get("active"):
                    continue
                if target != src:
                    continue
                if action_type in {
                    ActionType.BLOCK_SOURCE.value,
                    ActionType.ISOLATE_HOST.value,
                }:
                    return {
                        "decision": "DENY",
                        "reason": action_type,
                        "target": target,
                        "action_id": meta.get("action_id"),
                    }
                if action_type == ActionType.RATE_LIMIT.value:
                    return {
                        "decision": "THROTTLE",
                        "reason": action_type,
                        "target": target,
                        "action_id": meta.get("action_id"),
                        "allow_fraction": 0.2,
                    }
                if action_type == ActionType.MONITOR.value:
                    return {
                        "decision": "ALLOW",
                        "reason": action_type,
                        "target": target,
                        "action_id": meta.get("action_id"),
                        "monitored": True,
                    }
        return {"decision": "ALLOW", "reason": None, "target": src}

    def capabilities(self) -> dict[str, Any]:
        base = super().capabilities()
        base.update({"simulated_control_plane": True, "state": self.snapshot()})
        return base


# Process-wide singleton for CONTROLLED mode
test_network_adapter = TestNetworkAdapter()
