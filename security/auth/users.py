"""Local user directory for P4 (prototype — not a full IdP)."""
from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass
from typing import Any

from security.auth.passwords import hash_password, verify_password
from security.rbac import ROLE_PERMISSIONS, normalize_role

# Dev seed credentials — override via AEGIS_SEED_PASSWORD_<USER> or disable in prod docs.
_DEFAULT_SEEDS: list[tuple[str, str, str]] = [
    ("admin", "admin", "ChangeMeAdmin!"),
    ("responder", "responder", "ChangeMeResponder!"),
    ("analyst", "analyst", "ChangeMeAnalyst!"),
    ("viewer", "viewer", "ChangeMeViewer!"),
]


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


class UserStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._users: dict[str, UserRecord] = {}
        self._load_seeds()

    def _load_seeds(self) -> None:
        custom = os.getenv("AEGIS_SEED_USERS_JSON")
        if custom:
            try:
                rows = json.loads(custom)
                for row in rows:
                    self.upsert(
                        username=str(row["username"]),
                        role=str(row.get("role", "viewer")),
                        password=str(row["password"]),
                        user_id=str(row.get("user_id") or row["username"]),
                    )
                return
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                pass
        for user_id, username, password in _DEFAULT_SEEDS:
            env_pw = os.getenv(f"AEGIS_SEED_PASSWORD_{username.upper()}")
            self.upsert(
                username=username,
                role=username if username in ROLE_PERMISSIONS else "viewer",
                password=env_pw or password,
                user_id=user_id,
            )

    def upsert(self, *, username: str, role: str, password: str, user_id: str | None = None) -> UserRecord:
        uname = username.strip().lower()
        rec = UserRecord(
            user_id=(user_id or uname).strip().lower(),
            username=uname,
            role=normalize_role(role),
            password_hash=hash_password(password),
            active=True,
        )
        with self._lock:
            self._users[uname] = rec
        return rec

    def get(self, username: str) -> UserRecord | None:
        with self._lock:
            return self._users.get(username.strip().lower())

    def authenticate(self, username: str, password: str) -> UserRecord | None:
        user = self.get(username)
        if user is None or not user.active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def list_public(self) -> list[dict[str, Any]]:
        with self._lock:
            return [u.public_dict() for u in self._users.values()]


user_store = UserStore()
