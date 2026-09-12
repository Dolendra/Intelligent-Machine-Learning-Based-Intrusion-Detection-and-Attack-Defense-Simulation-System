"""DoS scenario behaviors."""
from __future__ import annotations

from simulation.scenarios.base import SessionLike, set_edge, set_node


def start(s: SessionLike) -> str:
    set_edge(s, "e1", traffic="malicious", intensity=0.85)
    set_edge(s, "e2", traffic="malicious", intensity=0.8)
    set_node(s, "attacker", status="alert")
    set_node(s, "firewall", status="stressed")
    return "Single-source DoS surge begins"


def impact(s: SessionLike) -> str:
    set_edge(s, "e3", traffic="malicious", intensity=0.9)
    set_edge(s, "e5", traffic="malicious", intensity=0.95)
    set_node(s, "server", status="stressed")
    return "Target service overloaded by high-rate requests"
