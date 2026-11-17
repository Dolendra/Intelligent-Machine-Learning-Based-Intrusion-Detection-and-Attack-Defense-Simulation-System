"""R-05 (SEC-1, SEC-2, SEC-7): no forgeable token secret, no published seed passwords."""
from __future__ import annotations

import base64
import hashlib
import hmac
import importlib
import json
import time

import pytest

from security.auth import posture, tokens
from security.auth.posture import InsecureConfigurationError, enforce_startup_posture
from security.auth.users import LEGACY_PUBLISHED_PASSWORDS, UserStore, user_store

OLD_PUBLIC_CONSTANT = "aegis-dev-only-change-me"


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _forge(secret: str, username: str = "admin") -> str:
    now = int(time.time())
    body = _b64(json.dumps({"sub": username, "username": username, "role": "admin", "iat": now,
                            "exp": now + 600, "typ": "access"}, separators=(",", ":"),
                           sort_keys=True).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def test_published_constant_is_gone_from_token_module():
    src = open(tokens.__file__, encoding="utf-8").read()
    assert OLD_PUBLIC_CONSTANT not in src


def test_token_forged_with_old_constant_is_rejected_without_secret(monkeypatch):
    monkeypatch.delenv("AEGIS_AUTH_SECRET", raising=False)
    with pytest.raises(ValueError, match="signature"):
        tokens.verify_token(_forge(OLD_PUBLIC_CONSTANT))


def test_api_key_is_not_the_signing_key(monkeypatch):
    monkeypatch.delenv("AEGIS_AUTH_SECRET", raising=False)
    monkeypatch.setenv("AEGIS_API_KEY", "some-api-key-value")
    assert tokens.auth_secret() != "some-api-key-value"
    with pytest.raises(ValueError, match="signature"):
        tokens.verify_token(_forge("some-api-key-value"))


def test_ephemeral_secret_differs_between_processes(monkeypatch):
    monkeypatch.delenv("AEGIS_AUTH_SECRET", raising=False)
    first = tokens.auth_secret()
    reloaded = importlib.reload(tokens)
    try:
        assert reloaded.auth_secret() != first
    finally:
        importlib.reload(tokens)


@pytest.mark.parametrize("secret,problem", [
    (None, "not set"),
    ("short-secret", "shorter than"),
])
def test_auth_enabled_requires_strong_secret(monkeypatch, secret, problem):
    monkeypatch.setenv("AEGIS_ENV", "production")
    monkeypatch.setenv("AEGIS_AUTH_ENABLED", "true")
    for k in posture.KILL_SWITCHES:
        monkeypatch.delenv(k, raising=False)
    if secret is None:
        monkeypatch.delenv("AEGIS_AUTH_SECRET", raising=False)
    else:
        monkeypatch.setenv("AEGIS_AUTH_SECRET", secret)
    with pytest.raises(InsecureConfigurationError, match=problem):
        enforce_startup_posture()


def test_secret_equal_to_api_key_is_refused(monkeypatch):
    monkeypatch.setenv("AEGIS_ENV", "production")
    monkeypatch.setenv("AEGIS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AEGIS_AUTH_SECRET", "k" * 40)
    monkeypatch.setenv("AEGIS_API_KEY", "k" * 40)
    with pytest.raises(InsecureConfigurationError, match="differ"):
        enforce_startup_posture()


def test_published_seed_passwords_do_not_log_in():
    from security.auth.service import AuthError, login

    for user, pw in zip(("admin", "responder", "analyst", "viewer"), LEGACY_PUBLISHED_PASSWORDS):
        with pytest.raises(AuthError):
            login(user, pw)


def test_seed_without_env_password_gets_random_unusable_password(monkeypatch, tmp_path):
    """A fresh DB seeded with no AEGIS_SEED_PASSWORD_* has no known password."""
    import database.db as dbmod
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f"sqlite:///{tmp_path / 'seed.db'}")
    dbmod.Base.metadata.create_all(engine)
    monkeypatch.setattr("security.auth.users.SessionLocal", sessionmaker(bind=engine))
    for u in ("ADMIN", "RESPONDER", "ANALYST", "VIEWER"):
        monkeypatch.delenv(f"AEGIS_SEED_PASSWORD_{u}", raising=False)
    monkeypatch.delenv("AEGIS_SEED_USERS_JSON", raising=False)
    store = UserStore()
    store.ensure_seeded()
    assert store.get("admin") is not None
    assert store.users_with_legacy_passwords() == []
    for pw in LEGACY_PUBLISHED_PASSWORDS:
        assert store.authenticate("admin", pw) is None


def test_legacy_password_is_detected_and_rotated(monkeypatch, tmp_path):
    import database.db as dbmod
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    dbmod.Base.metadata.create_all(engine)
    monkeypatch.setattr("security.auth.users.SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setenv("AEGIS_SEED_USERS_JSON", json.dumps(
        [{"username": "admin", "role": "admin", "password": LEGACY_PUBLISHED_PASSWORDS[0]}]))
    store = UserStore()
    store.ensure_seeded()
    assert store.users_with_legacy_passwords() == ["admin"]       # an old database is detected
    assert store.set_password("admin", "a-new-rotated-password-123")
    assert store.users_with_legacy_passwords() == []
    assert store.authenticate("admin", "a-new-rotated-password-123") is not None


def test_startup_refuses_while_published_password_is_active(monkeypatch):
    """Lifespan check: auth enabled + an account with a published password -> refuse."""
    import backend.main as main

    monkeypatch.setattr(main.SECURITY_POSTURE, "auth_enabled", True)
    monkeypatch.setattr(user_store, "users_with_legacy_passwords", lambda: ["admin"])
    from fastapi.testclient import TestClient

    with pytest.raises(InsecureConfigurationError, match="published default password"):
        with TestClient(main.app):
            pass


def test_suite_never_uses_the_developer_database():
    """conftest must isolate the DB even when a developer .env sets IDS_DB_URL."""
    from database.url import resolve_database_url
    from ids_config import ROOT

    url = resolve_database_url()
    assert "aegis_pytest_" in url
    assert (ROOT / "database" / "ids.db").as_posix() not in url
