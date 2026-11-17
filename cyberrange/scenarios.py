"""Scenario library for the trace-driven cyber range.

A scenario is data, not code: which attack families an attacker emits, at what rate, through which
stages, against which target, and how heavily each attack flow loads the target service. The engine
(``cyberrange.engine``) turns a scenario plus a seed into a reproducible run.

Stage names follow the locked pre-implementation state machine:
NORMAL → PREPARATION → RECONNAISSANCE → ATTACK_INITIATED → ATTACK_ACTIVE → (attack ends).
Detection-side states (SUSPICIOUS, DETECTED, EXPLAINED, RESPONSE_OPTIONS, MITIGATING, CONTAINED,
RECOVERY, COMPLETED) are driven by what the detectors actually see, not by the scenario script.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SCENARIO_VERSION = 1

# How many "service units" one flow of each family costs the target (benign = 1).
# Volumetric families are expensive; reconnaissance and beaconing are cheap. These are model
# parameters of the range, documented as such — not measurements.
FLOW_COST: dict[str, float] = {
    "BENIGN": 1.0, "DoS": 4.0, "DDoS": 4.0, "BruteForce": 1.5, "WebAttack": 1.5,
    "PortScan": 0.5, "Bot": 0.5, "Infiltration": 1.0, "Heartbleed": 1.0,
}

# Families the frozen detector and the gate were never trained on.
UNSEEN_FAMILIES = {"Infiltration", "Heartbleed"}


@dataclass(frozen=True)
class Stage:
    """One ground-truth attack stage. ``rate`` is a multiplier on the scenario's base attack rate."""

    name: str
    seconds: int
    families: dict[str, float] = field(default_factory=dict)  # family -> mixture weight
    rate: float = 0.0


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    family: str  # primary family (drives the recommended response)
    research_focus: str
    description: str
    base_rate: float  # attack flows per second per attacker at rate multiplier 1.0
    attackers: int
    target: str
    stages: tuple[Stage, ...]
    internal_attacker: bool = False
    difficulty: str = "medium"
    version: int = SCENARIO_VERSION

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["stages"] = [asdict(s) for s in self.stages]
        d["attack_seconds"] = sum(s.seconds for s in self.stages if s.rate > 0)
        return d


def _std(family: str, recon: bool = True, active: int = 40, init: int = 6) -> tuple[Stage, ...]:
    stages = [
        Stage("NORMAL", 12),
        Stage("PREPARATION", 3),
    ]
    if recon:
        stages.append(Stage("RECONNAISSANCE", 8, {"PortScan": 1.0}, 0.25))
    stages += [
        Stage("ATTACK_INITIATED", init, {family: 1.0}, 0.4),
        Stage("ATTACK_ACTIVE", active, {family: 1.0}, 1.0),
    ]
    return tuple(stages)


SCENARIOS: dict[str, Scenario] = {
    s.id: s
    for s in [
        Scenario(
            "port_scan", "Port scanning", "PortScan", "Early detection, false positives, feature importance",
            "An external host sweeps the web server's ports. Cheap for the server, but it precedes exploitation.",
            base_rate=14, attackers=1, target="web", stages=_std("PortScan", recon=False, active=40), difficulty="easy",
        ),
        Scenario(
            "host_discovery", "Host / service discovery", "PortScan", "Behavioural anomalies at low rate",
            "A slow, low-rate probe looking for live hosts and services — designed to stay under alert thresholds.",
            base_rate=3, attackers=1, target="web", stages=_std("PortScan", recon=False, active=45), difficulty="hard",
        ),
        Scenario(
            "brute_force", "Controlled brute force", "BruteForce", "Repeated authentication patterns",
            "Password guessing against FTP/SSH services after a short reconnaissance phase.",
            base_rate=10, attackers=1, target="auth", stages=_std("BruteForce"),
        ),
        Scenario(
            "dos", "Controlled DoS", "DoS", "Detection and mitigation latency",
            "A single host floods the web server with slow and expensive HTTP requests.",
            base_rate=24, attackers=1, target="web", stages=_std("DoS"),
        ),
        Scenario(
            "ddos", "Multi-source load (DDoS)", "DDoS", "Distributed behaviour and per-source attribution",
            "Four external sources flood the web server at once; each must be detected separately.",
            base_rate=10, attackers=4, target="web", stages=_std("DDoS", recon=False),
        ),
        Scenario(
            "web_burst", "Suspicious request burst", "WebAttack", "Rate / flow analysis of application attacks",
            "Bursts of SQL-injection, XSS and web brute-force requests against the web application.",
            base_rate=6, attackers=1, target="web", stages=_std("WebAttack"),
        ),
        Scenario(
            "bot_beacon", "Beacon-style periodic traffic", "Bot", "Temporal behaviour and XAI",
            "An infected internal workstation calls home to its command-and-control server at regular intervals.",
            base_rate=3, attackers=1, target="web", stages=_std("Bot", recon=False), internal_attacker=True,
            difficulty="hard",
        ),
        Scenario(
            "zero_day", "Zero-day intrusion (never-seen families)", "Infiltration",
            "Open-set detection of attack families absent from training",
            "Infiltration and Heartbleed traffic that neither detector was trained on, hidden in normal traffic.",
            base_rate=3, attackers=1, target="web",
            stages=(
                Stage("NORMAL", 12), Stage("PREPARATION", 3),
                Stage("ATTACK_INITIATED", 6, {"Infiltration": 1.0}, 0.5),
                Stage("ATTACK_ACTIVE", 40, {"Infiltration": 0.6, "Heartbleed": 0.4}, 1.0),
            ),
            difficulty="hard",
        ),
        Scenario(
            "apt_campaign", "Multi-stage campaign", "WebAttack", "Kill-chain progression across families",
            "Scan → brute force → web exploitation → botnet command-and-control from one actor.",
            base_rate=8, attackers=1, target="web",
            stages=(
                Stage("NORMAL", 12), Stage("PREPARATION", 3),
                Stage("RECONNAISSANCE", 10, {"PortScan": 1.0}, 0.6),
                Stage("ATTACK_INITIATED", 12, {"BruteForce": 1.0}, 0.8),
                Stage("ATTACK_ACTIVE", 30, {"WebAttack": 0.6, "Bot": 0.4}, 1.0),
            ),
            difficulty="hard",
        ),
    ]
}


def get_scenario(scenario_id: str) -> Scenario:
    if scenario_id not in SCENARIOS:
        raise KeyError(f"Unknown scenario {scenario_id!r}; choose one of {sorted(SCENARIOS)}")
    return SCENARIOS[scenario_id]


def catalog() -> list[dict[str, Any]]:
    return [s.to_dict() for s in SCENARIOS.values()]
