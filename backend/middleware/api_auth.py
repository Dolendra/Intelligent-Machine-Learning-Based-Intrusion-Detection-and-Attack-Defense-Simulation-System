"""Authentication + RBAC middleware (P4) — opt-in; demo baseline remains open when disabled."""
from __future__ import annotations

import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ids_config import load_config
from security.rbac import has_permission, normalize_role


PUBLIC_PATHS = {
    "/",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/health",
    "/api/ready",
    "/api/security/status",
    "/api/metrics",
    "/api/auth/login",
    "/api/auth/status",
}


def permission_for_request(method: str, path: str) -> str | None:
    """Map request to a coarse permission; None means allow when authenticated."""
    if path in PUBLIC_PATHS or path.startswith("/api/ws"):
        return None
    if path.startswith("/api/auth/me") or path.startswith("/api/auth/logout"):
        return None  # any authenticated user
    if path.startswith("/api/auth/users"):
        return "admin"
    if method == "GET":
        if path.startswith("/api/models") or path.startswith("/api/experiments") or path.startswith("/api/drift"):
            return "read_models"
        if path.startswith("/api/incidents") or path.startswith("/api/analytics") or path.startswith("/api/campaigns") or path.startswith("/api/export"):
            return "read_incidents"
        if path.startswith("/api/response/adapters") or path.startswith("/api/response/capabilities"):
            return "read_incidents"
        if path.startswith("/api/response/actions"):
            return "read_incidents"
        if path.startswith("/api/ingest"):
            return "read_health"
        return "read_health"
    # Mutations
    if path.startswith("/api/response/actions"):
        if method == "POST" and (
            path.endswith("/approve")
            or path.endswith("/reject")
            or path.endswith("/execute")
            or path.endswith("/rollback")
            or path.endswith("/expire")
            or path.endswith("/sweep-expired")
        ):
            return "approve_response"
        return "write_response"
    if path.startswith("/api/response/adapters"):
        return "admin"
    if path.startswith("/api/predict") or path.startswith("/api/explain") or path.startswith("/api/risk") or path.startswith("/api/recommendation") or path.startswith("/api/response"):
        return "write_detect"
    if path.startswith("/api/incidents") or path.startswith("/api/campaigns"):
        return "write_incidents"
    if path.startswith("/api/simulation"):
        return "write_simulation"
    if path.startswith("/api/ingest"):
        return "write_ingest"
    return "admin"


# Back-compat alias for tests
_permission_for_request = permission_for_request


def actor_from_request(request: Request) -> str:
    """Stable audit identity — never trust client-supplied actor names."""
    identity = getattr(request.state, "aegis_user", None) or {}
    if identity.get("username"):
        return str(identity["username"])
    role = getattr(request.state, "aegis_role", None)
    if role and role != "anonymous":
        return str(role)
    return "anonymous"


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
        api_key_role: str = "admin",
        allow_role_header: bool = False,
        enforce_rbac: bool = True,
    ):
        super().__init__(app)
        self.enabled = bool(enabled)
        self.api_key = api_key or ""
        self.header_name = header_name
        self.role_header = role_header
        self.default_role = default_role
        self.api_key_role = normalize_role(api_key_role)
        self.allow_role_header = allow_role_header
        self.enforce_rbac = enforce_rbac
        # Auth is "armed" when enabled; API key is optional if bearer login is used
        self._require_auth = self.enabled

    def _is_public(self, path: str) -> bool:
        if path in PUBLIC_PATHS:
            return True
        if path.startswith("/api/ws"):
            return True
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        request.state.aegis_user = None
        request.state.aegis_role = "anonymous"
        request.state.aegis_auth_method = None

        if not self._require_auth or request.method == "OPTIONS" or self._is_public(path):
            return await call_next(request)

        if os.getenv("DISABLE_API_AUTH", "").lower() in {"1", "true", "yes"}:
            request.state.aegis_role = "admin"
            request.state.aegis_user = {
                "user_id": "dev",
                "username": "dev-admin",
                "role": "admin",
                "permissions": [],
                "auth_method": "disabled_override",
            }
            request.state.aegis_auth_method = "disabled_override"
            return await call_next(request)

        identity = None
        auth_header = request.headers.get("Authorization") or ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            from security.auth.service import AuthError, identity_from_bearer

            try:
                identity = identity_from_bearer(token)
            except AuthError as exc:
                return JSONResponse(
                    status_code=exc.http_status,
                    content={"detail": {"code": exc.code, "message": exc.message}},
                )
        else:
            provided = request.headers.get(self.header_name) or request.query_params.get("api_key")
            if not self.api_key or not provided or provided != self.api_key:
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": {
                            "code": "UNAUTHORIZED",
                            "message": "Missing or invalid Bearer token / API key",
                        }
                    },
                )
            # Role is server-bound for API keys (no client privilege escalation by default)
            role = self.api_key_role
            if self.allow_role_header:
                role = normalize_role(request.headers.get(self.role_header) or self.api_key_role)
            identity = {
                "user_id": "api-key",
                "username": f"api-key:{role}",
                "role": role,
                "permissions": [],
                "auth_method": "api_key",
            }

        assert identity is not None
        role = normalize_role(identity.get("role"))
        request.state.aegis_user = identity
        request.state.aegis_role = role
        request.state.aegis_auth_method = identity.get("auth_method")

        if self.enforce_rbac:
            needed = permission_for_request(request.method, path)
            if needed and not has_permission(role, needed):
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": {
                            "code": "FORBIDDEN",
                            "message": f"Role '{role}' lacks permission '{needed}'",
                            "role": role,
                            "user": identity.get("username"),
                            "required": needed,
                        }
                    },
                )
        return await call_next(request)


def attach_api_auth(app) -> None:
    cfg = load_config().get("api", {}).get("auth", {}) or {}
    key = os.getenv("AEGIS_API_KEY") or str(cfg.get("api_key") or "")
    enabled_env = os.getenv("AEGIS_AUTH_ENABLED")
    if enabled_env is not None:
        enabled = enabled_env.lower() in {"1", "true", "yes"}
    else:
        enabled = bool(cfg.get("enabled", False))
    allow_role = bool(cfg.get("allow_role_header", False))
    if os.getenv("AEGIS_ALLOW_ROLE_HEADER", "").lower() in {"1", "true", "yes"}:
        allow_role = True
    app.add_middleware(
        ApiKeyMiddleware,
        enabled=enabled,
        api_key=key,
        header_name=str(cfg.get("header", "X-API-Key")),
        role_header=str(cfg.get("role_header", "X-Aegis-Role")),
        default_role=str(cfg.get("default_role", "analyst")),
        api_key_role=str(cfg.get("api_key_role", "admin")),
        allow_role_header=allow_role,
        enforce_rbac=bool(cfg.get("enforce_rbac", True)),
    )
