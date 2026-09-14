"""Password hashing (stdlib PBKDF2-HMAC-SHA256 — no plaintext storage)."""
from __future__ import annotations

import hashlib
import hmac
import secrets


_ITERATIONS = 200_000
_ALGO = "pbkdf2_sha256"


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if not password or len(password) > 256:
        raise ValueError("invalid password")
    salt_b = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_b, _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${salt_b.hex()}${dk.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iters_s, salt_hex, hash_hex = encoded.split("$", 3)
        if algo != _ALGO:
            return False
        iters = int(iters_s)
        salt_b = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_b, iters)
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False
