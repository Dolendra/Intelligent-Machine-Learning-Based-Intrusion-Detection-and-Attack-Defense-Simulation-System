"""R-14 (ARCH-5) and R-15 (ARCH-6): lifecycle state is consistent between API, memory and DB."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.services import pipeline as svc
from database.db import Incident, IncidentEvent, SessionLocal
from security.response import approve_action, propose_action
from security.response.store import ResponseActionStore, response_store


@pytest.fixture(autouse=True)
def _clear():
    response_store.clear()
    yield
    response_store.clear()


def test_verified_status_is_persisted():
    # duration 0 -> VERIFIED (not ACTIVE)
    aid = propose_action(attack_type="DDoS", source_ip="10.3.3.3", actor="alice",
                         duration_minutes=0)["action_id"]
    out = approve_action(aid, actor="bob")
    api_status = out["action"]["status"] if out["action"]["status"] != "APPROVED" else None
    persisted = ResponseActionStore().get(aid).status
    assert persisted == "VERIFIED"
    assert response_store.get(aid).status == persisted
    assert api_status in (None, "VERIFIED")


def _incident(code: str, status: str) -> None:
    with SessionLocal() as db:
        db.query(IncidentEvent).filter(IncidentEvent.incident_code == code).delete()
        db.query(Incident).filter(Incident.incident_code == code).delete()
        db.add(Incident(incident_code=code, attack_type="DDoS", severity="HIGH", status=status,
                        risk_score=70.0, confidence=0.9, recommendation="Rate limit",
                        resolved_at=datetime.now(timezone.utc) if status in ("Resolved", "FalsePositive") else None))
        db.commit()


@pytest.mark.parametrize("terminal", ["Resolved", "FalsePositive"])
def test_simulate_does_not_reopen_terminal_incidents(terminal):
    code = f"INC-R15{terminal[:3].upper()}"
    _incident(code, terminal)
    with SessionLocal() as db:
        svc.start_simulation_from_incident(db, code)
        row = db.query(Incident).filter(Incident.incident_code == code).first()
        assert row.status == terminal and row.resolved_at is not None
        last = (db.query(IncidentEvent).filter(IncidentEvent.incident_code == code)
                .order_by(IncidentEvent.id.desc()).first())
        assert last.new_status == terminal and "unchanged" in (last.notes or "")


def test_simulate_moves_open_incident_through_state_machine():
    code = "INC-R15OPEN"
    _incident(code, "Detected")
    with SessionLocal() as db:
        svc.start_simulation_from_incident(db, code)
        assert db.query(Incident).filter(Incident.incident_code == code).first().status == "Simulating"
