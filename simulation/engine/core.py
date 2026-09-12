"""Attack–defense simulation engine (visualization only — no real attacks)."""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from security.recommendations.engine import recommend
from security.risk.engine import compute_risk

SimState = Literal[
    "idle",
    "normal",
    "attack_start",
    "attack_impact",
    "detected",
    "recommended",
    "defended",
    "recovered",
]


@dataclass
class SimNode:
    id: str
    label: str
    kind: str  # attacker | firewall | router | server | client | ids
    status: str = "ok"  # ok | stressed | blocked | isolated | alert


@dataclass
class SimEdge:
    id: str
    source: str
    target: str
    traffic: str = "normal"  # normal | malicious | blocked | filtered
    intensity: float = 0.2


@dataclass
class SimulationSession:
    id: str
    attack_type: str
    state: SimState
    risk_score: float
    severity: str
    confidence: float
    recommendation: dict[str, Any]
    nodes: list[SimNode]
    edges: list[SimEdge]
    timeline: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "attack_type": self.attack_type,
            "state": self.state,
            "risk_score": self.risk_score,
            "severity": self.severity,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [asdict(e) for e in self.edges],
            "timeline": self.timeline,
            "created_at": self.created_at,
            "advisory_only": True,
        }


def _enterprise_topology() -> tuple[list[SimNode], list[SimEdge]]:
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


class SimulationEngine:
    """Stateful scenario player for attack → detect → defend → recover."""

    def __init__(self) -> None:
        self.sessions: dict[str, SimulationSession] = {}

    def start(
        self,
        attack_type: str = "DDoS",
        confidence: float = 0.96,
    ) -> dict[str, Any]:
        nodes, edges = _enterprise_topology()
        risk = compute_risk(attack_type, confidence, is_attack=True, traffic_intensity=0.3)
        rec = recommend(attack_type, risk["severity"])
        session = SimulationSession(
            id=str(uuid.uuid4()),
            attack_type=attack_type,
            state="idle",
            risk_score=risk["risk_score"],
            severity=risk["severity"],
            confidence=confidence,
            recommendation=rec,
            nodes=nodes,
            edges=edges,
        )
        session.timeline.append({"event": "session_created", "state": "idle", "detail": f"Scenario: {attack_type}"})
        self.sessions[session.id] = session
        return session.to_dict()

    def get(self, session_id: str) -> dict[str, Any]:
        return self._require(session_id).to_dict()

    def advance(self, session_id: str, action: str | None = None) -> dict[str, Any]:
        s = self._require(session_id)
        transitions = {
            "idle": ("normal", self._to_normal),
            "normal": ("attack_start", self._to_attack_start),
            "attack_start": ("attack_impact", self._to_attack_impact),
            "attack_impact": ("detected", self._to_detected),
            "detected": ("recommended", self._to_recommended),
            "recommended": ("defended", self._to_defended),
            "defended": ("recovered", self._to_recovered),
            "recovered": ("recovered", self._to_recovered),
        }
        if action == "reset":
            return self.start(s.attack_type, s.confidence)
        if action == "defend" and s.state in ("detected", "recommended"):
            s.state = "recommended"
            self._to_defended(s)
            s.state = "defended"
            return s.to_dict()

        _next, fn = transitions[s.state]
        fn(s)
        s.state = _next
        return s.to_dict()

    def _require(self, session_id: str) -> SimulationSession:
        if session_id not in self.sessions:
            raise KeyError(f"Unknown simulation session: {session_id}")
        return self.sessions[session_id]

    def _set_edge(self, s: SimulationSession, edge_id: str, **kwargs: Any) -> None:
        for e in s.edges:
            if e.id == edge_id:
                for k, v in kwargs.items():
                    setattr(e, k, v)

    def _node(self, s: SimulationSession, node_id: str, **kwargs: Any) -> None:
        for n in s.nodes:
            if n.id == node_id:
                for k, v in kwargs.items():
                    setattr(n, k, v)

    def _to_normal(self, s: SimulationSession) -> None:
        for e in s.edges:
            e.traffic = "normal"
            e.intensity = 0.2
        for n in s.nodes:
            n.status = "ok"
        s.timeline.append({"event": "normal_traffic", "state": "normal", "detail": "Baseline client ↔ server traffic"})

    def _to_attack_start(self, s: SimulationSession) -> None:
        self._set_edge(s, "e1", traffic="malicious", intensity=0.85)
        self._set_edge(s, "e2", traffic="malicious", intensity=0.8)
        self._node(s, "attacker", status="alert")
        self._node(s, "firewall", status="stressed")
        s.timeline.append({"event": "attack_start", "state": "attack_start", "detail": f"{s.attack_type} traffic surge begins"})

    def _to_attack_impact(self, s: SimulationSession) -> None:
        for eid in ("e3", "e5"):
            self._set_edge(s, eid, traffic="malicious", intensity=0.95)
        self._node(s, "server", status="stressed")
        self._node(s, "router", status="stressed")
        risk = compute_risk(s.attack_type, s.confidence, True, traffic_intensity=0.95)
        s.risk_score = risk["risk_score"]
        s.severity = risk["severity"]
        s.timeline.append({"event": "impact", "state": "attack_impact", "detail": "Target service degraded under malicious load"})

    def _to_detected(self, s: SimulationSession) -> None:
        self._node(s, "ids", status="alert")
        s.timeline.append(
            {
                "event": "ids_alert",
                "state": "detected",
                "detail": f"IDS detected {s.attack_type} (confidence {s.confidence:.0%})",
            }
        )

    def _to_recommended(self, s: SimulationSession) -> None:
        s.recommendation = recommend(s.attack_type, s.severity)
        s.timeline.append(
            {
                "event": "recommendation",
                "state": "recommended",
                "detail": s.recommendation["primary"],
            }
        )

    def _to_defended(self, s: SimulationSession) -> None:
        self._set_edge(s, "e2", traffic="blocked", intensity=0.1)
        self._set_edge(s, "e3", traffic="filtered", intensity=0.25)
        self._set_edge(s, "e5", traffic="normal", intensity=0.3)
        self._node(s, "firewall", status="blocked")
        self._node(s, "server", status="ok")
        self._node(s, "router", status="ok")
        s.timeline.append({"event": "defense_applied", "state": "defended", "detail": "Recommended controls simulated at firewall"})

    def _to_recovered(self, s: SimulationSession) -> None:
        self._node(s, "ids", status="ok")
        self._node(s, "attacker", status="ok")
        for e in s.edges:
            if e.traffic == "malicious":
                e.traffic = "blocked"
        s.risk_score = max(5.0, s.risk_score * 0.15)
        s.severity = "LOW"
        s.timeline.append({"event": "recovered", "state": "recovered", "detail": "Service restored; threat mitigated (simulated)"})


# Process-wide singleton used by the API
simulation_engine = SimulationEngine()
