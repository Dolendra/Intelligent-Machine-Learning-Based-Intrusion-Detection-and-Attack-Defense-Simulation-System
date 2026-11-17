"""Cyber-threat-intelligence context: map detected families to MITRE ATT&CK (Enterprise).

Every detection, recommendation, campaign and cyber-range incident can carry the ATT&CK tactic and
technique that best describes the observed behaviour, so an analyst can pivot to the shared
industry vocabulary (detections, mitigations, threat-actor reports) instead of a model's class name.

The mapping is a documented analyst judgement about what each CICIDS family *does*; it is not
learned. Technique IDs are from MITRE ATT&CK Enterprise (https://attack.mitre.org/).
"""
from __future__ import annotations

from typing import Any

# Kill-chain order of the tactics used below (ATT&CK Enterprise tactic order).
TACTIC_ORDER = ["TA0043", "TA0001", "TA0006", "TA0007", "TA0008", "TA0011", "TA0040"]

TACTICS = {
    "TA0043": "Reconnaissance",
    "TA0001": "Initial Access",
    "TA0006": "Credential Access",
    "TA0007": "Discovery",
    "TA0008": "Lateral Movement",
    "TA0011": "Command and Control",
    "TA0040": "Impact",
}

ATTACK_MAP: dict[str, dict[str, Any]] = {
    "PortScan": {"tactic": "TA0043", "technique": "T1595", "technique_name": "Active Scanning",
                 "also": [("T1046", "Network Service Discovery")]},
    "BruteForce": {"tactic": "TA0006", "technique": "T1110", "technique_name": "Brute Force",
                   "also": [("T1110.001", "Password Guessing")]},
    "WebAttack": {"tactic": "TA0001", "technique": "T1190", "technique_name": "Exploit Public-Facing Application",
                  "also": [("T1059.007", "JavaScript (XSS payloads)")]},
    "Infiltration": {"tactic": "TA0008", "technique": "T1021", "technique_name": "Remote Services",
                     "also": [("T1046", "Network Service Discovery")]},
    "Heartbleed": {"tactic": "TA0001", "technique": "T1190", "technique_name": "Exploit Public-Facing Application",
                   "also": [("T1212", "Exploitation for Credential Access")]},
    "Bot": {"tactic": "TA0011", "technique": "T1071", "technique_name": "Application Layer Protocol",
            "also": [("T1071.001", "Web Protocols")]},
    "DoS": {"tactic": "TA0040", "technique": "T1499", "technique_name": "Endpoint Denial of Service",
            "also": [("T1499.002", "Service Exhaustion Flood")]},
    "DDoS": {"tactic": "TA0040", "technique": "T1498", "technique_name": "Network Denial of Service",
             "also": [("T1498.001", "Direct Network Flood")]},
}


def attack_context(family: str | None) -> dict[str, Any] | None:
    """ATT&CK context for one detected family (None for benign/unknown labels)."""
    if not family or family not in ATTACK_MAP:
        return None
    m = ATTACK_MAP[family]
    return {
        "framework": "MITRE ATT&CK Enterprise",
        "tactic_id": m["tactic"],
        "tactic": TACTICS[m["tactic"]],
        "technique_id": m["technique"],
        "technique": m["technique_name"],
        "related": [{"technique_id": t, "technique": n} for t, n in m["also"]],
        "url": f"https://attack.mitre.org/techniques/{m['technique'].replace('.', '/')}/",
    }


def kill_chain(progression: list[str]) -> dict[str, Any]:
    """Summarise a campaign's family sequence as ATT&CK tactics and judge how far it got."""
    steps = []
    for fam in progression:
        ctx = attack_context(fam)
        if ctx and (not steps or steps[-1]["tactic_id"] != ctx["tactic_id"]):
            steps.append({"family": fam, "tactic_id": ctx["tactic_id"], "tactic": ctx["tactic"],
                          "technique_id": ctx["technique_id"]})
    reached = [s["tactic_id"] for s in steps]
    furthest = max(reached, key=TACTIC_ORDER.index) if reached else None
    ordered = reached == sorted(reached, key=TACTIC_ORDER.index)
    return {
        "steps": steps,
        "tactics_reached": len(set(reached)),
        "furthest_tactic": TACTICS.get(furthest) if furthest else None,
        "follows_kill_chain_order": ordered if len(reached) > 1 else None,
        "multi_stage": len(set(reached)) >= 2,
    }
