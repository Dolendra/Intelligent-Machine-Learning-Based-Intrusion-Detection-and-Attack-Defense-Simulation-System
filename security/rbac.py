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
    "write_response",
    "approve_response",
    "admin",
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": set(PERMISSIONS),
    "responder": {
        "read_health",
        "read_models",
        "read_incidents",
        "write_detect",
        "write_incidents",
        "write_simulation",
        "write_ingest",
        "write_response",
        "approve_response",
    },
    "analyst": {
        "read_health",
        "read_models",
        "read_incidents",
        "write_detect",
        "write_incidents",
        "write_simulation",
        "write_ingest",
        "write_response",
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

# Human-readable matrix for docs / viva (matches ROLE_PERMISSIONS)
OPERATION_MATRIX = {
    "view_detections": {"viewer": True, "analyst": True, "responder": True, "admin": True},
    "view_shap": {"viewer": True, "analyst": True, "responder": True, "admin": True},
    "create_incident": {"viewer": False, "analyst": True, "responder": True, "admin": True},
    "propose_response": {"viewer": False, "analyst": True, "responder": True, "admin": True},
    "dry_run": {"viewer": False, "analyst": True, "responder": True, "admin": True},
    "approve_response": {"viewer": False, "analyst": False, "responder": True, "admin": True},
    "rollback_response": {"viewer": False, "analyst": False, "responder": True, "admin": True},
    "manage_users": {"viewer": False, "analyst": False, "responder": False, "admin": True},
}


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
        "operations": OPERATION_MATRIX,
        "notes": [
            "P4: RBAC enforced when api.auth.enabled=true (or AEGIS_AUTH_ENABLED=true).",
            "Bearer login binds role to the user record — clients cannot escalate via headers.",
            "API keys use server-configured api_key_role unless allow_role_header=true (demo only).",
            "write_response = propose/dry-run; approve_response = approve/reject/rollback/execute.",
            "Not a full IdP/OAuth SSO — local password + HMAC bearer for the prototype.",
        ],
    }
