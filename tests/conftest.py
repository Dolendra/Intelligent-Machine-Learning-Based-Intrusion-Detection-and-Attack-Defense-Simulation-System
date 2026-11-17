"""Pytest bootstrap — Agg backend + isolated SQLite schema for CI."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
# R-05: the API fails closed unless AEGIS_ENV is development/test; tests run as "test".
os.environ.setdefault("AEGIS_ENV", "test")
# P5 enables rate limits by default; keep unit tests deterministic (opt out for dedicated rate-limit tests)
os.environ.setdefault("DISABLE_RATE_LIMIT", "true")

# Must be set before `database.db` / FastAPI app import so CI has no dependency on ids.db
# Fresh database per test session (R-05): seed accounts get the test-only passwords below
# instead of inheriting accounts from an earlier run.
_test_db = Path(tempfile.mkdtemp(prefix="aegis_pytest_")) / "aegis_ids_pytest.db"
os.environ.setdefault("IDS_DB_PATH", str(_test_db))
# IDS_DB_URL takes precedence over IDS_DB_PATH, and ids_config loads a developer .env
# (override=False). Set it here first so the suite never touches database/ids.db.
os.environ.setdefault("IDS_DB_URL", "sqlite:///" + _test_db.as_posix())
from tests._seed_passwords import SEED_PASSWORDS  # noqa: E402

for _user, _pw in SEED_PASSWORDS.items():
    os.environ.setdefault(f"AEGIS_SEED_PASSWORD_{_user.upper()}", _pw)
# Cyber Range runs from tests go to a temp dir, not results/cyber_range/runs (committed evidence)
os.environ.setdefault("AEGIS_RANGE_RUNS_DIR", str(Path(tempfile.gettempdir()) / "aegis_pytest_range_runs"))

import pytest

from database.db import init_db


@pytest.fixture(scope="session", autouse=True)
def _ensure_database_schema() -> None:
    """Create tables even when FastAPI lifespan does not run under TestClient."""
    init_db()
