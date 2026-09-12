"""Attack-specific simulation scenario behaviors (visualization only)."""
from __future__ import annotations

from typing import Any, Callable, Protocol


class _Session(Protocol):
    attack_type: str
    edges: list[Any]
    nodes: list[Any]


def _set_edge(s: _Session, edge_id: str, **kwargs: Any) -> None:
    for e in s.edges:
        if e.id == edge_id:
            for k, v in kwargs.items():
                setattr(e, k, v)


def _node(s: _Session, node_id: str, **kwargs: Any) -> None:
    for n in s.nodes:
        if n.id == node_id:
            for k, v in kwargs.items():
                setattr(n, k, v)


def apply_ddos_start(s: _Session) -> str:
    for eid in ("e1", "e1b", "e1c", "e1d", "e2"):
        _set_edge(s, eid, traffic="malicious", intensity=0.9)
    for nid in ("attacker", "attacker2", "attacker3", "attacker4"):
        _node(s, nid, status="alert")
    _node(s, "firewall", status="stressed")
    return "Distributed flood begins from multiple bots toward the edge"


def apply_ddos_impact(s: _Session) -> str:
    for eid in ("e3", "e5"):
        _set_edge(s, eid, traffic="malicious", intensity=0.98)
    _node(s, "server", status="stressed")
    _node(s, "router", status="stressed")
    return "Server capacity saturated; service degradation under volumetric load"


def apply_dos_start(s: _Session) -> str:
    _set_edge(s, "e1", traffic="malicious", intensity=0.85)
    _set_edge(s, "e2", traffic="malicious", intensity=0.8)
    _node(s, "attacker", status="alert")
    _node(s, "firewall", status="stressed")
    return "Single-source DoS surge begins"


def apply_dos_impact(s: _Session) -> str:
    _set_edge(s, "e3", traffic="malicious", intensity=0.9)
    _set_edge(s, "e5", traffic="malicious", intensity=0.95)
    _node(s, "server", status="stressed")
    return "Target service overloaded by high-rate requests"


def apply_portscan_start(s: _Session) -> str:
    _set_edge(s, "e1", traffic="malicious", intensity=0.55)
    _set_edge(s, "e_scan", traffic="malicious", intensity=0.7)
    _node(s, "attacker", status="alert")
    _node(s, "ports", status="stressed")
    return "Reconnaissance probes across exposed ports (21/22/80/443/...)"


def apply_portscan_impact(s: _Session) -> str:
    _set_edge(s, "e2", traffic="malicious", intensity=0.6)
    _set_edge(s, "e4", traffic="malicious", intensity=0.5)
    _node(s, "ids", status="alert")
    return "Port sweep pattern visible to IDS sensor"


def apply_bruteforce_start(s: _Session) -> str:
    _set_edge(s, "e_auth", traffic="malicious", intensity=0.75)
    _node(s, "attacker", status="alert")
    _node(s, "auth", status="stressed")
    return "Repeated authentication attempts against login endpoint"


def apply_bruteforce_impact(s: _Session) -> str:
    _set_edge(s, "e_auth", traffic="malicious", intensity=0.9)
    _set_edge(s, "e2", traffic="malicious", intensity=0.5)
    return "Failed-login rate exceeds baseline; account abuse likely"


def apply_web_start(s: _Session) -> str:
    _set_edge(s, "e1", traffic="malicious", intensity=0.6)
    _set_edge(s, "e_waf", traffic="malicious", intensity=0.65)
    _node(s, "attacker", status="alert")
    _node(s, "waf", status="stressed")
    return "Malicious web payloads directed at application tier"


def apply_web_impact(s: _Session) -> str:
    _set_edge(s, "e_web", traffic="malicious", intensity=0.8)
    _node(s, "server", status="stressed")
    return "Injection/XSS patterns reach web application"


def apply_bot_start(s: _Session) -> str:
    _set_edge(s, "e_c2", traffic="malicious", intensity=0.7)
    _node(s, "pc01", status="alert")
    _node(s, "c2", status="alert")
    return "Compromised host begins C2 beaconing"


def apply_bot_impact(s: _Session) -> str:
    _set_edge(s, "e6", traffic="malicious", intensity=0.55)
    _set_edge(s, "e_c2", traffic="malicious", intensity=0.85)
    _node(s, "ids", status="alert")
    return "Botnet traffic and C2 channels observed on LAN"


def apply_generic_start(s: _Session) -> str:
    _set_edge(s, "e1", traffic="malicious", intensity=0.8)
    _set_edge(s, "e2", traffic="malicious", intensity=0.75)
    _node(s, "attacker", status="alert")
    _node(s, "firewall", status="stressed")
    return f"{s.attack_type} attack traffic begins"


def apply_generic_impact(s: _Session) -> str:
    _set_edge(s, "e3", traffic="malicious", intensity=0.9)
    _set_edge(s, "e5", traffic="malicious", intensity=0.9)
    _node(s, "server", status="stressed")
    return "Target components show stress under malicious load"


def apply_defense(s: _Session) -> str:
    atk = s.attack_type
    if atk == "PortScan":
        _set_edge(s, "e_scan", traffic="blocked", intensity=0.05)
        _set_edge(s, "e1", traffic="blocked", intensity=0.1)
        _node(s, "firewall", status="blocked")
        return "Scanner source blocked; monitoring heightened"
    if atk == "BruteForce":
        _set_edge(s, "e_auth", traffic="filtered", intensity=0.15)
        _node(s, "auth", status="ok")
        return "Auth rate limiting and lockouts simulated"
    if atk == "WebAttack":
        _set_edge(s, "e_waf", traffic="filtered", intensity=0.2)
        _set_edge(s, "e_web", traffic="normal", intensity=0.3)
        _node(s, "waf", status="blocked")
        _node(s, "server", status="ok")
        return "WAF rules drop malicious payloads"
    if atk == "Bot":
        _set_edge(s, "e_c2", traffic="blocked", intensity=0.05)
        _node(s, "pc01", status="isolated")
        return "Host isolated and C2 channel blocked"
    _set_edge(s, "e2", traffic="blocked", intensity=0.1)
    _set_edge(s, "e3", traffic="filtered", intensity=0.25)
    _set_edge(s, "e5", traffic="normal", intensity=0.3)
    for eid in ("e1b", "e1c", "e1d"):
        _set_edge(s, eid, traffic="blocked", intensity=0.05)
    _node(s, "firewall", status="blocked")
    _node(s, "server", status="ok")
    _node(s, "router", status="ok")
    return "Upstream filtering / rate limiting simulated at firewall"


ScenarioFns = dict[str, Callable[[_Session], str]]

START: ScenarioFns = {
    "DDoS": apply_ddos_start,
    "DoS": apply_dos_start,
    "PortScan": apply_portscan_start,
    "BruteForce": apply_bruteforce_start,
    "WebAttack": apply_web_start,
    "Bot": apply_bot_start,
}

IMPACT: ScenarioFns = {
    "DDoS": apply_ddos_impact,
    "DoS": apply_dos_impact,
    "PortScan": apply_portscan_impact,
    "BruteForce": apply_bruteforce_impact,
    "WebAttack": apply_web_impact,
    "Bot": apply_bot_impact,
}
