"""Local user directory — durable via SQLite/Postgres (P6)."""
from __future__ import annotations

import json
import logging
import os
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from database.db import SessionLocal, UserAccount
from security.auth.passwords import hash_password, verify_password
from security.rbac import ROLE_PERMISSIONS, normalize_role

log = logging.getLogger("aegis.auth")

# Seed accounts (user_id, username). R-05 (SEC-2): no password is published in source.
# A seed gets AEGIS_SEED_PASSWORD_<USER> if set, otherwise a random password that is never
# shown or logged (the account cannot log in until rotated with
# scripts/70_rotate_credentials.py). AEGIS_SEED_USERS_JSON replaces the whole seed list.
_DEFAULT_SEEDS: list[tuple[str, str]] = [
    ("admin", "admin"),
    ("responder", "responder"),
    ("analyst", "analyst"),
    ("viewer", "viewer"),
]

# Passwords that were published in earlier versions of this repository. They are kept ONLY
# as a deny-list: startup refuses to run with auth enabled while any active account still
# accepts one of them, and the rotation script replaces them.
LEGACY_PUBLISHED_PASSWORDS: tuple[str, ...] = (
    "ChangeMeAdmin!",
    "ChangeMeResponder!",
    "ChangeMeAnalyst!",
    "ChangeMeViewer!",
)


@dataclass
class UserRecord:
    user_id: str
    username: str
    role: str
    password_hash: str
    active: bool = True

    def public_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "active": self.active,
            "permissions": sorted(ROLE_PERMISSIONS.get(self.role, set())),
        }


def _row_to_record(row: UserAccount) -> UserRecord:
    return UserRecord(
        user_id=row.user_id,
        username=row.username,
        role=row.role,
        password_hash=row.password_hash,
        active=bool(row.active),
    )


class UserStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._ready = False

    def ensure_seeded(self) -> None:
        """Idempotent seed — safe to call after migrations."""
        with self._lock:
            self._load_seeds_if_empty()
            self._ready = True

    def _ensure_ready(self) -> None:
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            try:
                self._load_seeds_if_empty()
                self._ready = True
            except Exception:
                # Schema may not exist yet during early import; callers retry after init_db.
                pass

    def _load_seeds_if_empty(self) -> None:
        with SessionLocal() as db:
            count = db.query(UserAccount).count()
            if count > 0:
                return
            custom = os.getenv("AEGIS_SEED_USERS_JSON")
            if custom:
                try:
                    rows = json.loads(custom)
                    for row in rows:
                        self._upsert_db(
                            db,
                            username=str(row["username"]),
                            role=str(row.get("role", "viewer")),
                            password=str(row["password"]),
                            user_id=str(row.get("user_id") or row["username"]),
                        )
                    db.commit()
                    return
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    pass
            unset: list[str] = []
            for user_id, username in _DEFAULT_SEEDS:
                env_pw = os.getenv(f"AEGIS_SEED_PASSWORD_{username.upper()}")
                if not env_pw:
                    unset.append(username)
                self._upsert_db(
                    db,
                    username=username,
                    role=username if username in ROLE_PERMISSIONS else "viewer",
                    password=env_pw or secrets.token_urlsafe(24),
                    user_id=user_id,
                )
            db.commit()
            if unset:
                log.warning(
                    "seed accounts %s created with random, undisclosed passwords; set them with "
                    "scripts/70_rotate_credentials.py or AEGIS_SEED_PASSWORD_<USER> before first use",
                    unset,
                )

    def _upsert_db(
        self,
        db,
        *,
        username: str,
        role: str,
        password: str,
        user_id: str | None = None,
    ) -> UserRecord:
        uname = username.strip().lower()
        uid = (user_id or uname).strip().lower()
        rec = UserRecord(
            user_id=uid,
            username=uname,
            role=normalize_role(role),
            password_hash=hash_password(password),
            active=True,
        )
        row = db.query(UserAccount).filter(UserAccount.username == uname).first()
        now = datetime.now(timezone.utc)
        if row is None:
            db.add(
                UserAccount(
                    user_id=rec.user_id,
                    username=rec.username,
                    role=rec.role,
                    password_hash=rec.password_hash,
                    active=1,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            row.user_id = rec.user_id
            row.role = rec.role
            row.password_hash = rec.password_hash
            row.active = 1
            row.updated_at = now
        return rec

    def upsert(self, *, username: str, role: str, password: str, user_id: str | None = None) -> UserRecord:
        self._ensure_ready()
        with self._lock:
            with SessionLocal() as db:
                rec = self._upsert_db(
                    db, username=username, role=role, password=password, user_id=user_id
                )
                db.commit()
                return rec

    def get(self, username: str) -> UserRecord | None:
        self._ensure_ready()
        with SessionLocal() as db:
            row = (
                db.query(UserAccount)
                .filter(UserAccount.username == username.strip().lower())
                .first()
            )
            return _row_to_record(row) if row else None

    def authenticate(self, username: str, password: str) -> UserRecord | None:
        user = self.get(username)
        if user is None or not user.active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def set_password(self, username: str, password: str) -> bool:
        """Replace a user's password hash. Returns False if the user does not exist."""
        if not password:
            raise ValueError("password must not be empty")
        self._ensure_ready()
        with self._lock, SessionLocal() as db:
            row = (
                db.query(UserAccount)
                .filter(UserAccount.username == username.strip().lower())
                .first()
            )
            if row is None:
                return False
            row.password_hash = hash_password(password)
            db.commit()
            return True

    def users_with_legacy_passwords(self) -> list[str]:
        """Active usernames whose password is one of LEGACY_PUBLISHED_PASSWORDS."""
        self._ensure_ready()
        with SessionLocal() as db:
            rows = db.query(UserAccount).filter(UserAccount.active != 0).all()
            return sorted(
                r.username
                for r in rows
                if any(verify_password(pw, r.password_hash) for pw in LEGACY_PUBLISHED_PASSWORDS)
            )

    def list_public(self) -> list[dict[str, Any]]:
        self._ensure_ready()
        with SessionLocal() as db:
            rows = db.query(UserAccount).order_by(UserAccount.username.asc()).all()
            return [_row_to_record(r).public_dict() for r in rows]


user_store = UserStore()
