"""Static asset inventory for risk context (prototype)."""
from __future__ import annotations

from typing import Any

# Criticality scale 1–5 (maps into risk engine asset_criticality)
ASSETS: dict[str, dict[str, Any]] = {
    "web-server": {
        "id": "web-server",
        "name": "Web Server",
        "criticality": 5,
        "tier": "production",
    },
    "database": {
        "id": "database",
        "name": "Database",
        "criticality": 5,
        "tier": "production",
    },
    "app-server": {
        "id": "app-server",
        "name": "Application Server",
        "criticality": 4,
        "tier": "production",
    },
    "dev-server": {
        "id": "dev-server",
        "name": "Development Server",
        "criticality": 3,
        "tier": "non-production",
    },
    "employee-pc": {
        "id": "employee-pc",
        "name": "Employee PC",
        "criticality": 2,
        "tier": "endpoint",
    },
}


def list_assets() -> list[dict[str, Any]]:
    return list(ASSETS.values())


def get_asset(asset_id: str) -> dict[str, Any] | None:
    return ASSETS.get(asset_id)


def criticality_for(asset_id: str | None) -> float | None:
    if not asset_id:
        return None
    asset = ASSETS.get(asset_id)
    if not asset:
        return None
    return float(asset["criticality"])
