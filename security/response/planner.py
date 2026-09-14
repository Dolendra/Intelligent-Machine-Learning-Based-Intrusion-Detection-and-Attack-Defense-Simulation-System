"""Map detections / recommendations to abstract response actions."""
from __future__ import annotations

from typing import Any

from security.response.types import ActionType

# Prefer rule codes when present; otherwise attack-family defaults.
_ATTACK_DEFAULT: dict[str, ActionType] = {
    "BENIGN": ActionType.MONITOR,
    "DoS": ActionType.RATE_LIMIT,
    "DDoS": ActionType.BLOCK_SOURCE,
    "PortScan": ActionType.BLOCK_SOURCE,
    "BruteForce": ActionType.RATE_LIMIT,
    "WebAttack": ActionType.BLOCK_SOURCE,
    "Bot": ActionType.ISOLATE_HOST,
    "Infiltration": ActionType.ISOLATE_HOST,
    "Heartbleed": ActionType.ESCALATE,
    "Other": ActionType.ESCALATE,
}

_RULE_TO_ACTION: dict[str, ActionType] = {
    "RATE_LIMIT": ActionType.RATE_LIMIT,
    "BLOCK_SOURCE": ActionType.BLOCK_SOURCE,
    "HOST_ISOLATE": ActionType.ISOLATE_HOST,
    "SEGMENT_ISOLATE": ActionType.ISOLATE_HOST,
    "UPSTREAM_FILTER": ActionType.RATE_LIMIT,
    "AUTH_LOCKOUT": ActionType.RATE_LIMIT,
    "WAF_TIGHTEN": ActionType.BLOCK_SOURCE,
    "ESCALATE_ANALYST": ActionType.ESCALATE,
    "ANALYST_REVIEW": ActionType.ESCALATE,
    "CONTINUE_MONITORING": ActionType.MONITOR,
}

_DEFAULT_DURATION: dict[str, int] = {
    ActionType.MONITOR.value: 60,
    ActionType.RATE_LIMIT.value: 30,
    ActionType.BLOCK_SOURCE.value: 15,
    ActionType.ISOLATE_HOST.value: 60,
    ActionType.ESCALATE.value: 0,
}


def plan_action_type(
    attack_type: str,
    *,
    rule_actions: list[str] | None = None,
    severity: str | None = None,
) -> ActionType:
    """Primary abstract action from attack family (rule codes are advisory context only)."""
    base = _ATTACK_DEFAULT.get(attack_type, ActionType.ESCALATE)
    if (severity or "").upper() == "CRITICAL" and base == ActionType.MONITOR:
        return ActionType.ESCALATE
    # If family default is soft monitoring but rules demand containment, escalate mapping.
    for code in rule_actions or []:
        mapped = _RULE_TO_ACTION.get(str(code).upper())
        if mapped in {ActionType.BLOCK_SOURCE, ActionType.ISOLATE_HOST, ActionType.RATE_LIMIT}:
            if base == ActionType.MONITOR or base == ActionType.ESCALATE:
                return mapped
    return base


def default_duration_minutes(action_type: str | ActionType) -> int:
    key = action_type.value if isinstance(action_type, ActionType) else str(action_type)
    return int(_DEFAULT_DURATION.get(key, 15))


def default_target(*, action_type: ActionType, source_ip: str | None, host: str | None) -> str:
    if action_type == ActionType.ISOLATE_HOST:
        return host or source_ip or "unknown-host"
    if action_type == ActionType.MONITOR:
        return source_ip or host or "network-segment"
    if action_type == ActionType.ESCALATE:
        return "soc-queue"
    return source_ip or host or "unknown-source"


def build_proposal_fields(
    *,
    attack_type: str,
    severity: str | None = None,
    risk_score: float | None = None,
    recommendation: dict[str, Any] | None = None,
    source_ip: str | None = None,
    host: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    rec = recommendation or {}
    action_type = plan_action_type(
        attack_type,
        rule_actions=list(rec.get("rule_actions") or []),
        severity=severity or rec.get("severity"),
    )
    duration = default_duration_minutes(action_type)
    target = default_target(action_type=action_type, source_ip=source_ip, host=host)
    why = reason or rec.get("primary") or rec.get("rationale") or f"Response for {attack_type}"
    return {
        "action_type": action_type.value,
        "target": target,
        "reason": str(why),
        "duration_minutes": duration,
        "severity": (severity or rec.get("severity") or "MEDIUM"),
        "risk_score": risk_score,
        "attack_type": attack_type,
    }
