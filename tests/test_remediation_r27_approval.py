"""P0-3 (SEC-24, SEC-3, user decision 2026-11-18): response approval authorization."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from security.detection_policy import GATE_ONLY_LABEL
from security.response import approve_action, propose_action
from security.response.service import ResponseError, execute_action
from security.response.store import response_store


@pytest.fixture(autouse=True)
def _clear():
    response_store.clear()
    yield
    response_store.clear()


def _propose(actor: str, **kw):
    return propose_action(attack_type="DDoS", source_ip="10.9.9.9", actor=actor, **kw)


def test_proposer_cannot_approve_own_action():
    aid = _propose("alice")["action_id"]
    with pytest.raises(ResponseError) as ei:
        approve_action(aid, actor="alice")
    assert ei.value.code == "SELF_APPROVAL_FORBIDDEN" and ei.value.http_status == 403
    assert response_store.get(aid).status == "PROPOSED"          # nothing changed


def test_identity_comparison_is_case_insensitive():
    aid = _propose("Alice")["action_id"]
    with pytest.raises(ResponseError):
        approve_action(aid, actor="alice")


def test_second_person_can_approve():
    aid = _propose("alice")["action_id"]
    out = approve_action(aid, actor="bob")
    assert out["ok"] and out["action"]["approved_by"] == "bob"


def test_proposer_cannot_execute_own_action():
    aid = _propose("alice")["action_id"]
    with pytest.raises(ResponseError) as ei:
        execute_action(aid, actor="alice")
    assert ei.value.code == "SELF_APPROVAL_FORBIDDEN"


def test_gate_only_candidate_defaults_to_escalation():
    a = propose_action(attack_type=GATE_ONLY_LABEL, source_ip="10.1.2.3", actor="alice",
                       severity="CRITICAL")
    assert a["action_type"] == "ESCALATE" and a["target"] == "soc-queue"


@pytest.mark.parametrize("containment", ["BLOCK_SOURCE", "ISOLATE_HOST", "RATE_LIMIT"])
def test_gate_only_candidate_cannot_request_containment(containment):
    with pytest.raises(ResponseError) as ei:
        propose_action(attack_type=GATE_ONLY_LABEL, source_ip="10.1.2.3", actor="alice",
                       action_type=containment)
    assert ei.value.code == "GATE_ONLY_ADVISORY" and ei.value.http_status == 422


def test_user_directory_is_not_anonymous_even_with_auth_disabled():
    r = TestClient(app).get("/api/auth/users")
    assert r.status_code == 403
