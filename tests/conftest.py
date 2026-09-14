"""Pytest bootstrap — Agg backend + isolated SQLite schema for CI."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
# P5 enables rate limits by default; keep unit tests deterministic (opt out for dedicated rate-limit tests)
os.environ.setdefault("DISABLE_RATE_LIMIT", "true")

# Must be set before `database.db` / FastAPI app import so CI has no dependency on ids.db
_test_db = Path(tempfile.gettempdir()) / "aegis_ids_pytest.db"
os.environ.setdefault("IDS_DB_PATH", str(_test_db))

import pytest

from database.db import init_db


@pytest.fixture(scope="session", autouse=True)
def _ensure_database_schema() -> None:
    """Create tables even when FastAPI lifespan does not run under TestClient."""
    init_db()
