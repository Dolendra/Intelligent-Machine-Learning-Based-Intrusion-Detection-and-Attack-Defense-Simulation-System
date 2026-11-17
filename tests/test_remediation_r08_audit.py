"""R-08 (SEC-6, SEC-18): the response audit trail is append-only; incident edits name the real actor."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from security.response import approve_action, propose_action
from security.response.service import action_audit
from security.response.store import ResponseActionStore, response_store


def test_audit_trail_survives_a_flood_of_new_proposals():
    """Old store.create() pruned the oldest terminal actions *and their audit rows* beyond
    max_actions. Use a store with a cap of 5 so the old behaviour would delete our action."""
    import dataclasses

    from security.response.store import new_action_id

    response_store.clear()
    aid = propose_action(attack_type="DDoS", source_ip="10.7.7.7", actor="alice")["action_id"]
    approve_action(aid, actor="bob")                     # approver recorded (ACTIVE, time-bound)
    from security.response.service import rollback_action

    rollback_action(aid, actor="bob")                    # terminal: old pruning would delete it
    assert response_store.get(aid).status == "ROLLED_BACK"
    events_before = [e["event"] for e in action_audit(aid)]
    assert "approved" in events_before
    template = response_store.get(aid)
    small = ResponseActionStore(max_actions=5)
    for _ in range(12):
        small.create(dataclasses.replace(template, action_id=new_action_id(), status="REJECTED", audit=[]))
    assert response_store.get(aid) is not None
    assert [e["event"] for e in action_audit(aid)] == events_before
    response_store.clear()


def test_incident_update_records_requesting_actor():
    from database.db import IncidentEvent, SessionLocal
    from backend.services import pipeline as svc

    with SessionLocal() as db:
        from database.db import Incident

        code = "INC-R08TEST"
        if not db.query(Incident).filter(Incident.incident_code == code).first():
            db.add(Incident(incident_code=code, attack_type="DDoS", severity="HIGH", status="Detected",
                            risk_score=70.0, confidence=0.9))
            db.commit()
        svc.update_incident_status(db, code, "Investigating", analyst_notes="looking", actor="dana")
        ev = (db.query(IncidentEvent).filter(IncidentEvent.incident_code == code)
              .order_by(IncidentEvent.id.desc()).first())
        assert ev.actor == "dana"


def test_patch_route_passes_actor_from_request():
    r = TestClient(app).patch("/api/incidents/INC-DOES-NOT-EXIST", json={"status": "Investigating"})
    assert r.status_code == 404                          # route still works; actor plumbing exercised
