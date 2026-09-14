from __future__ import annotations

import os
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

from database.url import engine_kwargs_for, resolve_database_url
from ids_config import ROOT

DATABASE_URL = resolve_database_url()
engine = create_engine(DATABASE_URL, **engine_kwargs_for(DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_code = Column(String(32), unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    attack_type = Column(String(64), index=True)
    is_attack = Column(Integer, default=0)
    confidence = Column(Float)
    risk_score = Column(Float)
    severity = Column(String(16), index=True)
    recommendation = Column(Text)
    explanation = Column(Text)
    status = Column(String(32), default="Detected")
    source_ref = Column(String(128), nullable=True)
    analyst_notes = Column(Text, nullable=True)
    defense_action = Column(String(128), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    asset_criticality = Column(Float, nullable=True)
    campaign_id = Column(String(32), nullable=True, index=True)
    hit_count = Column(Integer, default=1)


class SimulationRecord(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True)
    attack_type = Column(String(64))
    state = Column(String(32))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    payload = Column(Text)


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id = Column(Integer, primary_key=True, index=True)
    incident_code = Column(String(32), index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    old_status = Column(String(32), nullable=True)
    new_status = Column(String(32))
    actor = Column(String(64), default="system")
    notes = Column(Text, nullable=True)
    action = Column(String(64), nullable=True)


def init_db() -> None:
    """Create/upgrade schema.

    Prefer Alembic when available; fall back to create_all + PRAGMA alters for
    prototype DBs that predate migrations.
    """
    (ROOT / "database").mkdir(parents=True, exist_ok=True)
    try:
        from alembic import command
        from alembic.config import Config

        cfg = Config(str(ROOT / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        command.upgrade(cfg, "head")
        return
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.getLogger("aegis.db").warning(
            "Alembic upgrade skipped/failed (%s); using create_all fallback. "
            "If schema drifts, run `alembic upgrade head` manually.",
            exc,
        )

    Base.metadata.create_all(bind=engine)
    # Lightweight SQLite column add for existing prototype DBs
    with engine.connect() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(incidents)").fetchall()}
        alters = []
        if "analyst_notes" not in cols:
            alters.append("ALTER TABLE incidents ADD COLUMN analyst_notes TEXT")
        if "defense_action" not in cols:
            alters.append("ALTER TABLE incidents ADD COLUMN defense_action VARCHAR(128)")
        if "resolved_at" not in cols:
            alters.append("ALTER TABLE incidents ADD COLUMN resolved_at DATETIME")
        if "asset_criticality" not in cols:
            alters.append("ALTER TABLE incidents ADD COLUMN asset_criticality FLOAT")
        if "campaign_id" not in cols:
            alters.append("ALTER TABLE incidents ADD COLUMN campaign_id VARCHAR(32)")
        if "hit_count" not in cols:
            alters.append("ALTER TABLE incidents ADD COLUMN hit_count INTEGER DEFAULT 1")
        for stmt in alters:
            conn.exec_driver_sql(stmt)
        if alters:
            conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
