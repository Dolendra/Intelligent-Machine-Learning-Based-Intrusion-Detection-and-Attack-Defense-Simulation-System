"""P2 controlled response: dry-run + approval gate (no live network)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from security.rbac import has_permission
from security.response.dry_run import DryRunExecutor, LiveAdapterForbiddenError, LiveNetworkAdapter
from security.response.service import (
    ResponseError,
    approve_action,
    execute_action,
    propose_action,
    reject_action,
    run_dry_run,
)
from security.response.store import response_store
from security.response.types import ActionStatus, ExecutionMode, ResponseAction

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_store():
    response_store._actions.clear()
    response_store._order.clear()
    yield
    response_store._actions.clear()
    response_store._order.clear()


def test_dry_run_never_calls_live_adapter():
    adapter = LiveNetworkAdapter()
    action = ResponseAction(
        action_id="ra-test",
        action_type="BLOCK_SOURCE",
        incident_id="INC-1",
        source="unit",
        target="10.10.10.25",
        reason="test",
        risk_score=94.0,
        severity="CRITICAL",
        duration_minutes=15,
        mode=ExecutionMode.DRY_RUN.value,
    )
    with pytest.raises(LiveAdapterForbiddenError):
        adapter.apply(action)
    preview = DryRunExecutor().preview(action)
    assert "Would block source 10.10.10.25" in preview["message"]
    assert "15 minutes" in preview["message"]


def test_propose_ddos_block_source_pending_approval():
    action = propose_action(
        attack_type="DDoS",
        incident_id="INC-DDOS",
        severity="CRITICAL",
        risk_score=94.0,
        source_ip="10.10.10.25",
        actor="analyst",
    )
    assert action["action_type"] == "BLOCK_SOURCE"
    assert action["status"] == ActionStatus.PROPOSED.value
    assert action["approval_status"] == "PENDING_APPROVAL"
    assert action["live_network_change"] is False
    assert action["mode"] == "DRY_RUN"
    assert "Would block" in (action["dry_run_preview"] or "")
    assert len(action["audit"]) >= 2


def test_reject_never_executes():
    action = propose_action(attack_type="DDoS", source_ip="1.2.3.4", incident_id="INC-R")
    aid = action["action_id"]
    out = reject_action(aid, actor="responder", reason="False positive")
    assert out["executed"] is False
    assert out["action"]["status"] == ActionStatus.REJECTED.value
    with pytest.raises(ResponseError) as ei:
        execute_action(aid)
    assert ei.value.code == "REJECTED"


def test_unapproved_cannot_execute():
    action = propose_action(attack_type="PortScan", source_ip="9.9.9.9")
    with pytest.raises(ResponseError) as ei:
        execute_action(action["action_id"])
    assert ei.value.code == "NOT_APPROVED"


def test_approve_dry_runs_and_verifies_no_network_change():
    action = propose_action(
        attack_type="DDoS",
        severity="CRITICAL",
        risk_score=94.0,
        source_ip="10.10.10.25",
        incident_id="INC-OK",
    )
    aid = action["action_id"]
    out = approve_action(aid, actor="responder")
    assert out["action"]["status"] in {ActionStatus.VERIFIED.value, ActionStatus.ACTIVE.value}
    assert out["action"]["approved_by"] == "responder"
    assert out["execution"]["live_network_change"] is False
    assert out["action"]["live_network_change"] is False
    events = [e["event"] for e in out["action"]["audit"]]
    assert "approved" in events
    assert "verified" in events


def test_duplicate_approve_blocked():
    action = propose_action(attack_type="DoS", source_ip="8.8.8.8")
    aid = action["action_id"]
    approve_action(aid)
    with pytest.raises(ResponseError) as ei:
        approve_action(aid)
    assert ei.value.code == "ALREADY_DECIDED"


def test_invalid_action_type_rejected():
    with pytest.raises(ResponseError) as ei:
        propose_action(attack_type="DDoS", action_type="IPTABLES_DROP", source_ip="1.1.1.1")
    assert ei.value.code == "INVALID_ACTION"


def test_invalid_target_rejected():
    with pytest.raises(ResponseError) as ei:
        propose_action(attack_type="DDoS", target="evil; rm -rf /")
    assert ei.value.code == "INVALID_TARGET"


def test_live_mode_disabled():
    with pytest.raises(ResponseError) as ei:
        propose_action(attack_type="DDoS", source_ip="1.1.1.1", mode="LIVE")
    assert ei.value.code == "LIVE_MODE_DISABLED"


def test_api_propose_approve_reject_flow():
    r = client.post(
        "/api/response/actions/propose",
        json={
            "attack_type": "DDoS",
            "severity": "CRITICAL",
            "risk_score": 94,
            "source_ip": "10.10.10.25",
            "incident_id": "INC-API-1",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pending_approval"] is True
    aid = body["action_id"]

    dry = client.post(f"/api/response/actions/{aid}/dry-run")
    assert dry.status_code == 200
    assert dry.json()["dry_run"]["live_network_change"] is False

    ok = client.post(f"/api/response/actions/{aid}/approve")
    assert ok.status_code == 200
    assert ok.json()["action"]["status"] in {"VERIFIED", "ACTIVE"}
    assert ok.json()["execution"]["live_network_change"] is False

    # second action — reject path
    r2 = client.post(
        "/api/response/actions/propose",
        json={"attack_type": "Bot", "host": "host-a", "incident_id": "INC-API-2"},
    )
    aid2 = r2.json()["action_id"]
    rej = client.post(f"/api/response/actions/{aid2}/reject", json={"reason": "lab traffic"})
    assert rej.status_code == 200
    assert rej.json()["executed"] is False
    assert rej.json()["action"]["status"] == "REJECTED"


def test_api_execute_without_approve_fails():
    r = client.post(
        "/api/response/actions/propose",
        json={"attack_type": "WebAttack", "source_ip": "5.5.5.5"},
    )
    aid = r.json()["action_id"]
    ex = client.post(f"/api/response/actions/{aid}/execute")
    assert ex.status_code == 409
    assert ex.json()["detail"]["code"] == "NOT_APPROVED"


def test_rbac_boundary_permissions():
    assert has_permission("analyst", "write_response")
    assert not has_permission("analyst", "approve_response")
    assert has_permission("responder", "approve_response")
    assert has_permission("admin", "approve_response")
    assert not has_permission("viewer", "write_response")


def test_security_status_reports_p2_dry_run():
    r = client.get("/api/security/status")
    assert r.status_code == 200
    cr = r.json()["controlled_response"]
    assert cr["live_mitigation"] is False
    assert cr["dry_run_default"] is True
    assert cr["approval_required"] is True
    assert cr["phase"] == "P3"


def test_response_plan_includes_suggested_action():
    r = client.post("/api/response/plan", json={"attack_type": "DDoS", "severity": "CRITICAL"})
    assert r.status_code == 200
    body = r.json()
    assert body["live_mitigation"] is False
    assert body["suggested_action_type"] == "BLOCK_SOURCE"
    assert body["phase"] == "P3"


def test_dry_run_after_reject_fails():
    action = propose_action(attack_type="BruteForce", source_ip="7.7.7.7")
    reject_action(action["action_id"])
    with pytest.raises(ResponseError) as ei:
        run_dry_run(action["action_id"])
    assert ei.value.code == "REJECTED"
