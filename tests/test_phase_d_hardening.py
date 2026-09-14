"""Stage-2 Phase D: rate-limit coverage, security headers, controlled-response plan."""
from __future__ import annotations

from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient as StarletteTestClient

from backend.main import app
from backend.middleware.rate_limit import SimpleRateLimitMiddleware
from backend.middleware.security_headers import SecurityHeadersMiddleware
from backend.services.controlled_response import build_response_plan

client = TestClient(app)


def test_security_status_phase_d():
    r = client.get("/api/security/status")
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "2-phase-f"
    assert body["controlled_response"]["live_mitigation"] is False
    assert "/api/ingest" in body["rate_limit"]["paths"]
    assert body["security_headers"]["enabled"] is True


def test_security_headers_on_api():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("x-aegis-live-mitigation") == "false"


def test_rate_limit_covers_ingest_prefix(monkeypatch):
    monkeypatch.delenv("DISABLE_RATE_LIMIT", raising=False)

    async def ok(_request: Request):
        return JSONResponse({"ok": True})

    app_s = Starlette(routes=[Route("/api/ingest/queue/submit", ok, methods=["POST"])])
    app_s.add_middleware(
        SimpleRateLimitMiddleware,
        enabled=True,
        limit=2,
        window_seconds=60,
        paths=["/api/ingest"],
    )
    c = StarletteTestClient(app_s)
    assert c.post("/api/ingest/queue/submit").status_code == 200
    assert c.post("/api/ingest/queue/submit").status_code == 200
    denied = c.post("/api/ingest/queue/submit")
    assert denied.status_code == 429
    assert denied.json()["detail"]["code"] == "RATE_LIMITED"


def test_security_headers_middleware_sets_defaults():
    async def ok(_request: Request):
        return JSONResponse({"ok": True})

    app_s = Starlette(routes=[Route("/ping", ok)])
    app_s.add_middleware(SecurityHeadersMiddleware, enabled=True)
    c = StarletteTestClient(app_s)
    r = c.get("/ping")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-aegis-live-mitigation"] == "false"


def test_response_plan_advisory_only():
    r = client.post(
        "/api/response/plan",
        json={
            "attack_type": "DDoS",
            "severity": "HIGH",
            "confidence": 0.92,
            "traffic_intensity": 0.8,
            "start_simulation": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["live_mitigation"] is False
    assert body["advisory_only"] is True
    assert body["mode"] == "dry_run_approval"
    assert body["phase"] == "P2"
    assert body["suggested_action_type"] == "BLOCK_SOURCE"
    assert body["recommendation"]["advisory_only"] is True
    assert body["simulation"] is None
    assert "risk" in body


def test_response_plan_with_simulation_preview():
    plan = build_response_plan(
        attack_type="DoS",
        severity="MEDIUM",
        confidence=0.88,
        traffic_intensity=0.6,
        start_simulation=True,
    )
    assert plan["live_mitigation"] is False
    assert plan["simulation"] is not None
    assert plan["simulation"].get("advisory_only") is True
