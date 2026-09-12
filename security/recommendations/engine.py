"""Map attack families to recommended defensive actions (decision support only)."""
from __future__ import annotations

from typing import Any

from security.rules import evaluate_rules, rule_actions

# Recommendations are advisory — the platform does not execute destructive network changes.
RECOMMENDATIONS: dict[str, dict[str, Any]] = {
    "BENIGN": {
        "actions": ["Continue monitoring", "No immediate containment required"],
        "primary": "Continue monitoring",
        "rationale": "Traffic classified as benign; maintain baseline observability.",
        "expected_effect": "No service impact.",
    },
    "DoS": {
        "actions": [
            "Apply rate limiting on affected service",
            "Filter anomalous flow signatures at the firewall",
            "Scale / shed non-critical load if capacity is exhausted",
        ],
        "primary": "Rate limiting / traffic filtering",
        "rationale": "DoS floods exhaust resources via high request or connection volume.",
        "expected_effect": "Malicious flow volume reduced; legitimate clients retain access.",
    },
    "DDoS": {
        "actions": [
            "Enable upstream / edge traffic filtering",
            "Apply rate limiting and SYN/connection controls",
            "Block or sinkhole high-volume source aggregates",
            "Engage ISP or CDN mitigation if available",
        ],
        "primary": "Upstream filtering + rate limiting",
        "rationale": "Distributed sources amplify volumetric pressure beyond a single host block.",
        "expected_effect": "Attack traffic dropped before saturating the origin server.",
    },
    "PortScan": {
        "actions": [
            "Block or tarpit the scanning source IP",
            "Increase monitoring on scanned hosts",
            "Verify exposed services and close unnecessary ports",
        ],
        "primary": "Block suspicious source / heighten monitoring",
        "rationale": "Port scans are reconnaissance preceding exploitation.",
        "expected_effect": "Scanner lose visibility; attack surface reduced.",
    },
    "BruteForce": {
        "actions": [
            "Enforce account lockout / progressive delays",
            "Rate-limit authentication endpoints",
            "Block source after repeated failures",
            "Require MFA where applicable",
        ],
        "primary": "Account protection + auth rate limiting",
        "rationale": "Credential stuffing and password guessing succeed via high attempt rates.",
        "expected_effect": "Guessing throughput collapses; accounts remain protected.",
    },
    "WebAttack": {
        "actions": [
            "Deploy / tighten WAF rules for SQLi/XSS patterns",
            "Validate and sanitize all user inputs",
            "Patch vulnerable application endpoints",
            "Temporarily block offending source IPs",
        ],
        "primary": "WAF rules + input validation",
        "rationale": "Web attacks target application-layer injection and abuse paths.",
        "expected_effect": "Malicious payloads blocked at the edge or app layer.",
    },
    "Bot": {
        "actions": [
            "Isolate the compromised host from the LAN",
            "Block C2 communication destinations",
            "Trigger endpoint malware scan / reimage",
        ],
        "primary": "Host isolation + C2 block",
        "rationale": "Bot traffic indicates a controlled endpoint phoning home.",
        "expected_effect": "Bot cannot receive commands or exfiltrate data.",
    },
    "Infiltration": {
        "actions": [
            "Isolate affected segment",
            "Preserve forensic evidence",
            "Rotate credentials and review lateral-movement paths",
            "Hunt for persistence mechanisms",
        ],
        "primary": "Segment isolation + incident response",
        "rationale": "Infiltration implies a foothold that may already be expanding.",
        "expected_effect": "Attacker movement contained while investigation proceeds.",
    },
    "Heartbleed": {
        "actions": [
            "Patch OpenSSL / affected TLS services immediately",
            "Revoke and reissue exposed certificates and secrets",
            "Block vulnerable service versions at the perimeter",
        ],
        "primary": "Emergency patch + secret rotation",
        "rationale": "Heartbleed can leak memory including keys and credentials.",
        "expected_effect": "Vulnerability closed; previously exposed secrets invalidated.",
    },
    "Other": {
        "actions": [
            "Increase monitoring on involved hosts",
            "Capture full packet context for analyst review",
            "Apply least-privilege network controls",
        ],
        "primary": "Heightened monitoring + analyst review",
        "rationale": "Unrecognized attack family requires cautious containment.",
        "expected_effect": "Analysts gain visibility before aggressive blocking.",
    },
}

