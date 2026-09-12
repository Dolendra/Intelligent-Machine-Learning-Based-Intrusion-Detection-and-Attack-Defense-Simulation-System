"""BruteForce scenario behaviors."""
from __future__ import annotations

from simulation.scenarios.base import SessionLike, set_edge, set_node


def start(s: SessionLike) -> str:
    set_edge(s, "e_auth", traffic="malicious", intensity=0.75)
    set_node(s, "attacker", status="alert")
    set_node(s, "auth", status="stressed")
    return "Repeated authentication attempts against login endpoint"


def impact(s: SessionLike) -> str:
    set_edge(s, "e_auth", traffic="malicious", intensity=0.9)
    set_edge(s, "e2", traffic="malicious", intensity=0.5)
    return "Failed-login rate exceeds baseline; account abuse likely"


def defend(s: SessionLike) -> str:
    set_edge(s, "e_auth", traffic="filtered", intensity=0.15)
    set_node(s, "auth", status="ok")
    return "Auth rate limiting and lockouts simulated"
