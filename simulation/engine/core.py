"""Attack-defense simulation engine (visualization only — no real attacks)."""
from __future__ import annotations

import json
import time
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

_PHASE_LABELS = {
    "normal": "Normal",
    "attack_start": "Attack begins",
    "attack_impact": "Traffic spike",
    "detected": "IDS alert",
    "recommended": "Recommendation",
    "defended": "Defense",
    "recovered": "Recovery",
}

# Deterministic simulated seconds advanced on each phase (not wall-clock).
_PHASE_DT = {
    "idle": 0.0,
    "normal": 0.0,
    "attack_start": 2.0,
    "attack_impact": 2.0,
    "detected": 2.0,
    "recommended": 2.0,
    "defended": 2.0,
    "recovered": 4.0,
}


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
    campaign_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        series = self.metrics.get("series") or {"labels": [], "with_defense": {}, "without_defense": {}}
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
            "series": series,
            "comparison": {
                "without_defense": {
                    "peak_traffic": self.metrics.get(
                        "no_defense_peak_traffic", self.metrics.get("peak_traffic", 0)
                    ),
                    "server_stress": self.metrics.get(
                        "no_defense_server_stress",
                        self.metrics.get("attack_server_stress", self.metrics.get("server_stress", 0)),
                    ),
                    "risk": self.metrics.get("no_defense_risk", self.metrics.get("attack_risk", self.risk_score)),
                    "threat": "ACTIVE",
                },
                "with_defense": {
                    "peak_traffic": round(
                        float(self.metrics.get("peak_traffic", 0))
                        * (1 - float(self.metrics.get("traffic_blocked", 0))),
                        3,
                    )
                    if self.state in ("defended", "recovered")
                    else self.metrics.get("peak_traffic", 0),
                    "server_stress": self.metrics.get("server_stress", 0),
                    "risk": self.risk_score,
                    "traffic_blocked": self.metrics.get("traffic_blocked", 0),
                    "threat": "CONTAINED" if self.state in ("defended", "recovered") else "PENDING",
                },
            },
            "latencies": {
                "detection_s": self.metrics.get("detection_latency_s", self.metrics.get("detection_delay_s")),
                "defense_s": self.metrics.get("defense_latency_s", self.metrics.get("defense_delay_s")),
                "recovery_s": self.metrics.get("recovery_time_s"),
                "attack_to_recover_s": self.metrics.get("time_to_recover_s"),
            },
            "phase_guide": self._phase_guide(),
            "incident_id": self.incident_id,
            "campaign_id": self.campaign_id,
            "campaign_progression": self.metrics.get("campaign_progression"),
            "created_at": self.created_at,
            "advisory_only": True,
            "disclaimer": (
                "Controlled visualization only — not a real attack or live network control. "
                "Phase timings use deterministic simulation_time (not wall-clock). "
                "Defense effectiveness values are simulation assumptions for comparative "
                "visualization, not empirically measured real-world mitigation rates."
            ),
        }

    def _phase_guide(self) -> list[dict[str, str]]:
        order = [
            "normal",
            "attack_start",
            "attack_impact",
            "detected",
            "recommended",
            "defended",
            "recovered",
        ]
        guide = []
        for state in order:
            key = f"phase_{state}_at_s"
            if key in self.metrics:
                t = f"{float(self.metrics[key]):.1f}s"
            else:
                fallback = {
                    "normal": "00s",
                    "attack_start": "02s",
                    "attack_impact": "04s",
                    "detected": "06s",
                    "recommended": "08s",
                    "defended": "10s",
                    "recovered": "12s",
                }
                t = fallback[state]
            guide.append({"t": t, "label": _PHASE_LABELS[state], "state": state})
        return guide


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
        traffic_intensity: float | None = None,
        asset_criticality: float | None = None,
        campaign_id: str | None = None,
        campaign_progression: list[str] | None = None,
    ) -> dict[str, Any]:
        nodes, edges = topology_for(attack_type)
        # Mild dynamic topology cue: mark primary target under higher intensity
        intensity = float(traffic_intensity if traffic_intensity is not None else 0.55)
        intensity = max(0.05, min(1.0, intensity))
        for n in nodes:
            if n.kind in {"server", "web", "db"} and intensity >= 0.75:
                n.label = f"{n.label} (critical)"
        risk = compute_risk(
            attack_type,
            confidence,
            is_attack=True,
            traffic_intensity=intensity,
            asset_criticality=asset_criticality,
        )
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
            campaign_id=campaign_id,
            metrics={
                "peak_traffic": 0.2,
                "server_stress": 0.1,
                "traffic_blocked": 0.0,
                "configured_intensity": round(intensity, 3),
                "asset_criticality": asset_criticality,
                "t0_epoch": time.time(),
                "simulation_time": 0.0,
                "timing_mode": "deterministic_simulation_time",
                "series": {
                    "labels": [],
                    "with_defense": {"traffic": [], "stress": [], "risk": []},
                    "without_defense": {"traffic": [], "stress": [], "risk": []},
                },
                "campaign_progression": list(campaign_progression or []),
            },
        )
        self._log(session, "session_created", "idle", f"Scenario: {attack_type}", dt=0.0)
        session.narrative.append(
            f"Scenario prepared for {attack_type} (intensity={intensity:.2f}, visualization only)."
        )
        if campaign_id:
            session.narrative.append(
                f"Campaign {campaign_id} progression: {' → '.join(campaign_progression or [attack_type])}"
            )
        self.sessions[session.id] = session
        self._persist(session)
        return session.to_dict()

    def start_campaign(
        self,
        campaign_id: str,
        progression: list[str],
        confidence: float = 0.92,
        traffic_intensity: float = 0.8,
    ) -> dict[str, Any]:
        """Start a controlled sim seeded by a campaign's attack progression."""
        attacks = [a for a in progression if a and a != "BENIGN"]
        primary = attacks[-1] if attacks else "DDoS"
        return self.start(
            attack_type=primary,
            confidence=confidence,
            traffic_intensity=traffic_intensity,
            campaign_id=campaign_id,
            campaign_progression=attacks or [primary],
        )

    def get(self, session_id: str) -> dict[str, Any]:
        return self._require(session_id).to_dict()

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        """Recent persisted simulations for replay."""
        try:
            from database.db import SessionLocal, SimulationRecord

            db = SessionLocal()
            try:
                rows = (
                    db.query(SimulationRecord)
                    .order_by(SimulationRecord.created_at.desc())
                    .limit(limit)
                    .all()
                )
                items = []
                for row in rows:
                    items.append(
                        {
                            "session_id": row.session_id,
                            "attack_type": row.attack_type,
                            "state": row.state,
                            "created_at": row.created_at.isoformat() if row.created_at else None,
                        }
                    )
                return items
            finally:
                db.close()
        except Exception as exc:
            import logging

            logging.getLogger("aegis.simulation").warning("list_recent failed: %s", exc)
            return [
                {
                    "session_id": s.id,
                    "attack_type": s.attack_type,
                    "state": s.state,
                    "created_at": s.created_at,
                }
                for s in list(self.sessions.values())[-limit:]
            ]

    def advance(self, session_id: str, action: str | None = None) -> dict[str, Any]:
        s = self._require(session_id)
        if action == "reset":
            return self.start(
                s.attack_type,
                s.confidence,
                s.incident_id,
                s.risk_score,
                s.severity,
                s.recommendation,
                traffic_intensity=s.metrics.get("configured_intensity"),
                asset_criticality=s.metrics.get("asset_criticality"),
                campaign_id=s.campaign_id,
                campaign_progression=s.metrics.get("campaign_progression"),
            )
        if action == "defend" and s.state in ("detected", "recommended", "attack_impact"):
            if s.state != "recommended":
                self._to_recommended(s)
                s.state = "recommended"
            self._to_defended(s)
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

    def _elapsed_s(self, s: SimulationSession) -> float:
        """Current deterministic simulation clock (seconds)."""
        return round(float(s.metrics.get("simulation_time", 0.0)), 2)

    def _phase_dt(self, s: SimulationSession, state: str) -> float:
        base = float(_PHASE_DT.get(state, 2.0))
        # Confidence modulates detection/defense/recovery slightly but stays deterministic
        conf = max(0.0, min(1.0, float(s.confidence)))
        if state == "detected":
            return round(base + (1.0 - conf) * 2.0, 2)
        if state == "defended":
            return round(base + (1.0 - conf) * 1.5, 2)
        if state == "recovered":
            return round(base + (1.0 - conf) * 1.0, 2)
        return base

    def _log(self, s: SimulationSession, event: str, state: str, detail: str, dt: float | None = None) -> None:
        step = self._phase_dt(s, state) if dt is None else float(dt)
        elapsed = round(float(s.metrics.get("simulation_time", 0.0)) + max(0.0, step), 2)
        s.metrics["simulation_time"] = elapsed
        s.timeline.append(
            {
                "event": event,
                "state": state,
                "detail": detail,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "t_s": elapsed,
                "dt_s": step,
            }
        )
        s.metrics[f"phase_{state}_at_s"] = elapsed

    def _snapshot_series(self, s: SimulationSession, label: str) -> None:
        series = s.metrics.setdefault(
            "series",
            {
                "labels": [],
                "with_defense": {"traffic": [], "stress": [], "risk": []},
                "without_defense": {"traffic": [], "stress": [], "risk": []},
            },
        )
        series["labels"].append(label)
        traffic = float(s.metrics.get("peak_traffic", 0.2))
        stress = float(s.metrics.get("server_stress", 0.1))
        risk = float(s.risk_score)
        blocked = float(s.metrics.get("traffic_blocked", 0.0))
        defended_like = blocked > 0 or s.state in ("defended", "recovered")
        with_traffic = round(traffic * (1.0 - blocked), 3) if defended_like else traffic
        series["with_defense"]["traffic"].append(with_traffic)
        series["with_defense"]["stress"].append(round(stress, 3))
        series["with_defense"]["risk"].append(round(risk, 1))

        # Counterfactual: without defense, attack peak persists / slowly worsens
        nd_traffic = float(s.metrics.get("no_defense_peak_traffic", traffic))
        nd_stress = float(s.metrics.get("no_defense_server_stress", stress))
        nd_risk = float(s.metrics.get("no_defense_risk", risk))
        if defended_like:
            nd_stress = min(0.99, nd_stress + 0.03)
            nd_risk = min(100.0, nd_risk + 2.0)
            s.metrics["no_defense_server_stress"] = round(nd_stress, 3)
            s.metrics["no_defense_risk"] = round(nd_risk, 1)
        series["without_defense"]["traffic"].append(round(nd_traffic, 3))
        series["without_defense"]["stress"].append(round(nd_stress, 3))
        series["without_defense"]["risk"].append(round(nd_risk, 1))

    def _defense_effectiveness(self, s: SimulationSession) -> float:
        """Simulation assumption: defense efficacy from config + confidence + risk."""
        try:
            from ids_config import load_config

            cfg_base = load_config().get("simulation", {}).get("defense_effectiveness", {})
            base = float(cfg_base.get(s.attack_type, 0.75))
        except Exception:
            base = {
                "DDoS": 0.82,
                "DoS": 0.78,
                "PortScan": 0.85,
                "BruteForce": 0.88,
                "WebAttack": 0.90,
                "Bot": 0.92,
            }.get(s.attack_type, 0.75)
        conf_boost = 0.08 * max(0.0, min(1.0, s.confidence))
        risk_factor = max(0.0, min(1.0, s.risk_score / 100.0))
        intensity = float(s.metrics.get("configured_intensity") or s.metrics.get("peak_traffic") or 0.5)
        return float(max(0.45, min(0.97, base + conf_boost - 0.10 * risk_factor - 0.05 * intensity)))

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
                s.metrics["persistence"] = "ok"
            finally:
                db.close()
        except Exception as exc:
            import logging

            logging.getLogger("aegis.simulation").warning("Simulation persistence failed: %s", exc)
            s.metrics["persistence"] = "degraded"

    def _require(self, session_id: str) -> SimulationSession:
        if session_id not in self.sessions:
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
                            campaign_id=data.get("campaign_id"),
                            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
                        )
                        if "t0_epoch" not in session.metrics:
                            session.metrics["t0_epoch"] = time.time()
                        self.sessions[session_id] = session
                        return session
                finally:
                    db.close()
            except Exception as exc:
                import logging

                logging.getLogger("aegis.simulation").warning(
                    "Simulation restore failed for %s: %s", session_id, exc
                )
            raise KeyError(f"Unknown simulation session: {session_id}")
        return self.sessions[session_id]

    def _to_normal(self, s: SimulationSession) -> None:
        for e in s.edges:
            e.traffic = "normal"
            e.intensity = 0.2
        for n in s.nodes:
            n.status = "ok"
        detail = "Baseline client to server traffic"
        self._log(s, "normal_traffic", "normal", detail)
        s.narrative.append(detail)
        self._snapshot_series(s, "normal")

    def _to_attack_start(self, s: SimulationSession) -> None:
        fn = START.get(s.attack_type, apply_generic_start)
        detail = fn(s)
        configured = float(s.metrics.get("configured_intensity") or 0.55)
        intensity = min(0.99, configured * (0.85 + 0.15 * max(0.0, min(1.0, s.confidence))))
        s.metrics["peak_traffic"] = round(intensity, 3)
        self._log(s, "attack_start", "attack_start", detail)
        s.narrative.append(detail)
        self._snapshot_series(s, "attack_start")

    def _to_attack_impact(self, s: SimulationSession) -> None:
        fn = IMPACT.get(s.attack_type, apply_generic_impact)
        detail = fn(s)
        intensity = float(s.metrics.get("peak_traffic", 0.85))
        crit = s.metrics.get("asset_criticality")
        risk = compute_risk(
            s.attack_type,
            s.confidence,
            True,
            traffic_intensity=min(1.0, intensity + 0.1),
            asset_criticality=float(crit) if crit is not None else None,
        )
        s.risk_score = risk["risk_score"]
        s.severity = risk["severity"]
        s.metrics["peak_traffic"] = round(min(0.99, intensity + 0.08), 3)
        s.metrics["server_stress"] = round(min(0.98, 0.45 + 0.5 * intensity), 3)
        s.metrics["attack_server_stress"] = s.metrics["server_stress"]
        s.metrics["attack_risk"] = s.risk_score
        s.metrics["no_defense_peak_traffic"] = s.metrics["peak_traffic"]
        s.metrics["no_defense_server_stress"] = s.metrics["server_stress"]
        s.metrics["no_defense_risk"] = s.risk_score
        self._log(s, "impact", "attack_impact", detail)
        s.narrative.append(detail)
        self._snapshot_series(s, "impact")

    def _to_detected(self, s: SimulationSession) -> None:
        for n in s.nodes:
            if n.id == "ids":
                n.status = "alert"
        self._log(
            s,
            "ids_alert",
            "detected",
            f"IDS detected {s.attack_type} (confidence {s.confidence:.0%})",
        )
        attack_at = float(s.metrics.get("phase_attack_start_at_s", 0.0))
        detect_at = float(s.metrics.get("phase_detected_at_s", self._elapsed_s(s)))
        latency = round(max(0.05, detect_at - attack_at), 2)
        s.metrics["detection_latency_s"] = latency
        s.metrics["detection_delay_s"] = latency  # UI alias
        s.metrics["detection_at_s"] = detect_at
        s.timeline[-1]["detail"] = (
            f"IDS detected {s.attack_type} (confidence {s.confidence:.0%}); "
            f"detection latency {latency}s"
        )
        s.narrative.append(s.timeline[-1]["detail"])
        self._snapshot_series(s, "detected")

    def _to_recommended(self, s: SimulationSession) -> None:
        s.recommendation = recommend(s.attack_type, s.severity)
        detail = s.recommendation["primary"]
        self._log(s, "recommendation", "recommended", detail)
        s.narrative.append(f"Recommended response: {detail}")
        self._snapshot_series(s, "recommended")

    def _to_defended(self, s: SimulationSession) -> None:
        detail = apply_defense(s)
        eff = self._defense_effectiveness(s)
        peak = float(s.metrics.get("peak_traffic", 0.9))
        s.metrics["defense_effectiveness"] = round(eff, 3)
        s.metrics["traffic_blocked"] = round(eff, 3)
        s.metrics["remaining_malicious"] = round(peak * (1.0 - eff), 3)
        s.metrics["server_stress"] = round(
            max(0.08, float(s.metrics.get("server_stress", 0.9)) * (1.0 - 0.75 * eff)), 3
        )
        self._log(s, "defense_applied", "defended", detail)
        detect_at = float(s.metrics.get("phase_detected_at_s", 0.0))
        defend_at = float(s.metrics.get("phase_defended_at_s", self._elapsed_s(s)))
        latency = round(max(0.05, defend_at - detect_at), 2)
        s.metrics["defense_latency_s"] = latency
        s.metrics["defense_delay_s"] = latency
        s.timeline[-1]["detail"] = f"{detail} (defense latency {latency}s)"
        s.narrative.append(s.timeline[-1]["detail"])
        self._snapshot_series(s, "defended")

    def _to_recovered(self, s: SimulationSession) -> None:
        for n in s.nodes:
            if n.kind == "ids":
                n.status = "ok"
            if n.kind == "attacker":
                n.status = "ok"
        for e in s.edges:
            if e.traffic == "malicious":
                e.traffic = "blocked"
        s.risk_score = max(5.0, s.risk_score * (1.0 - 0.7 * float(s.metrics.get("defense_effectiveness", 0.8))))
        s.severity = "LOW"
        s.metrics["server_stress"] = 0.12
        self._log(s, "recovered", "recovered", "Service restored; threat mitigated (simulated)")
        defend_at = float(s.metrics.get("phase_defended_at_s", 0.0))
        recover_at = float(s.metrics.get("phase_recovered_at_s", self._elapsed_s(s)))
        attack_at = float(s.metrics.get("phase_attack_start_at_s", 0.0))
        recovery = round(max(0.05, recover_at - defend_at), 2)
        total = round(max(0.05, recover_at - attack_at), 2)
        s.metrics["recovery_time_s"] = recovery
        s.metrics["time_to_recover_s"] = total
        s.metrics["risk_reduction"] = round(
            max(0.0, float(s.metrics.get("attack_risk", s.risk_score)) - s.risk_score), 1
        )
        s.timeline[-1]["detail"] = (
            f"Service restored; threat mitigated (simulated). "
            f"Recovery {recovery}s after defense; attack→recover {total}s"
        )
        s.narrative.append(s.timeline[-1]["detail"])
        self._snapshot_series(s, "recovered")


simulation_engine = SimulationEngine()