_ACTION_LABELS = {
    "UPSTREAM_FILTER": "Enable upstream / edge traffic filtering",
    "RATE_LIMIT": "Apply rate limiting on affected paths",
    "BLOCK_SOURCE": "Block or tarpit the scanning source",
    "AUTH_LOCKOUT": "Enforce account lockout / auth rate limits",
    "WAF_TIGHTEN": "Tighten WAF rules for injection patterns",
    "HOST_ISOLATE": "Isolate the compromised host from the LAN",
    "SEGMENT_ISOLATE": "Isolate affected network segment",
    "ESCALATE_ANALYST": "Escalate to SOC analyst for critical response",
    "ANALYST_REVIEW": "Hold aggressive blocking — request analyst review",
    "CONTINUE_MONITORING": "Continue monitoring",
}

_SEVERITY_PRIMARY = {
    "CRITICAL": "Escalate containment and monitor recovery closely",
    "HIGH": "Apply primary containment immediately",
    "MEDIUM": "Apply measured containment and continue monitoring",
    "LOW": "Heighten monitoring; defer aggressive blocking if uncertain",
}


def recommend(
    attack_type: str,
    severity: str | None = None,
    *,
    confidence: float | None = None,
    traffic_intensity: float | None = None,
    certainty: str | None = None,
    is_attack: bool | None = None,
) -> dict[str, Any]:
    """Context-aware advisory recommendation using base playbooks + rule hits."""
    key = attack_type if attack_type in RECOMMENDATIONS else "Other"
    payload = dict(RECOMMENDATIONS[key])
    sev = (severity or "MEDIUM").upper()
    attack_flag = True if is_attack is None else bool(is_attack)
    if attack_type == "BENIGN":
        attack_flag = False

    hits = evaluate_rules(
        attack_type=attack_type,
        severity=sev,
        is_attack=attack_flag,
        traffic_intensity=traffic_intensity,
        certainty=certainty,
    )
    rule_codes = rule_actions(hits)
    rule_action_labels = [_ACTION_LABELS.get(a, a) for a in rule_codes]

    # Merge playbook actions with rule-driven actions (rules first for context).
    merged: list[str] = []
    for a in rule_action_labels + list(payload.get("actions", [])):
        if a not in merged:
            merged.append(a)

    # Severity / intensity can escalate the primary recommendation.
    primary = payload["primary"]
    if sev == "CRITICAL" and attack_flag:
        primary = merged[0] if merged else _SEVERITY_PRIMARY["CRITICAL"]
    elif certainty == "uncertain" and attack_flag:
        primary = "Analyst review (uncertain prediction)"
    elif traffic_intensity is not None and traffic_intensity >= 0.7 and attack_type in {"DDoS", "DoS"}:
        primary = "Upstream filtering + aggressive rate limiting"

    rationale = payload["rationale"]
    if confidence is not None:
        rationale += f" Model confidence={float(confidence):.2f}."
    if traffic_intensity is not None:
        rationale += f" Observed traffic intensity≈{float(traffic_intensity):.2f}."
    rationale += f" Severity band={sev}."

    payload["actions"] = merged
    payload["primary"] = primary
    payload["rationale"] = rationale
    payload["attack_type"] = attack_type
    payload["severity"] = sev
    payload["rule_hits"] = [h.to_dict() for h in hits]
    payload["rule_actions"] = rule_codes
    payload["advisory_only"] = True
    payload["disclaimer"] = (
        "These are recommended defensive actions for decision support. "
        "The platform does not automatically execute destructive network changes."
    )
    return payload
