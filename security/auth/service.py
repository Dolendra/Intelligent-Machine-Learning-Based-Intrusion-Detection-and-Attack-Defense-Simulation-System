"""P4 authentication service — login, token validation, identity helpers."""
from __future__ import annotations

import logging
from typing import Any

from security.auth.tokens import mint_token, token_ttl_seconds, verify_token
from security.auth.users import UserRecord, user_store
from security.rbac import permissions_for

logger = logging.getLogger("aegis.auth")


class AuthError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 401) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def login(username: str, password: str) -> dict[str, Any]:
    user = user_store.authenticate(username, password)
    if user is None:
        logger.info("auth_failed username=%s", (username or "")[:64])
        raise AuthError("INVALID_CREDENTIALS", "Invalid username or password", http_status=401)
    token, claims = mint_token(user_id=user.user_id, username=user.username, role=user.role)
    logger.info("auth_login user=%s role=%s", user.username, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": token_ttl_seconds(),
        "user": user.public_dict(),
        "claims": {"exp": claims["exp"], "iat": claims["iat"]},
    }


def identity_from_bearer(token: str) -> dict[str, Any]:
    try:
        claims = verify_token(token)
    except ValueError as exc:
        msg = str(exc)
        code = "TOKEN_EXPIRED" if "expired" in msg else "INVALID_TOKEN"
        raise AuthError(code, msg, http_status=401) from exc
    user = user_store.get(str(claims.get("username") or ""))
    if user is None or not user.active:
        raise AuthError("INVALID_TOKEN", "User no longer active", http_status=401)
    # Role always from directory — never trust a stale/spoofed role claim alone
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "permissions": sorted(permissions_for(user.role)),
        "auth_method": "bearer",
    }


def identity_dict(user: UserRecord, *, auth_method: str) -> dict[str, Any]:
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "permissions": sorted(permissions_for(user.role)),
        "auth_method": auth_method,
    }


def auth_status(*, enabled: bool) -> dict[str, Any]:
    return {
        "phase": "P4",
        "enabled": enabled,
        "login_endpoint": "/api/auth/login",
        "me_endpoint": "/api/auth/me",
        "methods": ["bearer_password", "api_key"],
        "notes": [
            "When enabled, Bearer tokens bind role to the authenticated user (not client headers).",
            "API keys map to a server-configured role; X-Aegis-Role is ignored unless allow_role_header=true.",
            "UI hiding is not a security boundary — enforcement is server-side.",
        ],
    }
