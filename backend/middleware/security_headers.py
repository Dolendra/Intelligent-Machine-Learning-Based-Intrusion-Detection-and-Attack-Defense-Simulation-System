"""Baseline security response headers (Stage-2 Phase D hardening)."""
from __future__ import annotations

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ids_config import load_config

# Conservative defaults suitable for a local SOC UI + API demo.
DEFAULT_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-Aegis-Live-Mitigation": "false",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, enabled: bool = True, headers: dict[str, str] | None = None):
        super().__init__(app)
        self.enabled = enabled
        self.headers = dict(headers or DEFAULT_HEADERS)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        if self.enabled:
            for key, value in self.headers.items():
                response.headers.setdefault(key, value)
        return response


def security_headers_summary() -> dict:
    cfg = load_config().get("api", {}).get("security_headers", {}) or {}
    enabled = bool(cfg.get("enabled", True))
    return {
        "enabled": enabled,
        "headers": sorted((cfg.get("headers") or DEFAULT_HEADERS).keys()),
        "notes": [
            "Demo hardening only — not a full browser security policy / CSP suite.",
            "X-Aegis-Live-Mitigation is always false: response actions remain advisory/simulated.",
        ],
    }


def attach_security_headers(app) -> None:
    cfg = load_config().get("api", {}).get("security_headers", {}) or {}
    enabled = bool(cfg.get("enabled", True))
    custom = cfg.get("headers")
    headers = {**DEFAULT_HEADERS, **(custom or {})} if isinstance(custom, dict) else DEFAULT_HEADERS
    app.add_middleware(SecurityHeadersMiddleware, enabled=enabled, headers=headers)
