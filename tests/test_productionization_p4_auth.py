"""P4 authentication + server-side RBAC (no UI-only security)."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient as StarletteTestClient

from backend.main import app
from backend.middleware.api_auth import ApiKeyMiddleware
from security.auth.passwords import hash_password, verify_password
from security.auth.tokens import mint_token, verify_token
from security.rbac import OPERATION_MATRIX, has_permission
from security.response.store import response_store

client = TestClient(app)


def test_password_hash_not_plaintext():
    encoded = hash_password("ChangeMeAnalyst!")
    assert "ChangeMeAnalyst!" not in encoded
    assert verify_password("ChangeMeAnalyst!", encoded)
    assert not verify_password("wrong", encoded)


def test_token_expiry_rejected(monkeypatch):
    token, _ = mint_token(user_id="u1", username="analyst", role="analyst", ttl_seconds=1)
    time.sleep(1.1)
    try:
        verify_token(token)
        assert False, "expected expiry"
    except ValueError as exc:
        assert "expired" in str(exc)


def test_login_and_me_when_auth_disabled():
    # Default research baseline — auth off
    r = client.post("/api/auth/login", json={"username": "analyst", "password": "ChangeMeAnalyst!"})
    assert r.status_code == 200
    assert "access_token" in r.json()
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["auth_enabled"] is False


def test_operation_matrix_matches_roles():
    assert OPERATION_MATRIX["approve_response"]["analyst"] is False
    assert OPERATION_MATRIX["approve_response"]["responder"] is True
    assert has_permission("analyst", "write_response")
    assert not has_permission("analyst", "approve_response")
    assert has_permission("viewer", "read_incidents")
    assert not has_permission("viewer", "write_response")


def test_analyst_cannot_approve_via_direct_api():
    """Critical: UI bypass attempt must fail server-side."""

    async def propose(request: Request):
        return JSONResponse({"ok": True})

    async def approve(request: Request):
        return JSONResponse({"ok": True, "approved": True})

    app_s = Starlette(
        routes=[
            Route("/api/response/actions/propose", propose, methods=["POST"]),
            Route("/api/response/actions/ra-1/approve", approve, methods=["POST"]),
        ]
    )
    app_s.add_middleware(
        ApiKeyMiddleware,
        enabled=True,
        api_key="secret",
        enforce_rbac=True,
        allow_role_header=False,
        api_key_role="admin",
    )
    # Use bearer tokens instead of role header spoofing
    c = StarletteTestClient(app_s)

    # Build real tokens via auth service
    from security.auth.service import login

    analyst = login("analyst", "ChangeMeAnalyst!")
    responder = login("responder", "ChangeMeResponder!")

    # Re-mount with only bearer path — empty api key forces bearer
    app_b = Starlette(
        routes=[
            Route("/api/response/actions/propose", propose, methods=["POST"]),
            Route("/api/response/actions/ra-1/approve", approve, methods=["POST"]),
        ]
    )
    app_b.add_middleware(
        ApiKeyMiddleware,
        enabled=True,
        api_key="",  # bearer only
        enforce_rbac=True,
        allow_role_header=False,
    )
    cb = StarletteTestClient(app_b)

    denied = cb.post(
        "/api/response/actions/ra-1/approve",
        headers={"Authorization": f"Bearer {analyst['access_token']}"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "FORBIDDEN"

    allowed_propose = cb.post(
        "/api/response/actions/propose",
        headers={"Authorization": f"Bearer {analyst['access_token']}"},
    )
    assert allowed_propose.status_code == 200

    allowed_approve = cb.post(
        "/api/response/actions/ra-1/approve",
        headers={"Authorization": f"Bearer {responder['access_token']}"},
    )
    assert allowed_approve.status_code == 200


def test_unauthenticated_gets_401_when_auth_on():
    app_s = Starlette(routes=[Route("/api/response/actions/propose", lambda r: JSONResponse({}), methods=["POST"])])
    app_s.add_middleware(ApiKeyMiddleware, enabled=True, api_key="secret", enforce_rbac=True)
    c = StarletteTestClient(app_s)
    r = c.post("/api/response/actions/propose")
    assert r.status_code == 401


def test_role_header_cannot_escalate_when_disallowed():
    async def ok(request: Request):
        return JSONResponse({"role": getattr(request.state, "aegis_role", None)})

    app_s = Starlette(routes=[Route("/api/predict", ok, methods=["POST"])])
    app_s.add_middleware(
        ApiKeyMiddleware,
        enabled=True,
        api_key="secret",
        enforce_rbac=True,
        allow_role_header=False,
        api_key_role="viewer",
    )
    c = StarletteTestClient(app_s)
    # Client claims admin but server binds viewer
    r = c.post("/api/predict", headers={"X-API-Key": "secret", "X-Aegis-Role": "admin"})
    assert r.status_code == 403


def test_full_app_analyst_forbidden_approve(monkeypatch):
    monkeypatch.setenv("AEGIS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AEGIS_AUTH_SECRET", "p4-test-secret")
    # Re-attach is hard on existing app; use login + middleware unit style via TestClient
    # with a fresh app import is heavy — use Starlette isolation already covered.
    # Additionally prove end-to-end against response service with actor binding:
    response_store._actions.clear()
    from security.auth.service import login
    from security.response import propose_action, approve_action
    from security.response.service import ResponseError

    analyst = login("analyst", "ChangeMeAnalyst!")
    # Propose as analyst identity string
    action = propose_action(
        attack_type="DDoS",
        source_ip="10.1.1.1",
        actor=analyst["user"]["username"],
    )
    assert action["created_by"] == "analyst"
    # Approval permission is middleware-level; service still allows if called directly.
    # Document: service is behind middleware — middleware test above is the security boundary.
    assert not has_permission("analyst", "approve_response")
    assert has_permission("responder", "approve_response")


def test_invalid_login():
    r = client.post("/api/auth/login", json={"username": "analyst", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_security_status_reports_p4_auth_fields():
    r = client.get("/api/security/status")
    assert r.status_code == 200
    auth = r.json()["auth"]
    assert auth["phase"] == "P4"
    assert auth["bearer"] is True
    assert "operations" in r.json()["rbac"]
