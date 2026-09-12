"""Seed a few demo incidents so the dashboard is not empty on first open."""
from __future__ import annotations

from sqlalchemy.orm import Session

from database.db import Incident, SessionLocal
from security.recommendations.engine import recommend
from security.risk.engine import compute_risk


SEED = [
    ("DDoS", 0.96, 0.9),
    ("PortScan", 0.91, 0.4),
    ("BruteForce", 0.94, 0.55),
    ("DoS", 0.93, 0.7),
    ("WebAttack", 0.88, 0.5),
]


def seed_demo_incidents(force: bool = False) -> int:
    db: Session = SessionLocal()
    try:
        demo_codes = [f"INC-DEMO{i:02d}" for i in range(1, len(SEED) + 1)]
        existing_demos = (
            db.query(Incident).filter(Incident.incident_code.in_(demo_codes)).count()
        )
        if existing_demos > 0 and not force:
            return 0
        added = 0
        for i, (attack, conf, intensity) in enumerate(SEED, start=1):
            code = f"INC-DEMO{i:02d}"
            if db.query(Incident).filter(Incident.incident_code == code).first():
                continue
            risk = compute_risk(attack, conf, True, intensity)
            rec = recommend(attack, risk["severity"])
            db.add(
                Incident(
                    incident_code=code,
                    attack_type=attack,
                    is_attack=1,
                    confidence=conf,
                    risk_score=risk["risk_score"],
                    severity=risk["severity"],
                    recommendation=rec["primary"],
                    explanation=f"Seeded demo incident for {attack}",
                    status="Detected",
                )
            )
            added += 1
        db.commit()
        return added
    finally:
        db.close()
