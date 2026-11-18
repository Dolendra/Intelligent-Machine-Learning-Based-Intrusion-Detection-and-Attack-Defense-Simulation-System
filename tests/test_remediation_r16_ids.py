"""R-16 (ARCH-12): incident and campaign IDs carry 48 random bits; a collision is retried, not a 500."""
from __future__ import annotations

import re
import uuid

from backend.services import pipeline as svc
from database.db import Incident, SessionLocal
from security.correlation import new_campaign_id


def test_id_formats():
    with SessionLocal() as db:
        assert re.fullmatch(r"INC-[0-9A-F]{12}", svc._new_incident_code(db))
    assert re.fullmatch(r"CMP-[0-9A-F]{12}", new_campaign_id())


def test_collision_is_retried(monkeypatch):
    taken = "AAAAAAAAAAAA" + "0" * 20
    fresh = "BBBBBBBBBBBB" + "0" * 20
    with SessionLocal() as db:
        db.query(Incident).filter(Incident.incident_code == f"INC-{taken[:12]}").delete()
        db.add(Incident(incident_code=f"INC-{taken[:12]}", attack_type="DDoS", severity="LOW", status="Detected"))
        db.commit()
        seq = iter([uuid.UUID(taken), uuid.UUID(fresh)])
        monkeypatch.setattr(svc.uuid, "uuid4", lambda: next(seq))
        assert svc._new_incident_code(db) == f"INC-{fresh[:12]}"
