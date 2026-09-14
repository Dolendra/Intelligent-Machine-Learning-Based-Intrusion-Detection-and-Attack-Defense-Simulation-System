"""Optional API-key authentication + coarse RBAC (disabled by default for local demos)."""
from __future__ import annotations

import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ids_config import load_config
from security.rbac import has_permission, normalize_role


def _permission_for_request(method: str, path: str) -> str | None:
    """Map request to a coarse permission; None means allow when authenticated."""
    if path in {"/", "/docs", "/openapi.json", "/redoc", "/api/health", "/api/ready", "/api/security/status", "/api/metrics"}:
        return None
    if path.startswith("/api/ws"):
        return None
    if method == "GET":
        if path.startswith("/api/models") or path.startswith("/api/experiments") or path.startswith("/api/drift"):
            return "read_models"
        if path.startswith("/api/incidents") or path.startswith("/api/analytics") or path.startswith("/api/campaigns") or path.startswith("/api/export"):
            return "read_incidents"
        if path.startswith("/api/ingest"):
            return "read_health"
        return "read_health"
    # Mutations
    if path.startswith("/api/response/actions"):
        # Approve / reject require elevated permission when RBAC is on
        if method == "POST" and (
            path.endswith("/approve") or path.endswith("/reject") or path.endswith("/execute")
        ):
            return "approve_response"
        if method == "GET":
            return "read_incidents"
        return "write_response"
    if path.startswith("/api/predict") or path.startswith("/api/explain") or path.startswith("/api/risk") or path.startswith("/api/recommendation") or path.startswith("/api/response"):
        return "write_detect"
    if path.startswith("/api/incidents") or path.startswith("/api/campaigns"):
        return "write_incidents"
    if path.startswith("/api/simulation"):
        return "write_simulation"
    if path.startswith("/api/ingest"):
        return "write_ingest"
    return "admin"


class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        enabled: bool,
        api_key: str,
        header_name: str = "X-API-Key",
        role_header: str = "X-Aegis-Role",
        default_role: str = "analyst",
        enforce_rbac: bool = True,
    ):
        super().__init__(app)
        self.enabled = enabled and bool(api_key)
        self.api_key = api_key
        self.header_name = header_name
        self.role_header = role_header
        self.default_role = default_role
        self.enforce_rbac = enforce_rbac

    def _is_public(self, path: str) -> bool:
        if path in {"/", "/docs", "/openapi.json", "/redoc", "/api/health", "/api/ready", "/api/security/status", "/api/metrics"}:
            return True
        if path.startswith("/api/ws"):
            return True
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled or request.method == "OPTIONS" or self._is_public(request.url.path):
            request.state.aegis_role = "anonymous"
            return await call_next(request)
        if os.getenv("DISABLE_API_AUTH", "").lower() in {"1", "true", "yes"}:
            request.state.aegis_role = "admin"
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

        role = normalize_role(request.headers.get(self.role_header) or self.default_role)
        request.state.aegis_role = role

        if self.enforce_rbac:
            needed = _permission_for_request(request.method, request.url.path)
            if needed and not has_permission(role, needed):
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": {
                            "code": "FORBIDDEN",
                            "message": f"Role '{role}' lacks permission '{needed}'",
                            "role": role,
                            "required": needed,
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
        role_header=str(cfg.get("role_header", "X-Aegis-Role")),
        default_role=str(cfg.get("default_role", "analyst")),
        enforce_rbac=bool(cfg.get("enforce_rbac", True)),
    )
