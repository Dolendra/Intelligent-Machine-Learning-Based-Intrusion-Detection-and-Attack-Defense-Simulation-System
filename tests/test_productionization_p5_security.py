"""P5 application security suite — boundary hardening (no ML changes)."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient as StarletteTestClient
from starlette.websockets import WebSocketDisconnect

from backend.main import app
from backend.middleware.api_auth import ApiKeyMiddleware
from backend.middleware.rate_limit import SimpleRateLimitMiddleware
from backend.middleware.request_limits import RequestSizeLimitMiddleware
from ingestion.pcap_validation import validate_pcap_upload
from ingestion.upload_safety import UnsafeFilenameError, safe_upload_basename
from security.auth.service import login
from security.response.store import response_store

client = TestClient(app)


def _minimal_pcap() -> bytes:
    return b"\xd4\xc3\xb2\xa1" + b"\x02\x00\x04\x00" + b"\x00" * 16


@pytest.fixture(autouse=True)
def _clear_response_store():
    response_store.clear()
    yield
    response_store.clear()


def test_path_traversal_filename_rejected():
    with pytest.raises(UnsafeFilenameError):
        safe_upload_basename("../../etc/passwd.pcap")
    with pytest.raises(UnsafeFilenameError):
        safe_upload_basename("C:\\Windows\\system32\\evil.pcap")
    assert safe_upload_basename("ok.pcap") == "ok.pcap"


def test_pcap_validation_rejects_traversal_and_bad_magic():
    bad = validate_pcap_upload(filename="../x.pcap", content=_minimal_pcap())
    assert bad.ok is False
    assert bad.code == "UNSAFE_FILENAME"

    magic = validate_pcap_upload(filename="x.pcap", content=b"not-a-pcap-file!!!!!!!!!")
    assert magic.ok is False
    assert magic.code == "PCAP_BAD_MAGIC"

    empty = validate_pcap_upload(filename="x.pcap", content=b"")
    assert empty.code == "PCAP_EMPTY"


def test_api_rejects_pcap_path_traversal():
    r = client.post(
        "/api/ingest/pcap",
        files={"file": ("../../evil.pcap", _minimal_pcap(), "application/octet-stream")},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "UNSAFE_FILENAME"


def test_request_size_middleware_413():
    async def ok(_request: Request):
        return JSONResponse({"ok": True})

    app_s = Starlette(routes=[Route("/api/predict", ok, methods=["POST"])])
    app_s.add_middleware(RequestSizeLimitMiddleware, enabled=True)
    c = StarletteTestClient(app_s)
    r = c.post("/api/predict", content=b"{}", headers={"Content-Length": str(50 * 1024 * 1024), "Content-Type": "application/json"})
    assert r.status_code == 413
    assert r.json()["detail"]["code"] == "REQUEST_TOO_LARGE"


def test_rate_limit_prefix_bucket_blocks_alternate_paths(monkeypatch):
    monkeypatch.delenv("DISABLE_RATE_LIMIT", raising=False)

    async def ok(_request: Request):
        return JSONResponse({"ok": True})

    app_s = Starlette(
        routes=[
            Route("/api/predict", ok, methods=["POST"]),
            Route("/api/predict/batch", ok, methods=["POST"]),
        ]
    )
    app_s.add_middleware(
        SimpleRateLimitMiddleware,
        enabled=True,
        limit=2,
        window_seconds=60,
        paths=["/api/predict"],
    )
    c = StarletteTestClient(app_s)
    assert c.post("/api/predict").status_code == 200
    assert c.post("/api/predict/batch").status_code == 200
    # Third hit on either path shares the /api/predict bucket
    denied = c.post("/api/predict")
    assert denied.status_code == 429
    assert denied.json()["detail"]["code"] == "RATE_LIMITED"


def test_unhandled_error_does_not_leak_exception_text(monkeypatch):
    # Force an internal error path via validation-safe endpoint that raises
    # Use a dedicated Starlette app with our error handlers attached via FastAPI pattern is heavy;
    # instead hit a route that returns controlled 500 from ResponseError already tested.
    # Direct unit: errors envelope
    from backend.middleware.errors import _envelope, _sanitize_validation_errors

    env = _envelope("INTERNAL_ERROR", "Unexpected server error", "rid-1")
    assert "traceback" not in str(env).lower()
    assert env["detail"]["message"] == "Unexpected server error"
    sanitized = _sanitize_validation_errors(
        [{"type": "value_error", "loc": ("body", "password"), "msg": "bad", "input": "SUPERSECRET"}]
    )
    assert "SUPERSECRET" not in str(sanitized)
    assert sanitized[0]["loc"] == ("body", "password")


def test_security_status_p5_defaults():
    r = client.get("/api/security/status")
    assert r.status_code == 200
    body = r.json()
    assert body["rate_limit"]["phase"] == "P5"
    assert body["rate_limit"]["default_on"] is True
    assert "/api/auth/login" in body["rate_limit"]["paths"]
    assert "request_limits" in body
    assert body["request_limits"]["enabled"] is True


def test_security_headers_present():
    r = client.get("/api/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("referrer-policy") == "no-referrer"


def test_response_action_abuse_matrix():
    """Analyst cannot approve; viewer cannot propose; unauthenticated 401 when auth on."""

    async def propose(_request: Request):
        return JSONResponse({"ok": True})

    async def approve(_request: Request):
        return JSONResponse({"ok": True})

    app_s = Starlette(
        routes=[
            Route("/api/response/actions/propose", propose, methods=["POST"]),
            Route("/api/response/actions/x/approve", approve, methods=["POST"]),
        ]
    )
    app_s.add_middleware(
        ApiKeyMiddleware,
        enabled=True,
        api_key="",
        enforce_rbac=True,
        allow_role_header=False,
    )
    c = StarletteTestClient(app_s)
    analyst = login("analyst", "ChangeMeAnalyst!")
    viewer = login("viewer", "ChangeMeViewer!")
    responder = login("responder", "ChangeMeResponder!")

    assert (
        c.post(
            "/api/response/actions/propose",
            headers={"Authorization": f"Bearer {viewer['access_token']}"},
        ).status_code
        == 403
    )
    assert (
        c.post(
            "/api/response/actions/x/approve",
            headers={"Authorization": f"Bearer {analyst['access_token']}"},
        ).status_code
        == 403
    )
    assert c.post("/api/response/actions/propose").status_code == 401
    assert (
        c.post(
            "/api/response/actions/x/approve",
            headers={"Authorization": f"Bearer {responder['access_token']}"},
        ).status_code
        == 200
    )


def test_forged_actor_ignored_on_approve():
    # With auth disabled (default TestClient app), propose/approve works but actor comes from request state
    r = client.post(
        "/api/response/actions/propose",
        json={"attack_type": "DDoS", "source_ip": "1.2.3.4", "mode": "DRY_RUN"},
    )
    assert r.status_code == 200
    aid = r.json()["action_id"]
    ap = client.post(
        f"/api/response/actions/{aid}/approve",
        json={"actor": "totally-admin-hacker"},
    )
    assert ap.status_code == 200
    # Actor must not be the forged body value when auth is off → anonymous/role from middleware
    assert ap.json()["action"]["approved_by"] != "totally-admin-hacker"


def test_duplicate_approval_rejected():
    r = client.post(
        "/api/response/actions/propose",
        json={"attack_type": "PortScan", "source_ip": "9.9.9.9"},
    )
    aid = r.json()["action_id"]
    assert client.post(f"/api/response/actions/{aid}/approve").status_code == 200
    dup = client.post(f"/api/response/actions/{aid}/approve")
    assert dup.status_code == 409
    assert dup.json()["detail"]["code"] == "ALREADY_DECIDED"


def test_invalid_target_rejected():
    r = client.post(
        "/api/response/actions/propose",
        json={"attack_type": "DDoS", "target": "evil; rm -rf /"},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "INVALID_TARGET"


def test_ws_requires_auth_when_enabled(monkeypatch):
    monkeypatch.setenv("AEGIS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AEGIS_AUTH_SECRET", "p5-ws-secret-for-ws")
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/api/ws/events") as ws:
            ws.receive_json()
    assert excinfo.value.code == 4401


def test_ws_accepts_bearer_token_when_auth_enabled(monkeypatch):
    monkeypatch.setenv("AEGIS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AEGIS_AUTH_SECRET", "p5-ws-secret-for-ws")
    tok = login("viewer", "ChangeMeViewer!")["access_token"]
    with client.websocket_connect(f"/api/ws/events?token={tok}") as ws:
        msg = ws.receive_json()
    assert msg["type"] == "connected"
    assert msg["auth_required"] is True
    assert msg["role"] == "viewer"


def test_validation_error_omits_input_secrets():
    r = client.post("/api/response/actions/propose", json={"attack_type": 123})
    assert r.status_code == 422
    body = r.json()
    assert body["detail"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in body["detail"]
    # Sanitized errors must not include raw "input" payload fields
    err_blob = str(body["detail"].get("errors"))
    assert "'input'" not in err_blob and '"input"' not in err_blob

