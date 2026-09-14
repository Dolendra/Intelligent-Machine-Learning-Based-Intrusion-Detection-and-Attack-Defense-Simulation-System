"""Stage-2 Phase C auth/RBAC + database URL helpers."""
from __future__ import annotations

import os

from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient as StarletteTestClient

from backend.main import app
from backend.middleware.api_auth import ApiKeyMiddleware
from database.url import database_info, engine_kwargs_for, resolve_database_url
from security.rbac import has_permission, normalize_role, rbac_summary

client = TestClient(app)


def test_security_status_public():
    r = client.get("/api/security/status")
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "2-phase-f"
    assert "rbac" in body
    assert "database" in body
    assert body["auth"]["enabled"] is False
    assert body["database"]["sqlite_default"] is True or body["database"]["dialect"] == "sqlite"


def test_rbac_matrix():
    assert has_permission("viewer", "read_incidents")
    assert not has_permission("viewer", "write_detect")
    assert has_permission("analyst", "write_ingest")
    assert has_permission("admin", "admin")
    assert normalize_role("nope") == "analyst"
    summary = rbac_summary()
    assert "analyst" in summary["roles"]


def test_resolve_database_url_sqlite_default(monkeypatch):
    monkeypatch.delenv("IDS_DB_URL", raising=False)
    url = resolve_database_url()
    assert url.startswith("sqlite:///")
    info = database_info(url)
    assert info["dialect"] == "sqlite"
    assert "check_same_thread" in engine_kwargs_for(url)["connect_args"]


def test_resolve_database_url_postgres_env(monkeypatch):
    monkeypatch.setenv("IDS_DB_URL", "postgresql+psycopg://u:p@localhost:5432/aegis")
    url = resolve_database_url()
    assert url.startswith("postgresql")
    kwargs = engine_kwargs_for(url)
    assert kwargs.get("pool_pre_ping") is True
    info = database_info(url)
    assert info["postgres_ready"] is True
    assert "***" in info["url_redacted"]


def test_api_key_rbac_forbids_viewer_predict():
    async def ok(request: Request):
        return JSONResponse({"ok": True, "role": getattr(request.state, "aegis_role", None)})

    app_s = Starlette(routes=[Route("/api/predict", ok, methods=["POST"])])
    app_s.add_middleware(
        ApiKeyMiddleware,
        enabled=True,
        api_key="secret",
        enforce_rbac=True,
        default_role="viewer",
    )
    c = StarletteTestClient(app_s)
    denied = c.post("/api/predict", headers={"X-API-Key": "secret", "X-Aegis-Role": "viewer"})
    assert denied.status_code == 403
    allowed = c.post("/api/predict", headers={"X-API-Key": "secret", "X-Aegis-Role": "analyst"})
    assert allowed.status_code == 200
