"""Database URL helpers — SQLite by default, PostgreSQL when IDS_DB_URL is set."""
from __future__ import annotations

import os
from typing import Any

from ids_config import ROOT, load_config


def resolve_database_url() -> str:
    """Prefer IDS_DB_URL, then config database.url, else local SQLite file."""
    env = os.getenv("IDS_DB_URL")
    if env:
        return env
    cfg = load_config().get("database", {}) or {}
    configured = str(cfg.get("url") or "").strip()
    if configured:
        return configured
    path = os.getenv("IDS_DB_PATH") or str(ROOT / "database" / "ids.db")
    # SQLAlchemy SQLite absolute path form
    return f"sqlite:///{path}"


def engine_kwargs_for(url: str) -> dict[str, Any]:
    """Dialect-specific create_engine kwargs."""
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    # PostgreSQL / other servers
    return {
        "pool_pre_ping": True,
        "pool_size": int(os.getenv("IDS_DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("IDS_DB_MAX_OVERFLOW", "10")),
    }


def database_info(url: str | None = None) -> dict[str, Any]:
    resolved = url or resolve_database_url()
    dialect = resolved.split(":", 1)[0]
    safe = resolved
    if "@" in resolved:
        # redact credentials
        try:
            prefix, rest = resolved.split("://", 1)
            creds, hostpart = rest.split("@", 1)
            safe = f"{prefix}://***:***@{hostpart}"
        except ValueError:
            safe = f"{dialect}://***"
    return {
        "dialect": dialect,
        "url_redacted": safe,
        "sqlite_default": dialect == "sqlite",
        "postgres_ready": dialect.startswith("postgresql"),
        "env_override": bool(os.getenv("IDS_DB_URL")),
        "notes": [
            "Default remains SQLite for the v1.1 research/demo baseline.",
            "Set IDS_DB_URL=postgresql+psycopg://user:pass@host:5432/aegis for Stage-2 Postgres.",
            "Run alembic upgrade head after pointing at a new database.",
        ],
    }
