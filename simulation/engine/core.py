"""Attack-defense simulation engine (visualization only — no real attacks)."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from security.recommendations.engine import recommend
from security.risk.engine import compute_risk
from simulation.types import SimEdge, SimNode
from simulation.scenarios.behaviors import IMPACT, START, apply_defense, apply_generic_impact, apply_generic_start
from simulation.topology.enterprise import topology_for

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
    narrative: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    incident_id: str | None = None
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
            "narrative": self.narrative,
            "metrics": self.metrics,
            "incident_id": self.incident_id,
            "created_at": self.created_at,
            "advisory_only": True,
            "disclaimer": "Controlled visualization only — not a real attack or live network control.",
        }


class SimulationEngine:
    """Stateful scenario player for attack → detect → defend → recover."""

    def __init__(self) -> None:
        self.sessions: dict[str, SimulationSession] = {}

    def start(
        self,
        attack_type: str = "DDoS",
        confidence: float = 0.96,
        incident_id: str | None = None,
        risk_score: float | None = None,
        severity: str | None = None,
        recommendation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        nodes, edges = topology_for(attack_type)
        risk = compute_risk(attack_type, confidence, is_attack=True, traffic_intensity=0.3)
        rec = recommendation or recommend(attack_type, severity or risk["severity"])
        session = SimulationSession(
            id=str(uuid.uuid4()),
            attack_type=attack_type,
            state="idle",
            risk_score=float(risk_score if risk_score is not None else risk["risk_score"]),
            severity=severity or risk["severity"],
            confidence=confidence,
            recommendation=rec,
            nodes=nodes,
            edges=edges,
            incident_id=incident_id,
            metrics={"peak_traffic": 0.2, "server_stress": 0.1, "traffic_blocked": 0.0},
        )
        session.timeline.append(
            {"event": "session_created", "state": "idle", "detail": f"Scenario: {attack_type}"}
        )
        session.narrative.append(f"Scenario prepared for {attack_type} (visualization only).")
        self.sessions[session.id] = session
        self._persist(session)
        return session.to_dict()

    def get(self, session_id: str) -> dict[str, Any]:
        return self._require(session_id).to_dict()

    def advance(self, session_id: str, action: str | None = None) -> dict[str, Any]:
        s = self._require(session_id)
        if action == "reset":
            return self.start(s.attack_type, s.confidence, s.incident_id, s.risk_score, s.severity, s.recommendation)
        if action == "defend" and s.state in ("detected", "recommended", "attack_impact"):
            if s.state != "recommended":
                self._to_recommended(s)
                s.state = "recommended"
            detail = apply_defense(s)
            s.timeline.append({"event": "defense_applied", "state": "defended", "detail": detail})
            s.narrative.append(detail)
            s.metrics["traffic_blocked"] = 0.84
            s.metrics["server_stress"] = max(0.1, s.metrics.get("server_stress", 0.9) * 0.28)
            s.state = "defended"
            self._persist(s)
            return s.to_dict()

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
        _next, fn = transitions[s.state]
        fn(s)
        s.state = _next
        self._persist(s)
        return s.to_dict()

    def _persist(self, s: SimulationSession) -> None:
        try:
            from database.db import SessionLocal, SimulationRecord

            db = SessionLocal()
            try:
                row = db.query(SimulationRecord).filter(SimulationRecord.session_id == s.id).first()
                payload = json.dumps(s.to_dict())
                if row is None:
                    db.add(
                        SimulationRecord(
                            session_id=s.id,
                            attack_type=s.attack_type,
                            state=s.state,
                            payload=payload,
                        )
                    )
                else:
                    row.state = s.state
                    row.payload = payload
                db.commit()
            finally:
                db.close()
        except Exception:
            # Persistence is best-effort for prototype; in-memory session remains source of truth for active process
            pass

    def _require(self, session_id: str) -> SimulationSession:
        if session_id not in self.sessions:
            # Try restore from DB
            try:
                from database.db import SessionLocal, SimulationRecord

                db = SessionLocal()
                try:
                    row = db.query(SimulationRecord).filter(SimulationRecord.session_id == session_id).first()
                    if row and row.payload:
                        data = json.loads(row.payload)
                        session = SimulationSession(
                            id=data["id"],
                            attack_type=data["attack_type"],
                            state=data["state"],
                            risk_score=data["risk_score"],
                            severity=data["severity"],
                            confidence=data["confidence"],
                            recommendation=data["recommendation"],
                            nodes=[SimNode(**n) for n in data["nodes"]],
                            edges=[SimEdge(**e) for e in data["edges"]],
                            timeline=data.get("timeline", []),
                            narrative=data.get("narrative", []),
                            metrics=data.get("metrics", {}),
                            incident_id=data.get("incident_id"),
                            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
                        )
                        self.sessions[session_id] = session
                        return session
                finally:
                    db.close()
            except Exception:
                pass
            raise KeyError(f"Unknown simulation session: {session_id}")
        return self.sessions[session_id]

    def _to_normal(self, s: SimulationSession) -> None:
        for e in s.edges:
            e.traffic = "normal"
            e.intensity = 0.2
        for n in s.nodes:
            n.status = "ok"
        detail = "Baseline client to server traffic"
        s.timeline.append({"event": "normal_traffic", "state": "normal", "detail": detail})
        s.narrative.append(detail)

    def _to_attack_start(self, s: SimulationSession) -> None:
        fn = START.get(s.attack_type, apply_generic_start)
        detail = fn(s)
        s.metrics["peak_traffic"] = 0.85
        s.timeline.append({"event": "attack_start", "state": "attack_start", "detail": detail})
        s.narrative.append(detail)

    def _to_attack_impact(self, s: SimulationSession) -> None:
        fn = IMPACT.get(s.attack_type, apply_generic_impact)
        detail = fn(s)
        risk = compute_risk(s.attack_type, s.confidence, True, traffic_intensity=0.95)
        s.risk_score = risk["risk_score"]
        s.severity = risk["severity"]
        s.metrics["peak_traffic"] = 0.95
        s.metrics["server_stress"] = 0.91
        s.timeline.append({"event": "impact", "state": "attack_impact", "detail": detail})
        s.narrative.append(detail)

    def _to_detected(self, s: SimulationSession) -> None:
        for n in s.nodes:
            if n.id == "ids":
                n.status = "alert"
        detail = f"IDS detected {s.attack_type} (confidence {s.confidence:.0%})"
        s.timeline.append({"event": "ids_alert", "state": "detected", "detail": detail})
        s.narrative.append(detail)

    def _to_recommended(self, s: SimulationSession) -> None:
        s.recommendation = recommend(s.attack_type, s.severity)
        detail = s.recommendation["primary"]
        s.timeline.append({"event": "recommendation", "state": "recommended", "detail": detail})
        s.narrative.append(f"Recommended response: {detail}")

    def _to_defended(self, s: SimulationSession) -> None:
        detail = apply_defense(s)
        s.metrics["traffic_blocked"] = 0.84
        s.metrics["server_stress"] = 0.25
        s.timeline.append({"event": "defense_applied", "state": "defended", "detail": detail})
        s.narrative.append(detail)

    def _to_recovered(self, s: SimulationSession) -> None:
        for n in s.nodes:
            if n.kind == "ids":
                n.status = "ok"
            if n.kind == "attacker":
                n.status = "ok"
        for e in s.edges:
            if e.traffic == "malicious":
                e.traffic = "blocked"
        s.risk_score = max(5.0, s.risk_score * 0.15)
        s.severity = "LOW"
        s.metrics["server_stress"] = 0.12
        detail = "Service restored; threat mitigated (simulated)"
        s.timeline.append({"event": "recovered", "state": "recovered", "detail": detail})
        s.narrative.append(detail)


simulation_engine = SimulationEngine()
