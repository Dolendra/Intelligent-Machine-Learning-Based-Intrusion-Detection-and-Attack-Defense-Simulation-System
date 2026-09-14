"""Retention policy helpers (P6) — purge is explicit; no silent deletion of audit by default."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from database.db import (
    Incident,
    IncidentEvent,
    ModelVersionRef,
    ResponseActionRecord,
    ResponseAuditEvent,
    SecurityAuditEvent,
    SessionLocal,
    SimulationRecord,
    UserAccount,
)
from ids_config import load_config


DEFAULT_RETENTION = {
    # Rationale: security evidence / SOC investigation window for a research prototype.
    "audit_days": 365,
    "incidents_days": 365,
    # Detection records are Incident rows (no separate alerts table).
    "alerts_days": 365,
    "simulations_days": 90,
    # Raw PCAP / temp files are filesystem concerns — short retention.
    "raw_pcap_hours": 24,
    "temp_files_hours": 1,
}


def retention_policy() -> dict[str, Any]:
    cfg = (load_config().get("database") or {}).get("retention") or {}
    policy = dict(DEFAULT_RETENTION)
    for key, default in DEFAULT_RETENTION.items():
        if key in cfg and cfg[key] is not None:
            policy[key] = int(cfg[key])
    policy["notes"] = [
        "Audit and incidents default to long retention (security evidence).",
        "Simulations are shorter-lived operational artifacts.",
        "Raw PCAP and temp uploads are not DB rows — enforce via filesystem TTL.",
        "Detection/alert history is stored as Incident (+ IncidentEvent) rows.",
        "Purge helpers never delete response_audit_events newer than audit_days.",
    ]
    return policy


def _cutoff_days(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=max(0, days))


def purge_expired(*, dry_run: bool = True) -> dict[str, Any]:
    """Optional operator tool — defaults to dry_run so audit is not silently wiped."""
    policy = retention_policy()
    sim_cut = _cutoff_days(int(policy["simulations_days"]))
    with SessionLocal() as db:
        sim_q = db.query(SimulationRecord).filter(SimulationRecord.created_at < sim_cut)
        sim_count = sim_q.count()
        deleted_sims = 0
        if not dry_run and sim_count:
            deleted_sims = sim_q.delete(synchronize_session=False)
            db.commit()
    key = "would_delete" if dry_run else "deleted"
    return {
        "dry_run": dry_run,
        "policy": policy,
        key: {"simulations": sim_count if dry_run else deleted_sims},
    }


def persistence_summary() -> dict[str, Any]:
    with SessionLocal() as db:
        counts = {
            "users": db.query(UserAccount).count(),
            "incidents": db.query(Incident).count(),
            "incident_events": db.query(IncidentEvent).count(),
            "response_actions": db.query(ResponseActionRecord).count(),
            "response_audit_events": db.query(ResponseAuditEvent).count(),
            "security_audit_events": db.query(SecurityAuditEvent).count(),
            "simulations": db.query(SimulationRecord).count(),
            "model_version_refs": db.query(ModelVersionRef).count(),
        }
    return {
        "phase": "P6",
        "durable": [
            "users",
            "incidents",
            "incident_events",
            "response_actions",
            "response_audit_events",
            "security_audit_events",
            "simulations",
            "model_version_refs",
            "campaign_id on incidents",
        ],
        "ephemeral": [
            "ingest_queue jobs",
            "websocket EventHub clients",
            "rate-limit counters",
            "metrics buffers",
            "TestNetworkAdapter in-process controls",
        ],
        "counts": counts,
        "retention": retention_policy(),
        "backup_ready": True,
        "notes": [
            "Critical security state survives API/worker restart via SQLite/Postgres.",
            "Full disaster recovery / backup automation is P9.",
        ],
    }
