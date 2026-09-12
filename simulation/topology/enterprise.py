"""Enterprise topology builders for attack-defense simulation."""
from __future__ import annotations

from simulation.types import SimEdge, SimNode


def base_enterprise() -> tuple[list[SimNode], list[SimEdge]]:
    nodes = [
        SimNode("attacker", "Attacker", "attacker"),
        SimNode("internet", "Internet", "router"),
        SimNode("firewall", "Firewall", "firewall"),
        SimNode("router", "Core Router", "router"),
        SimNode("ids", "IDS Sensor", "ids"),
        SimNode("server", "App Server", "server"),
        SimNode("pc01", "PC-01", "client"),
        SimNode("pc02", "PC-02", "client"),
    ]
    edges = [
        SimEdge("e1", "attacker", "internet", "normal", 0.1),
        SimEdge("e2", "internet", "firewall", "normal", 0.2),
        SimEdge("e3", "firewall", "router", "normal", 0.2),
        SimEdge("e4", "router", "ids", "normal", 0.15),
        SimEdge("e5", "router", "server", "normal", 0.25),
        SimEdge("e6", "router", "pc01", "normal", 0.15),
        SimEdge("e7", "router", "pc02", "normal", 0.15),
    ]
    return nodes, edges


def ddos_topology() -> tuple[list[SimNode], list[SimEdge]]:
    nodes, edges = base_enterprise()
    # Extra distributed attackers for DDoS narrative
    nodes.extend(
        [
            SimNode("attacker2", "Bot-02", "attacker"),
            SimNode("attacker3", "Bot-03", "attacker"),
            SimNode("attacker4", "Bot-04", "attacker"),
        ]
    )
    edges.extend(
        [
            SimEdge("e1b", "attacker2", "internet", "normal", 0.1),
            SimEdge("e1c", "attacker3", "internet", "normal", 0.1),
            SimEdge("e1d", "attacker4", "internet", "normal", 0.1),
        ]
    )
    return nodes, edges


def portscan_topology() -> tuple[list[SimNode], list[SimEdge]]:
    nodes, edges = base_enterprise()
    nodes.append(SimNode("ports", "Port Surface", "server"))
    edges.append(SimEdge("e_scan", "attacker", "ports", "normal", 0.1))
    return nodes, edges


def bruteforce_topology() -> tuple[list[SimNode], list[SimEdge]]:
    nodes, edges = base_enterprise()
    nodes.append(SimNode("auth", "Auth Endpoint", "server"))
    edges.append(SimEdge("e_auth", "attacker", "auth", "normal", 0.15))
    return nodes, edges


def webattack_topology() -> tuple[list[SimNode], list[SimEdge]]:
    nodes, edges = base_enterprise()
    nodes.append(SimNode("waf", "WAF", "firewall"))
    edges = [
        SimEdge("e1", "attacker", "internet", "normal", 0.1),
        SimEdge("e2", "internet", "firewall", "normal", 0.2),
        SimEdge("e_waf", "firewall", "waf", "normal", 0.2),
        SimEdge("e_web", "waf", "server", "normal", 0.25),
        SimEdge("e4", "firewall", "ids", "normal", 0.15),
        SimEdge("e6", "router", "pc01", "normal", 0.1),
        SimEdge("e3", "firewall", "router", "normal", 0.1),
    ]
    return nodes, edges


def bot_topology() -> tuple[list[SimNode], list[SimEdge]]:
    nodes, edges = base_enterprise()
    nodes.append(SimNode("c2", "C2 Server", "attacker"))
    edges.append(SimEdge("e_c2", "pc01", "c2", "normal", 0.1))
    return nodes, edges


def topology_for(attack_type: str) -> tuple[list[SimNode], list[SimEdge]]:
    mapping = {
        "DDoS": ddos_topology,
        "DoS": base_enterprise,
        "PortScan": portscan_topology,
        "BruteForce": bruteforce_topology,
        "WebAttack": webattack_topology,
        "Bot": bot_topology,
    }
    return mapping.get(attack_type, base_enterprise)()
