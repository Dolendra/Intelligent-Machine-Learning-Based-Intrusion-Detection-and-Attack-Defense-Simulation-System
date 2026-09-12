"""Campaign correlation helpers for related incidents."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from database.db import Incident
from ids_config import load_config

# Typical kill-chain adjacency (prototype heuristic)
CHAIN_NEXT: dict[str, set[str]] = {
    "PortScan": {"BruteForce", "WebAttack", "Bot", "Infiltration"},
    "BruteForce": {"WebAttack", "Infiltration", "Bot"},
    "WebAttack": {"Infiltration", "Bot"},
    "Bot": {"DDoS", "DoS", "Infiltration"},
    "DoS": {"DDoS"},
    "DDoS": set(),
}


def campaign_window_minutes() -> int:
    return int(load_config().get("incident", {}).get("campaign_window_minutes", 30))


def find_related_campaign(
    db: Session,
    *,
    attack_type: str,
    source_ref: str | None,
    now: datetime | None = None,
) -> Incident | None:
    """Find an open incident that should share a campaign_id with this detection.

    Requires source_ref so unrelated flows are not glued together.
    """
    if not source_ref:
        return None
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=campaign_window_minutes())
    closed = ("Resolved", "FalsePositive")
    candidates = (
        db.query(Incident)
        .filter(
            Incident.source_ref == source_ref,
            Incident.created_at >= cutoff,
            ~Incident.status.in_(closed),
        )
        .order_by(Incident.created_at.desc())
        .limit(50)
        .all()
    )
    for row in candidates:
        if row.attack_type == attack_type:
            return row
        nxt = CHAIN_NEXT.get(row.attack_type or "", set())
        if attack_type in nxt:
            return row
    return None


def severity_rank(label: str | None) -> int:
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    return order.get((label or "").upper(), 0)


def escalate_severity(current: str | None, target: str | None, *, hit_count: int) -> str:
    """Escalate when repeated hits accumulate; never downgrade on escalation path."""
    base = target or current or "MEDIUM"
    if hit_count >= 8 and severity_rank(base) < severity_rank("CRITICAL"):
        base = "CRITICAL"
    elif hit_count >= 4 and severity_rank(base) < severity_rank("HIGH"):
        if severity_rank(base) < severity_rank("HIGH"):
            base = "HIGH"
    elif hit_count >= 2 and severity_rank(base) < severity_rank("MEDIUM"):
        base = "MEDIUM"
    # Prefer higher of current vs computed
    if severity_rank(current) > severity_rank(base):
        return (current or base).upper()
    return base.upper()


def new_campaign_id() -> str:
    import uuid

    return f"CMP-{uuid.uuid4().hex[:6].upper()}"


def campaign_summary(db: Session, campaign_id: str) -> dict[str, Any]:
    rows = (
        db.query(Incident)
        .filter(Incident.campaign_id == campaign_id)
        .order_by(Incident.created_at.asc())
        .all()
    )
    return {
        "campaign_id": campaign_id,
        "incident_count": len(rows),
        "attack_types": sorted({r.attack_type for r in rows if r.attack_type}),
        "progression": [r.attack_type for r in rows if r.attack_type],
        "max_risk": max((float(r.risk_score or 0) for r in rows), default=0.0),
        "max_severity": max((r.severity or "LOW" for r in rows), key=severity_rank, default="LOW"),
        "incidents": [
            {
                "incident_id": r.incident_code,
                "attack_type": r.attack_type,
                "risk_score": r.risk_score,
                "severity": r.severity,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


def list_campaigns(db: Session, limit: int = 30) -> list[dict[str, Any]]:
    rows = (
        db.query(Incident)
        .filter(Incident.campaign_id.isnot(None))
        .order_by(Incident.created_at.desc())
        .limit(500)
        .all()
    )
    by_id: dict[str, list[Incident]] = {}
    for r in rows:
        cid = r.campaign_id
        if not cid:
            continue
        by_id.setdefault(cid, []).append(r)
    items = []
    for cid, group in by_id.items():
        group_sorted = sorted(group, key=lambda x: x.created_at or datetime.min.replace(tzinfo=timezone.utc))
        items.append(
            {
                "campaign_id": cid,
                "incident_count": len(group_sorted),
                "attack_types": sorted({g.attack_type for g in group_sorted if g.attack_type}),
                "progression": [g.attack_type for g in group_sorted if g.attack_type],
                "max_risk": max((float(g.risk_score or 0) for g in group_sorted), default=0.0),
                "latest_at": group_sorted[-1].created_at.isoformat() if group_sorted[-1].created_at else None,
            }
        )
    items.sort(key=lambda x: x.get("latest_at") or "", reverse=True)
    return items[:limit]
