"""PortScan scenario behaviors."""
from __future__ import annotations

from simulation.scenarios.base import SessionLike, set_edge, set_node


def start(s: SessionLike) -> str:
    set_edge(s, "e1", traffic="malicious", intensity=0.55)
    set_edge(s, "e_scan", traffic="malicious", intensity=0.7)
    set_node(s, "attacker", status="alert")
    set_node(s, "ports", status="stressed")
    return "Reconnaissance probes across exposed ports (21/22/80/443/...)"


def impact(s: SessionLike) -> str:
    set_edge(s, "e2", traffic="malicious", intensity=0.6)
    set_edge(s, "e4", traffic="malicious", intensity=0.5)
    set_node(s, "ids", status="alert")
    return "Port sweep pattern visible to IDS sensor"


def defend(s: SessionLike) -> str:
    set_edge(s, "e_scan", traffic="blocked", intensity=0.05)
    set_edge(s, "e1", traffic="blocked", intensity=0.1)
    set_node(s, "firewall", status="blocked")
    return "Scanner source blocked; monitoring heightened"
