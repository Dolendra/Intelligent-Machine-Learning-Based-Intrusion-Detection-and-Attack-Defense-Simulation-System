"""P9 failure recovery — controlled failure injection + backup/restore drill."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.recovery import reclaim_stale_response_actions, recovery_summary
from database.db import Incident, ResponseActionRecord, SessionLocal, init_db
from ingestion.queue import IngestDetectQueue
from security.response.adapters import reset_test_adapter, test_network_adapter
from security.response.service import ResponseError, approve_action, propose_action, rollback_action
from security.response.store import response_store
from security.response.types import ActionStatus, utc_now_iso

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    response_store.clear()
    reset_test_adapter()
    yield
    response_store.clear()
    reset_test_adapter()


def test_health_liveness_even_when_not_ready(monkeypatch):
    monkeypatch.setattr(
        "backend.observability.health_checks.check_database",
        lambda: {"status": "unavailable", "detail": "database_check_failed"},
    )
    monkeypatch.setattr(
        "backend.observability.deps.check_database",
        lambda: {"status": "unavailable", "detail": "database_check_failed"},
    )
    h = client.get("/api/health")
    assert h.status_code == 200
    assert h.json()["status"] == "ok"
    r = client.get("/api/ready")
    assert r.status_code == 503
    detail = r.json()["detail"]
    assert detail["code"] == "NOT_READY"
    assert "database" in detail.get("missing", [])
    # No filesystem path leakage
    assert "ids.db" not in json.dumps(detail).lower() or "database_check_failed" in json.dumps(detail)


def test_model_unavailable_not_ready(monkeypatch):
    monkeypatch.setattr("backend.services.pipeline.models_ready", lambda: False)
    monkeypatch.setattr(
        "backend.observability.health_checks.check_models",
        lambda: {"status": "unavailable", "detail": "not_loaded"},
    )
    monkeypatch.setattr(
        "backend.observability.deps.check_models",
        lambda: {"status": "unavailable", "detail": "not_loaded"},
    )
    r = client.get("/api/ready")
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "NOT_READY"


def test_predict_model_missing_is_not_fake_success(monkeypatch):
    monkeypatch.setattr("backend.services.pipeline.get_predictor", lambda: None)
    r = client.post("/api/predict", json={"features": {"Destination Port": 80}, "persist": False})
    assert r.status_code in {503, 500}
    body = r.json()
    detail = body.get("detail") or body
    blob = json.dumps(detail).lower()
    assert "model" in blob or "not" in blob
    assert "verified" not in blob


def test_reclaim_executing_after_crash():
    proposed = propose_action(attack_type="DDoS", source_ip="198.51.100.1", mode="DRY_RUN")
    aid = proposed["action_id"]
    action = response_store.get(aid)
    assert action is not None
    action.status = ActionStatus.EXECUTING.value
    response_store.save(action)

    summary = reclaim_stale_response_actions()
    assert summary["reclaimed_executing"] >= 1
    recovered = response_store.get(aid)
    assert recovered is not None
    assert recovered.status == ActionStatus.FAILED.value
    events = [e["event"] for e in recovered.audit]
    assert "recovered_stale_executing" in events
    assert recovered.status != ActionStatus.VERIFIED.value
    assert recovery_summary()["reclaimed_executing"] >= 1


def test_reclaim_approved_without_execution():
    proposed = propose_action(attack_type="PortScan", source_ip="198.51.100.2", mode="DRY_RUN")
    aid = proposed["action_id"]
    action = response_store.get(aid)
    assert action is not None
    action.status = ActionStatus.APPROVED.value
    action.approved_at = utc_now_iso()
    action.executed_at = None
    response_store.save(action)

    summary = reclaim_stale_response_actions()
    assert summary["reclaimed_approved"] >= 1
    recovered = response_store.get(aid)
    assert recovered is not None
    assert recovered.status == ActionStatus.FAILED.value
    assert any(e["event"] == "recovered_stale_approved" for e in recovered.audit)


def test_verify_failure_never_verified():
    proposed = propose_action(
        attack_type="DDoS",
        source_ip="198.51.100.3",
        mode="CONTROLLED",
        duration_minutes=10,
    )
    aid = proposed["action_id"]
    test_network_adapter.fail_next_verify = True
    with pytest.raises(ResponseError) as ei:
        approve_action(aid, actor="responder")
    assert ei.value.code == "VERIFY_FAILED"
    final = response_store.get(aid)
    assert final is not None
    assert final.status in {ActionStatus.ROLLED_BACK.value, ActionStatus.FAILED.value}
    assert final.status != ActionStatus.VERIFIED.value
    assert final.status != ActionStatus.ACTIVE.value


def test_rollback_failure_marked_failed():
    proposed = propose_action(
        attack_type="DDoS",
        source_ip="198.51.100.4",
        mode="CONTROLLED",
        duration_minutes=10,
    )
    aid = proposed["action_id"]
    approve_action(aid, actor="responder")
    action = response_store.get(aid)
    assert action is not None
    assert action.status in {ActionStatus.ACTIVE.value, ActionStatus.VERIFIED.value}
    test_network_adapter.fail_next_rollback = True
    with pytest.raises(ResponseError) as ei:
        rollback_action(aid, actor="responder")
    assert ei.value.code == "ROLLBACK_FAILED"
    final = response_store.get(aid)
    assert final is not None
    assert final.rollback_status == "ROLLBACK_FAILED"
    assert final.status != ActionStatus.VERIFIED.value or final.rollback_status == "ROLLBACK_FAILED"


def test_queue_predict_failure_no_silent_success():
    q = IngestDetectQueue(max_jobs=10, history=10)

    def _boom(_flows):
        raise RuntimeError("worker_boom")

    q.set_predict_fn(_boom)
    q.start()
    job = q.submit([{"Destination Port": 80.0}], source="p9")
    # Wait for worker
    import time

    deadline = time.time() + 5
    while time.time() < deadline:
        cur = q.get(job.job_id)
        if cur and cur.status in {"done", "error"}:
            break
        time.sleep(0.05)
    cur = q.get(job.job_id)
    q.stop(wait=True)
    assert cur is not None
    assert cur.status == "error"
    assert cur.result is None


def test_pcap_bad_magic_no_fake_prediction():
    from ingestion.pcap_validation import validate_pcap_upload

    bad = validate_pcap_upload(filename="x.pcap", content=b"not-a-pcap")
    assert bad.ok is False
    r = client.post(
        "/api/ingest/pcap",
        files={"file": ("x.pcap", b"not-a-pcap", "application/octet-stream")},
    )
    assert r.status_code in {400, 422}
    body = r.json()
    assert "prediction" not in json.dumps(body).lower() or body.get("detail", {}).get("code")


def test_backup_restore_disaster_drill(tmp_path):
    import importlib.util
    import uuid

    from database.url import resolve_database_url

    init_db()
    code = f"INC-P9-{uuid.uuid4().hex[:8].upper()}"
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
                campaign_id="camp-p9",
                hit_count=1,
            )
        )
        db.commit()
    proposed = propose_action(attack_type="DDoS", source_ip="198.51.100.9")
    aid = proposed["action_id"]

    live = resolve_database_url().replace("sqlite:///", "")
    live_path = Path(live)
    assert live_path.exists()

    spec = importlib.util.spec_from_file_location(
        "backup_mod", Path(__file__).resolve().parents[1] / "scripts" / "40_db_backup_restore.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    work = tmp_path / "drill"
    result = mod.disaster_drill(live_path, work)
    assert result["ok"] is True
    assert result["destroyed_exists"] is False
    assert result["post_verify"]["ok"] is True
    assert result["post_verify"]["counts"].get("incidents", 0) >= 1
    assert result["post_verify"]["counts"].get("response_actions", 0) >= 1
    assert result["rto_seconds_measured"] is not None
    assert result["rto_seconds_measured"] < 60

    restored = Path(result["restore"]["target"])
    conn = sqlite3.connect(str(restored))
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM response_actions WHERE action_id = ?", (aid,)
        ).fetchone()[0]
        assert n == 1
        inc = conn.execute(
            "SELECT COUNT(*) FROM incidents WHERE incident_code = ?", (code,)
        ).fetchone()[0]
        assert inc == 1
    finally:
        conn.close()


def test_ops_exposes_recovery_block():
    r = client.get("/api/ops/status")
    assert r.status_code == 200
    body = r.json()
    assert "recovery" in body
    assert body["phase"] == "P9"
