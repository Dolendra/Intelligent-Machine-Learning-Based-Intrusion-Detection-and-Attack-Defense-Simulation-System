"""Project-defined security rules for mitigation decision support."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RuleHit:
    rule_id: str
    attack_type: str
    min_severity: str
    action: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SEVERITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

# Declarative mitigation rules (project conventions — advisory only).
MITIGATION_RULES: list[dict[str, Any]] = [
    {
        "rule_id": "ddos-critical-upstream",
        "attack_type": "DDoS",
        "min_severity": "HIGH",
        "min_intensity": 0.7,
        "action": "UPSTREAM_FILTER",
        "reason": "High-intensity DDoS warrants upstream / edge filtering",
    },
    {
        "rule_id": "ddos-rate-limit",
        "attack_type": "DDoS",
        "min_severity": "MEDIUM",
        "min_intensity": 0.0,
        "action": "RATE_LIMIT",
        "reason": "Volumetric pressure should be rate-limited at the perimeter",
    },
    {
        "rule_id": "dos-rate-limit",
        "attack_type": "DoS",
        "min_severity": "MEDIUM",
        "min_intensity": 0.0,
        "action": "RATE_LIMIT",
        "reason": "DoS floods respond to rate limiting and signature filters",
    },
    {
        "rule_id": "portscan-block-source",
        "attack_type": "PortScan",
        "min_severity": "LOW",
        "min_intensity": 0.0,
        "action": "BLOCK_SOURCE",
        "reason": "Reconnaissance sources should be blocked or tarpitted",
    },
    {
        "rule_id": "bruteforce-auth-protect",
        "attack_type": "BruteForce",
        "min_severity": "MEDIUM",
        "min_intensity": 0.0,
        "action": "AUTH_LOCKOUT",
        "reason": "Repeated auth failures need lockout and MFA pressure",
    },
    {
        "rule_id": "web-waf",
        "attack_type": "WebAttack",
        "min_severity": "MEDIUM",
        "min_intensity": 0.0,
        "action": "WAF_TIGHTEN",
        "reason": "Application-layer attacks require WAF / input validation",
    },
    {
        "rule_id": "bot-isolate",
        "attack_type": "Bot",
        "min_severity": "HIGH",
        "min_intensity": 0.0,
        "action": "HOST_ISOLATE",
        "reason": "Bot C2 implies a compromised host that should be isolated",
    },
    {
        "rule_id": "infiltration-segment",
        "attack_type": "Infiltration",
        "min_severity": "HIGH",
        "min_intensity": 0.0,
        "action": "SEGMENT_ISOLATE",
        "reason": "Foothold scenarios need segment isolation and forensics",
    },
    {
        "rule_id": "critical-escalate",
        "attack_type": "*",
        "min_severity": "CRITICAL",
        "min_intensity": 0.0,
        "action": "ESCALATE_ANALYST",
        "reason": "Critical severity requires human SOC escalation",
    },
    {
        "rule_id": "uncertain-review",
        "attack_type": "*",
        "min_severity": "LOW",
        "min_intensity": 0.0,
        "require_uncertain": True,
        "action": "ANALYST_REVIEW",
        "reason": "Low model certainty — prefer analyst review before aggressive blocking",
    },
]


def _sev_ok(current: str, minimum: str) -> bool:
    return SEVERITY_RANK.get((current or "LOW").upper(), 0) >= SEVERITY_RANK.get(
        (minimum or "LOW").upper(), 0
    )


def evaluate_rules(
    *,
    attack_type: str,
    severity: str,
    is_attack: bool,
    traffic_intensity: float | None = None,
    certainty: str | None = None,
) -> list[RuleHit]:
    """Return matching mitigation rules for the current incident context."""
    if not is_attack or attack_type == "BENIGN":
        return [
            RuleHit(
                rule_id="benign-monitor",
                attack_type="BENIGN",
                min_severity="LOW",
                action="CONTINUE_MONITORING",
                reason="Benign traffic — maintain baseline observability",
            )
        ]

    intensity = 0.5 if traffic_intensity is None else max(0.0, min(1.0, float(traffic_intensity)))
    hits: list[RuleHit] = []
    for rule in MITIGATION_RULES:
        if rule.get("require_uncertain") and certainty != "uncertain":
            continue
        atk = rule["attack_type"]
        if atk != "*" and atk != attack_type:
            continue
        if not _sev_ok(severity, rule["min_severity"]):
            continue
        if intensity < float(rule.get("min_intensity", 0.0)):
            continue
        hits.append(
            RuleHit(
                rule_id=rule["rule_id"],
                attack_type=attack_type if atk == "*" else atk,
                min_severity=rule["min_severity"],
                action=rule["action"],
                reason=rule["reason"],
            )
        )
    return hits


def rule_actions(hits: list[RuleHit]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for h in hits:
        if h.action not in seen:
            seen.add(h.action)
            out.append(h.action)
    return out
