"""Shared helpers for attack scenario modules (visualization only)."""
from __future__ import annotations

from typing import Any, Callable, Protocol


class SessionLike(Protocol):
    attack_type: str
    edges: list[Any]
    nodes: list[Any]


ScenarioFn = Callable[[SessionLike], str]


def set_edge(s: SessionLike, edge_id: str, **kwargs: Any) -> None:
    for e in s.edges:
        if e.id == edge_id:
            for k, v in kwargs.items():
                setattr(e, k, v)


def set_node(s: SessionLike, node_id: str, **kwargs: Any) -> None:
    for n in s.nodes:
        if n.id == node_id:
            for k, v in kwargs.items():
                setattr(n, k, v)


def apply_generic_start(s: SessionLike) -> str:
    set_edge(s, "e1", traffic="malicious", intensity=0.8)
    set_edge(s, "e2", traffic="malicious", intensity=0.75)
    set_node(s, "attacker", status="alert")
    set_node(s, "firewall", status="stressed")
    return f"{s.attack_type} attack traffic begins"


def apply_generic_impact(s: SessionLike) -> str:
    set_edge(s, "e3", traffic="malicious", intensity=0.9)
    set_edge(s, "e5", traffic="malicious", intensity=0.9)
    set_node(s, "server", status="stressed")
    return "Target components show stress under malicious load"


def apply_volumetric_defense(s: SessionLike) -> str:
    set_edge(s, "e2", traffic="blocked", intensity=0.1)
    set_edge(s, "e3", traffic="filtered", intensity=0.25)
    set_edge(s, "e5", traffic="normal", intensity=0.3)
    for eid in ("e1b", "e1c", "e1d"):
        set_edge(s, eid, traffic="blocked", intensity=0.05)
    set_node(s, "firewall", status="blocked")
    set_node(s, "server", status="ok")
    set_node(s, "router", status="ok")
    return "Upstream filtering / rate limiting simulated at firewall"
