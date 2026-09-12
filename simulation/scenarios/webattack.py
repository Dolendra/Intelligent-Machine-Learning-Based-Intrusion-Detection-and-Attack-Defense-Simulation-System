"""WebAttack scenario behaviors."""
from __future__ import annotations

from simulation.scenarios.base import SessionLike, set_edge, set_node


def start(s: SessionLike) -> str:
    set_edge(s, "e1", traffic="malicious", intensity=0.6)
    set_edge(s, "e_waf", traffic="malicious", intensity=0.65)
    set_node(s, "attacker", status="alert")
    set_node(s, "waf", status="stressed")
    return "Malicious web payloads directed at application tier"


def impact(s: SessionLike) -> str:
    set_edge(s, "e_web", traffic="malicious", intensity=0.8)
    set_node(s, "server", status="stressed")
    return "Injection/XSS patterns reach web application"


def defend(s: SessionLike) -> str:
    set_edge(s, "e_waf", traffic="filtered", intensity=0.2)
    set_edge(s, "e_web", traffic="normal", intensity=0.3)
    set_node(s, "waf", status="blocked")
    set_node(s, "server", status="ok")
    return "WAF rules drop malicious payloads"
