"""P6 persistence — restart recovery, concurrency, migrations, retention."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from backend.main import app
from database.bootstrap import bootstrap_persistence, seed_model_version_refs
from database.db import Incident, SessionLocal, init_db
from database.retention import persistence_summary, purge_expired, retention_policy
from security.auth.users import UserStore, user_store
from security.response.service import approve_action, propose_action, reject_action
from security.response.store import ResponseActionStore, response_store
from security.response.types import ActionStatus
from security.security_events import security_event

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_response():
    response_store.clear()
    yield
    response_store.clear()


def test_incident_survives_simulated_restart():
    code = f"INC-P6-{datetime.now(timezone.utc).strftime('%H%M%S%f')}"
    with SessionLocal() as db:
        db.add(
            Incident(
                incident_code=code,
                attack_type="DDoS",
                is_attack=1,
                confidence=0.9,
                risk_score=0.8,
                severity="High",
                status="Detected",
                campaign_id="camp-p6-1",
                hit_count=1,
            )
        )
        db.commit()

    # New session == process restart for SQLite file-backed store
    with SessionLocal() as db:
        row = db.query(Incident).filter(Incident.incident_code == code).first()
        assert row is not None
        assert row.campaign_id == "camp-p6-1"
        assert row.attack_type == "DDoS"


def test_campaign_relationship_preserved():
    import uuid

    camp = f"camp-p6-{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        for i in range(3):
            db.add(
                Incident(
                    incident_code=f"INC-{camp}-{i}",
                    attack_type="PortScan",
                    is_attack=1,
                    confidence=0.7,
                    risk_score=0.5,
                    severity="Medium",
                    status="Detected",
                    campaign_id=camp,
                    hit_count=1,
                )
            )
        db.commit()

    with SessionLocal() as db:
        rows = db.query(Incident).filter(Incident.campaign_id == camp).all()
        assert len(rows) >= 3


def test_response_action_and_audit_survive_restart():
    proposed = propose_action(attack_type="DDoS", source_ip="8.8.8.8", mode="DRY_RUN")
    aid = proposed["action_id"]
    approve_action(aid, actor="responder")

    # Simulate restart: brand-new store instance reading same DB
    store2 = ResponseActionStore()
    action = store2.get(aid)
    assert action is not None
    assert action.status in {
        ActionStatus.ACTIVE.value,
        ActionStatus.VERIFIED.value,
        ActionStatus.SUCCEEDED.value,
    }
    assert action.approved_by == "responder"
    events = [e["event"] for e in action.audit]
    assert "proposed" in events
    assert "approved" in events
    assert "succeeded" in events or "verified" in events or "activated" in events


def test_rejected_state_durable():
    proposed = propose_action(attack_type="Bot", source_ip="1.2.3.4")
    aid = proposed["action_id"]
    reject_action(aid, actor="responder", reason="false positive")
    store2 = ResponseActionStore()
    action = store2.get(aid)
    assert action is not None
    assert action.status == ActionStatus.REJECTED.value
    assert any(e["event"] == "rejected" for e in action.audit)


def test_active_controlled_survives_and_is_listable():
    proposed = propose_action(
        attack_type="DDoS",
        source_ip="9.9.9.9",
        mode="CONTROLLED",
        duration_minutes=30,
    )
    aid = proposed["action_id"]
    out = approve_action(aid, actor="responder")
    assert out["action"]["status"] in {ActionStatus.ACTIVE.value, ActionStatus.VERIFIED.value}
    store2 = ResponseActionStore()
    action = store2.get(aid)
    assert action is not None
    assert action.mode == "CONTROLLED"
    assert action.status in {ActionStatus.ACTIVE.value, ActionStatus.VERIFIED.value}


def test_duplicate_approve_concurrent():
    proposed = propose_action(attack_type="DDoS", source_ip="5.5.5.5")
    aid = proposed["action_id"]
    results: list[str] = []
    lock = threading.Lock()

    def _approve() -> str:
        try:
            approve_action(aid, actor="responder")
            return "ok"
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", type(exc).__name__)
            return str(code)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(_approve) for _ in range(4)]
        for fut in as_completed(futs):
            with lock:
                results.append(fut.result())

    assert results.count("ok") == 1
    assert results.count("ALREADY_DECIDED") == 3
    action = response_store.get(aid)
    assert action is not None
    # Exactly one successful transition out of PROPOSED
    assert action.status != ActionStatus.PROPOSED.value


def test_users_survive_restart():
    user_store.ensure_seeded()
    store2 = UserStore()
    store2.ensure_seeded()
    admin = store2.authenticate("admin", "ChangeMeAdmin!")
    assert admin is not None
    assert admin.role == "admin"


def test_security_audit_persisted():
    security_event("p6_test_event", path="/api/test", code="TEST", user="tester")
    summary = persistence_summary()
    assert summary["counts"]["security_audit_events"] >= 1


def test_model_refs_seeded():
    n = seed_model_version_refs()
    assert n >= 0
    summary = persistence_summary()
    assert summary["counts"]["model_version_refs"] >= 3


def test_retention_policy_documented():
    policy = retention_policy()
    assert policy["audit_days"] >= 365
    assert policy["simulations_days"] <= policy["audit_days"]
    assert policy["raw_pcap_hours"] <= 48
    dry = purge_expired(dry_run=True)
    assert dry["dry_run"] is True


def test_security_status_reports_p6():
    r = client.get("/api/security/status")
    assert r.status_code == 200
    body = r.json()
    assert body["database"]["persistence"]["phase"] == "P6"
    assert body["database"]["persistence"]["backup_ready"] is True
    assert "response_actions" in body["database"]["persistence"]["durable"]


def test_migration_fresh_db(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "fresh_p6.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("IDS_DB_URL", url)
    # Re-bind engine for this process is hard; instead run alembic via init_db on a side engine
    from alembic import command
    from alembic.config import Config
    from ids_config import ROOT

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    eng = create_engine(url)
    tables = set(inspect(eng).get_table_names())
    for required in {
        "incidents",
        "incident_events",
        "simulations",
        "users",
        "response_actions",
        "response_audit_events",
        "security_audit_events",
        "model_version_refs",
    }:
        assert required in tables, f"missing {required}"
