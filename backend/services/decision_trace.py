"""Decision-trace builder — signature Aegis “why did the system do this?” view."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from database.db import Incident, IncidentEvent


def build_trace_from_prediction(payload: dict[str, Any], explain: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a linear decision narrative from a live prediction (+ optional XAI)."""
    steps: list[dict[str, Any]] = []
    intensity = None
    if isinstance(payload.get("risk_factors"), dict):
        intensity = payload["risk_factors"].get("intensity")

    steps.append(
        {
            "stage": "traffic",
            "title": "Traffic / features",
            "detail": (
                f"Flow scored with certainty={payload.get('certainty', 'n/a')}; "
                f"binary attack probability={float(payload.get('binary_proba_attack') or 0):.3f}"
                + (f"; intensity≈{intensity}" if intensity is not None else "")
            ),
        }
    )
    steps.append(
        {
            "stage": "ml",
            "title": "ML detection",
            "detail": (
                f"{'ATTACK' if payload.get('is_attack') else 'BENIGN'} → "
                f"{payload.get('attack_type')} "
                f"(confidence {float(payload.get('confidence') or 0):.0%}, "
                f"threshold {payload.get('threshold')})"
            ),
        }
    )
    if explain:
        tops = explain.get("top_features") or []
        names = ", ".join(str(t.get("feature")) for t in tops[:3]) or "n/a"
        method = explain.get("actual_method") or explain.get("method") or "xai"
        fb = explain.get("fallback_used")
        steps.append(
            {
                "stage": "xai",
                "title": "Explainability",
                "detail": f"{method}: top drivers {names}"
                + (" (fallback_used=true)" if fb else ""),
            }
        )
    steps.append(
        {
            "stage": "risk",
            "title": "Risk scoring",
            "detail": f"Risk {payload.get('risk_score')} / 100 → {payload.get('severity')}",
        }
    )
    rec = payload.get("recommendation") or {}
    if isinstance(rec, dict):
        primary = rec.get("primary", "")
        rules = rec.get("rule_hits") or []
    else:
        primary = str(rec)
        rules = []
    steps.append(
        {
            "stage": "recommendation",
            "title": "Recommendation",
            "detail": primary + (f" · rules={len(rules)}" if rules else ""),
        }
    )
    if payload.get("incident_id"):
        steps.append(
            {
                "stage": "incident",
                "title": "Incident",
                "detail": (
                    f"{payload['incident_id']}"
                    + (f" · campaign {payload.get('campaign_id')}" if payload.get("campaign_id") else "")
                    + (" · deduplicated" if payload.get("deduplicated") else "")
                    + (" · escalated" if payload.get("escalated") else "")
                ),
            }
        )
    return {
        "title": "WHY DID AEGIS DO THIS?",
        "advisory_only": True,
        "steps": steps,
    }


def build_trace_from_incident(db: Session, incident_id: str) -> dict[str, Any] | None:
    row = db.query(Incident).filter(Incident.incident_code == incident_id).first()
    if not row:
        return None
    events = (
        db.query(IncidentEvent)
        .filter(IncidentEvent.incident_code == incident_id)
        .order_by(IncidentEvent.timestamp.asc())
        .all()
    )
    steps: list[dict[str, Any]] = [
        {
            "stage": "ml",
            "title": "Detection",
            "detail": f"{row.attack_type} · confidence {float(row.confidence or 0):.0%}",
        },
        {
            "stage": "risk",
            "title": "Risk",
            "detail": f"Risk {row.risk_score} → {row.severity} (hits={getattr(row, 'hit_count', 1)})",
        },
        {
            "stage": "recommendation",
            "title": "Recommendation",
            "detail": row.recommendation or "n/a",
        },
        {
            "stage": "incident",
            "title": "Lifecycle",
            "detail": f"Status {row.status}"
            + (f" · campaign {row.campaign_id}" if getattr(row, "campaign_id", None) else "")
            + (f" · source {row.source_ref}" if row.source_ref else ""),
        },
    ]
    for e in events[-8:]:
        steps.append(
            {
                "stage": "event",
                "title": f"{e.old_status or '—'} → {e.new_status}",
                "detail": (e.notes or e.action or "")[:200],
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
        )
    return {
        "title": "WHY DID AEGIS DO THIS?",
        "incident_id": incident_id,
        "advisory_only": True,
        "steps": steps,
    }
