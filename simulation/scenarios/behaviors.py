"""Attack scenario registry — re-exports START/IMPACT/defense for the engine."""
from __future__ import annotations

from typing import Callable

from simulation.scenarios import bot, bruteforce, ddos, dos, portscan, webattack
from simulation.scenarios.base import (
    SessionLike,
    apply_generic_impact,
    apply_generic_start,
    apply_volumetric_defense,
)

ScenarioFns = dict[str, Callable[[SessionLike], str]]

START: ScenarioFns = {
    "DDoS": ddos.start,
    "DoS": dos.start,
    "PortScan": portscan.start,
    "BruteForce": bruteforce.start,
    "WebAttack": webattack.start,
    "Bot": bot.start,
}

IMPACT: ScenarioFns = {
    "DDoS": ddos.impact,
    "DoS": dos.impact,
    "PortScan": portscan.impact,
    "BruteForce": bruteforce.impact,
    "WebAttack": webattack.impact,
    "Bot": bot.impact,
}

_DEFENSE: ScenarioFns = {
    "PortScan": portscan.defend,
    "BruteForce": bruteforce.defend,
    "WebAttack": webattack.defend,
    "Bot": bot.defend,
    "DDoS": apply_volumetric_defense,
    "DoS": apply_volumetric_defense,
}


def apply_defense(s: SessionLike) -> str:
    fn = _DEFENSE.get(s.attack_type, apply_volumetric_defense)
    return fn(s)


# Backward-compatible aliases used by older imports/tests
apply_ddos_start = ddos.start
apply_ddos_impact = ddos.impact
apply_dos_start = dos.start
apply_dos_impact = dos.impact
apply_portscan_start = portscan.start
apply_portscan_impact = portscan.impact
apply_bruteforce_start = bruteforce.start
apply_bruteforce_impact = bruteforce.impact
apply_web_start = webattack.start
apply_web_impact = webattack.impact
apply_bot_start = bot.start
apply_bot_impact = bot.impact
