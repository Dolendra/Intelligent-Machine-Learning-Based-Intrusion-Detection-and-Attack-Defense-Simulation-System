"""Sensitive-field redaction for operational logs (preserve P5 privacy posture)."""
from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
    "apikey",
    "x-api-key",
    "bearer",
    "cookie",
    "set-cookie",
    "private_key",
    "auth_secret",
    "aegis_auth_secret",
    "aegis_api_key",
}


def is_sensitive_key(key: str) -> bool:
    k = key.lower().replace("-", "_")
    if k in SENSITIVE_KEYS:
        return True
    return any(s in k for s in ("password", "secret", "token", "authorization", "api_key"))


def redact_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    if isinstance(value, str) and len(value) > 8 and value.lower().startswith("bearer "):
        return "Bearer [REDACTED]"
    return value


def redact_mapping(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    out: dict[str, Any] = {}
    for key, val in data.items():
        if is_sensitive_key(str(key)):
            out[str(key)] = "[REDACTED]"
        else:
            out[str(key)] = redact_value(val)
    return out
