"""Optional API-key authentication (disabled by default for local demos)."""
from __future__ import annotations

import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ids_config import load_config

PUBLIC_PREFIXES = (
    "/api/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/",
)


class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, enabled: bool, api_key: str, header_name: str = "X-API-Key"):
        super().__init__(app)
        self.enabled = enabled and bool(api_key)
        self.api_key = api_key
        self.header_name = header_name

    def _is_public(self, path: str) -> bool:
        if path in {"/", "/docs", "/openapi.json", "/redoc", "/api/health", "/api/ready"}:
            return True
        if path.startswith("/api/ws"):
            return True
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled or request.method == "OPTIONS" or self._is_public(request.url.path):
            return await call_next(request)
        if os.getenv("DISABLE_API_AUTH", "").lower() in {"1", "true", "yes"}:
            return await call_next(request)

        provided = request.headers.get(self.header_name) or request.query_params.get("api_key")
        if not provided or provided != self.api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": {
                        "code": "UNAUTHORIZED",
                        "message": f"Missing or invalid {self.header_name}",
                    }
                },
            )
        return await call_next(request)


def attach_api_auth(app) -> None:
    cfg = load_config().get("api", {}).get("auth", {})
    key = os.getenv("AEGIS_API_KEY") or str(cfg.get("api_key") or "")
    enabled = bool(cfg.get("enabled", False))
    app.add_middleware(
        ApiKeyMiddleware,
        enabled=enabled,
        api_key=key,
        header_name=str(cfg.get("header", "X-API-Key")),
    )
