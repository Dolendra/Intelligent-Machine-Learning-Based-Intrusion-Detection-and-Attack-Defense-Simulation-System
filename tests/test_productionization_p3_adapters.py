"""P3: adapter contract, TestNetworkAdapter, verify, rollback, expire."""
from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from security.response.adapters import get_adapter, reset_test_adapter, test_network_adapter
from security.response.adapters.live_forbidden import LiveAdapterForbiddenError
from security.response.service import (
    ResponseError,
    approve_action,
    expire_action,
    propose_action,
    rollback_action,
    run_dry_run,
)
from security.response.store import response_store
from security.response.types import ActionStatus, utc_now

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    response_store.clear()
    reset_test_adapter()
    yield
    response_store.clear()
    reset_test_adapter()


def test_live_adapter_still_forbidden():
    adapter = get_adapter("live")
    action = propose_action(attack_type="DDoS", source_ip="1.1.1.1")
    # rebuild minimal — use store action object
    from security.response.store import response_store as store

    ra = store.get(action["action_id"])
    assert ra is not None
    with pytest.raises(LiveAdapterForbiddenError):
        adapter.execute(ra)


def test_controlled_lifecycle_verify_rollback_audit():
    action = propose_action(
        attack_type="DDoS",
        severity="CRITICAL",
        risk_score=94.0,
        source_ip="10.10.10.25",
        incident_id="INC-P3",
        mode="CONTROLLED",
    )
    assert action["adapter"] == "test_network"
    assert action["mode"] == "CONTROLLED"
    aid = action["action_id"]

    dry = run_dry_run(aid)
    assert dry["dry_run"]["live_network_change"] is False

    out = approve_action(aid, actor="responder")
    assert out["action"]["status"] == ActionStatus.ACTIVE.value
    assert out["execution"]["live_network_change"] is False
    assert out["execution"]["adapter"] == "test_network"
    assert test_network_adapter.snapshot()["count"] == 1

    events = [e["event"] for e in out["action"]["audit"]]
    assert "approved" in events
    assert "verified" in events
    assert "activated" in events

    rb = rollback_action(aid, actor="responder")
    assert rb["action"]["status"] == ActionStatus.ROLLED_BACK.value
    assert rb["action"]["rollback_status"] == "ROLLED_BACK"
    assert test_network_adapter.snapshot()["count"] == 0
    assert any(e["event"] == "rolled_back" for e in rb["action"]["audit"])


def test_verify_failure_triggers_rollback():
    action = propose_action(
        attack_type="PortScan",
        source_ip="9.9.9.9",
        mode="CONTROLLED",
    )
    aid = action["action_id"]
    test_network_adapter.fail_next_verify = True
    with pytest.raises(ResponseError) as ei:
        approve_action(aid)
    assert ei.value.code == "VERIFY_FAILED"
    final = response_store.get(aid)
    assert final is not None
    assert final.status == ActionStatus.ROLLED_BACK.value
    assert test_network_adapter.snapshot()["count"] == 0
    assert any(e["event"] == "verify_failed" for e in final.audit)
    assert any(e["event"] == "rolled_back" for e in final.audit)


def test_adapter_execute_failure_audited():
    action = propose_action(attack_type="DoS", source_ip="8.8.8.8", mode="CONTROLLED")
    aid = action["action_id"]
    test_network_adapter.fail_next_execute = True
    with pytest.raises(ResponseError) as ei:
        approve_action(aid)
    assert ei.value.code == "ADAPTER_UNAVAILABLE"
    final = response_store.get(aid)
    assert final is not None
    assert final.status == ActionStatus.FAILED.value
    assert any(e["event"] == "failed" for e in final.audit)


def test_escalate_not_reversible():
    action = propose_action(
        attack_type="Heartbleed",
        action_type="ESCALATE",
        target="soc-queue",
        mode="CONTROLLED",
        duration_minutes=0,
    )
    assert action["reversible"] is False
    aid = action["action_id"]
    out = approve_action(aid)
    assert out["action"]["status"] == ActionStatus.VERIFIED.value
    with pytest.raises(ResponseError) as ei:
        rollback_action(aid)
    assert ei.value.code == "NOT_REVERSIBLE"


def test_expire_active_action():
    action = propose_action(
        attack_type="DDoS",
        source_ip="10.0.0.1",
        mode="CONTROLLED",
        duration_minutes=15,
    )
    aid = action["action_id"]
    approve_action(aid)
    ra = response_store.get(aid)
    assert ra is not None
    assert ra.status == ActionStatus.ACTIVE.value
    # Force expiry in the past (must persist — store is DB-backed in P6)
    ra.expires_at = (utc_now() - timedelta(minutes=1)).isoformat()
    response_store.save(ra)
    out = expire_action(aid)
    assert out["action"]["status"] == ActionStatus.EXPIRED.value
    assert test_network_adapter.snapshot()["count"] == 0


def test_api_controlled_flow_and_adapters():
    caps = client.get("/api/response/capabilities")
    assert caps.status_code == 200
    assert caps.json()["phase"] == "P3"
    assert "dry_run" in {a["name"] for a in caps.json()["adapters"]}

    adapters = client.get("/api/response/adapters")
    assert adapters.status_code == 200
    assert adapters.json()["live_mitigation"] is False

    r = client.post(
        "/api/response/actions/propose",
        json={
            "attack_type": "DDoS",
            "severity": "CRITICAL",
            "source_ip": "10.10.10.25",
            "mode": "CONTROLLED",
            "incident_id": "INC-API-P3",
        },
    )
    assert r.status_code == 200, r.text
    aid = r.json()["action_id"]
    assert r.json()["adapter"] == "test_network"

    assert client.post(f"/api/response/actions/{aid}/dry-run").status_code == 200
    ap = client.post(f"/api/response/actions/{aid}/approve")
    assert ap.status_code == 200
    assert ap.json()["action"]["status"] == "ACTIVE"

    rb = client.post(f"/api/response/actions/{aid}/rollback")
    assert rb.status_code == 200
    assert rb.json()["action"]["status"] == "ROLLED_BACK"


def test_no_approval_no_execution_controlled():
    r = client.post(
        "/api/response/actions/propose",
        json={"attack_type": "Bot", "host": "h1", "mode": "CONTROLLED"},
    )
    aid = r.json()["action_id"]
    ex = client.post(f"/api/response/actions/{aid}/execute")
    assert ex.status_code == 409
    assert ex.json()["detail"]["code"] == "NOT_APPROVED"
    assert test_network_adapter.snapshot()["count"] == 0
