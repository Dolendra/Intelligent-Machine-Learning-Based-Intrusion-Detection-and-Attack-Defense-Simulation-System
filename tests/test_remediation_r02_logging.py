"""R-02 (SEC-5/ARCH-3, ARCH-22, SEC-8): logging survives startup; identities and login failures are recorded."""
from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from backend.main import app
from database.db import init_db

AEGIS_LOGGERS = ("aegis", "aegis.api", "aegis.api.errors", "aegis.security", "aegis.ops",
                 "aegis.auth", "aegis.ingest.audit", "aegis.response.audit")


def test_startup_migration_keeps_app_loggers_enabled():
    for name in AEGIS_LOGGERS:
        logging.getLogger(name)                      # make sure they exist before startup
    logging.getLogger().setLevel(logging.INFO)       # independent of earlier tests
    root_before = logging.getLogger().level
    init_db()                                        # runs `alembic upgrade head` in-process
    with TestClient(app):                            # full lifespan (init_db again)
        pass
    for name in AEGIS_LOGGERS:
        assert logging.getLogger(name).disabled is False, name
    assert logging.getLogger().level == root_before
    assert logging.getLogger().getEffectiveLevel() <= logging.INFO


def test_alembic_cli_path_does_not_disable_existing_loggers():
    """Even when Alembic configures logging (CLI path), existing loggers stay enabled."""
    from alembic import command
    from alembic.config import Config

    from database.db import DATABASE_URL
    from ids_config import ROOT

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)          # configure_logger defaults to True
    root_level = logging.getLogger().level
    try:
        command.upgrade(cfg, "head")
        assert logging.getLogger("aegis.security").disabled is False
        assert logging.getLogger("aegis.api.errors").disabled is False
    finally:
        logging.getLogger().setLevel(root_level)


def test_server_errors_are_logged(caplog):
    from fastapi import FastAPI

    from backend.middleware.errors import attach_error_handlers

    init_db()
    mini = FastAPI()

    @mini.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    attach_error_handlers(mini)
    with caplog.at_level(logging.ERROR, logger="aegis.api.errors"):
        r = TestClient(mini, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500
    assert any("unhandled" in rec.getMessage() for rec in caplog.records)


def test_failed_password_login_is_a_durable_security_event():
    from database.db import SecurityAuditEvent, SessionLocal

    with SessionLocal() as db:
        before = db.query(SecurityAuditEvent).filter(SecurityAuditEvent.event == "authentication_failure").count()
    r = TestClient(app).post("/api/auth/login", json={"username": "nobody-r02", "password": "wrong"})
    assert r.status_code == 401
    with SessionLocal() as db:
        after = db.query(SecurityAuditEvent).filter(SecurityAuditEvent.event == "authentication_failure").count()
    assert after == before + 1


def test_logging_middleware_reads_auth_identity():
    from types import SimpleNamespace

    from backend.middleware.logging_mw import _state_user

    req = SimpleNamespace(state=SimpleNamespace(aegis_user={"username": "alice"}, aegis_role="analyst"))
    assert _state_user(req) == "alice"
    req = SimpleNamespace(state=SimpleNamespace(aegis_user=None, aegis_role="anonymous"))
    assert _state_user(req) is None
