"""Bot scenario behaviors."""
from __future__ import annotations

from simulation.scenarios.base import SessionLike, set_edge, set_node


def start(s: SessionLike) -> str:
    set_edge(s, "e_c2", traffic="malicious", intensity=0.7)
    set_node(s, "pc01", status="alert")
    set_node(s, "c2", status="alert")
    return "Compromised host begins C2 beaconing"


def impact(s: SessionLike) -> str:
    set_edge(s, "e6", traffic="malicious", intensity=0.55)
    set_edge(s, "e_c2", traffic="malicious", intensity=0.85)
    set_node(s, "ids", status="alert")
    return "Botnet traffic and C2 channels observed on LAN"


def defend(s: SessionLike) -> str:
    set_edge(s, "e_c2", traffic="blocked", intensity=0.05)
    set_node(s, "pc01", status="isolated")
    return "Host isolated and C2 channel blocked"
