"""Inverse / reversibility map for abstract response actions."""
from __future__ import annotations

from security.response.types import ActionType

# Reversible pairs (action → inverse label used in audit / test adapter)
INVERSE_ACTIONS: dict[str, str] = {
    ActionType.BLOCK_SOURCE.value: "UNBLOCK_SOURCE",
    ActionType.RATE_LIMIT.value: "REMOVE_RATE_LIMIT",
    ActionType.ISOLATE_HOST.value: "REJOIN_HOST",
    ActionType.MONITOR.value: "STOP_MONITOR",
}

# Explicitly non-reversible (no pretend rollback)
NON_REVERSIBLE: set[str] = {
    ActionType.ESCALATE.value,
}


def is_reversible(action_type: str) -> bool:
    return action_type in INVERSE_ACTIONS and action_type not in NON_REVERSIBLE


def inverse_action(action_type: str) -> str | None:
    if action_type in NON_REVERSIBLE:
        return None
    return INVERSE_ACTIONS.get(action_type)
