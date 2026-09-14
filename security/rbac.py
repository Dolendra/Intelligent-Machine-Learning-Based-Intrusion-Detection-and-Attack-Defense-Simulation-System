"""Role-based access matrix for Stage-2 Phase C (opt-in with API auth)."""
from __future__ import annotations

from typing import Iterable

# Coarse permissions used by middleware / route guards
PERMISSIONS = {
    "read_health",
    "read_models",
    "read_incidents",
    "write_detect",
    "write_incidents",
    "write_simulation",
    "write_ingest",
    "admin",
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": set(PERMISSIONS),
    "analyst": {
        "read_health",
        "read_models",
        "read_incidents",
        "write_detect",
        "write_incidents",
        "write_simulation",
        "write_ingest",
    },
    "viewer": {
        "read_health",
        "read_models",
        "read_incidents",
    },
    "ml_research": {
        "read_health",
        "read_models",
        "read_incidents",
        "write_detect",
    },
}

DEFAULT_ROLE = "analyst"


def normalize_role(role: str | None) -> str:
    r = (role or DEFAULT_ROLE).strip().lower()
    return r if r in ROLE_PERMISSIONS else DEFAULT_ROLE


def permissions_for(role: str | None) -> set[str]:
    return set(ROLE_PERMISSIONS[normalize_role(role)])


def has_permission(role: str | None, permission: str) -> bool:
    return permission in permissions_for(role)


def require_any(role: str | None, needed: Iterable[str]) -> bool:
    have = permissions_for(role)
    return any(p in have for p in needed)


def rbac_summary() -> dict:
    return {
        "default_role": DEFAULT_ROLE,
        "roles": sorted(ROLE_PERMISSIONS.keys()),
        "permissions": sorted(PERMISSIONS),
        "matrix": {role: sorted(perms) for role, perms in ROLE_PERMISSIONS.items()},
        "notes": [
            "RBAC is enforced only when api.auth.enabled=true (or AEGIS_API_KEY + enabled).",
            "Pass role via X-Aegis-Role when authenticated; defaults to analyst.",
            "This is scaffolding for Stage-2 — not a full IdP/OAuth SSO implementation.",
        ],
    }
