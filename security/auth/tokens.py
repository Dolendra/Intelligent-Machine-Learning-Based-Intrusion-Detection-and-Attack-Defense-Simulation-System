"""HMAC-signed bearer tokens (opaque to clients; role bound server-side)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def auth_secret() -> str:
    return (
        os.getenv("AEGIS_AUTH_SECRET")
        or os.getenv("AEGIS_API_KEY")
        or "aegis-dev-only-change-me"
    )


def token_ttl_seconds() -> int:
    return int(os.getenv("AEGIS_TOKEN_TTL_SECONDS", str(8 * 3600)))


def mint_token(
    *,
    user_id: str,
    username: str,
    role: str,
    ttl_seconds: int | None = None,
) -> tuple[str, dict[str, Any]]:
    now = int(time.time())
    ttl = ttl_seconds if ttl_seconds is not None else token_ttl_seconds()
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + ttl,
        "typ": "access",
    }
    body = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    sig = _b64e(hmac.new(auth_secret().encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}", payload


def verify_token(token: str) -> dict[str, Any]:
    try:
        body, sig = token.strip().split(".", 1)
    except ValueError as exc:
        raise ValueError("malformed token") from exc
    expected = _b64e(hmac.new(auth_secret().encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        raise ValueError("invalid token signature")
    payload = json.loads(_b64d(body).decode("utf-8"))
    if payload.get("typ") != "access":
        raise ValueError("invalid token type")
    exp = int(payload.get("exp") or 0)
    if int(time.time()) >= exp:
        raise ValueError("token expired")
    return payload
