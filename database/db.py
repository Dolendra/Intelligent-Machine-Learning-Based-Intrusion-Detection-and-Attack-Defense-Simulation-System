from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

from ids_config import ROOT

DATABASE_URL = f"sqlite:///{ROOT / 'database' / 'ids.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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


class SimulationRecord(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True)
    attack_type = Column(String(64))
    state = Column(String(32))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    payload = Column(Text)


def init_db() -> None:
    (ROOT / "database").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
