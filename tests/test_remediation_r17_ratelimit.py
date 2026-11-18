"""R-17 (SEC-10, SEC-11): proxy-aware rate-limit keys; failed auth attempts are rate-limited."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.middleware.api_auth import ApiKeyMiddleware
from backend.middleware.rate_limit import SimpleRateLimitMiddleware, client_ip


def _req(peer: str, xff: str | None = None):
    headers = {"x-forwarded-for": xff} if xff else {}
    return SimpleNamespace(client=SimpleNamespace(host=peer), headers=headers)


def test_xff_ignored_without_trusted_proxies(monkeypatch):
    monkeypatch.delenv("AEGIS_TRUSTED_PROXIES", raising=False)
    assert client_ip(_req("203.0.113.9", "1.2.3.4")) == "203.0.113.9"      # no spoofing


def test_xff_used_only_from_trusted_proxy(monkeypatch):
    monkeypatch.setenv("AEGIS_TRUSTED_PROXIES", "172.16.0.0/12")
    assert client_ip(_req("172.18.0.5", "198.51.100.7")) == "198.51.100.7"  # via nginx
    assert client_ip(_req("203.0.113.9", "198.51.100.7")) == "203.0.113.9"  # untrusted peer
    # client-supplied hops to the left of the proxy-appended one are ignored
    assert client_ip(_req("172.18.0.5", "6.6.6.6, 198.51.100.7")) == "198.51.100.7"
    assert client_ip(_req("172.18.0.5", "not-an-ip")) == "172.18.0.5"


def _app(trusted: str | None, monkeypatch, limit=3):
    if trusted:
        monkeypatch.setenv("AEGIS_TRUSTED_PROXIES", trusted)
    else:
        monkeypatch.delenv("AEGIS_TRUSTED_PROXIES", raising=False)
    monkeypatch.setenv("AEGIS_ENV", "production")       # kill switches (DISABLE_RATE_LIMIT) ignored
    app = FastAPI()

    @app.post("/api/auth/login")
    def login():
        return {"ok": True}

    @app.get("/api/response/actions")
    def actions():
        return {"items": []}

    app.add_middleware(ApiKeyMiddleware, enabled=True, api_key="right-key")
    app.add_middleware(SimpleRateLimitMiddleware, enabled=True, limit=limit, window_seconds=60,
                       paths=["/api/auth/login", "/api/response"])           # outermost, as in main.py
    return TestClient(app, client=("172.18.0.5", 1234))


def test_users_behind_proxy_get_separate_buckets(monkeypatch):
    c = _app("172.16.0.0/12", monkeypatch)
    for _ in range(3):
        assert c.post("/api/auth/login", headers={"X-Forwarded-For": "198.51.100.1"}).status_code == 200
    assert c.post("/api/auth/login", headers={"X-Forwarded-For": "198.51.100.1"}).status_code == 429
    # a different user behind the same nginx is not locked out (SEC-10)
    assert c.post("/api/auth/login", headers={"X-Forwarded-For": "198.51.100.2"}).status_code == 200


def test_failed_auth_attempts_are_rate_limited(monkeypatch):
    c = _app(None, monkeypatch)
    codes = [c.get("/api/response/actions", headers={"X-API-Key": f"guess-{i}"}).status_code for i in range(5)]
    assert codes[:3] == [401, 401, 401] and codes[3:] == [429, 429]          # SEC-11


def test_main_app_orders_limiter_outside_auth():
    from backend.main import app

    names = [m.cls.__name__ for m in app.user_middleware]                     # outermost first
    assert names.index("SimpleRateLimitMiddleware") < names.index("ApiKeyMiddleware")
