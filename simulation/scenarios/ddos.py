"""DDoS scenario behaviors."""
from __future__ import annotations

from simulation.scenarios.base import SessionLike, set_edge, set_node


def start(s: SessionLike) -> str:
    for eid in ("e1", "e1b", "e1c", "e1d", "e2"):
        set_edge(s, eid, traffic="malicious", intensity=0.9)
    for nid in ("attacker", "attacker2", "attacker3", "attacker4"):
        set_node(s, nid, status="alert")
    set_node(s, "firewall", status="stressed")
    return "Distributed flood begins from multiple bots toward the edge"


def impact(s: SessionLike) -> str:
    for eid in ("e3", "e5"):
        set_edge(s, eid, traffic="malicious", intensity=0.98)
    set_node(s, "server", status="stressed")
    set_node(s, "router", status="stressed")
    return "Server capacity saturated; service degradation under volumetric load"
