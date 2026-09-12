"""Application services wrapping ML + security engines."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from database.db import Incident
from explainability.shap_engine import ExplanationEngine
from explainability.lime_engine import LimeExplanationEngine
from ids_config import load_config, resolve_path
from ml.prediction.predictor import FeatureValidationError, IDSPredictor, PredictionResult
from security.recommendations.engine import recommend
from security.risk.engine import compute_risk

INCIDENT_TRANSITIONS: dict[str, set[str]] = {
    "Detected": {"Triaged", "Investigating", "MitigationRecommended", "Simulating", "FalsePositive", "Resolved"},
    "Triaged": {"Investigating", "MitigationRecommended", "Simulating", "FalsePositive", "Resolved"},
    "Investigating": {"MitigationRecommended", "DefenseApplied", "Simulating", "FalsePositive", "Resolved"},
    "MitigationRecommended": {"DefenseApplied", "Simulating", "Monitoring", "Resolved"},
    "DefenseApplied": {"Monitoring", "Resolved", "Simulating"},
    "Simulating": {"DefenseApplied", "Monitoring", "Resolved", "MitigationRecommended"},
    "Monitoring": {"Resolved", "Investigating"},
    "Resolved": set(),
    "FalsePositive": set(),
}


@lru_cache(maxsize=1)
def get_predictor() -> IDSPredictor | None:
    cfg = load_config()
    model_dir = resolve_path(cfg["models"]["output_dir"])
    required = [
        model_dir / "feature_bundle.joblib",
        model_dir / "binary_best.joblib",
        model_dir / "multiclass_best.joblib",
    ]
    if not all(p.exists() for p in required):
        return None
    return IDSPredictor.from_artifacts(model_dir)


@lru_cache(maxsize=1)
def get_explainer() -> ExplanationEngine | None:
    predictor = get_predictor()
    if predictor is None:
        return None
    cfg = load_config()
    bg_path = resolve_path(cfg["models"]["output_dir"]) / "shap_background.npy"
    background = np.load(bg_path) if bg_path.exists() else None
    return ExplanationEngine(predictor, background=background)


@lru_cache(maxsize=1)
def get_lime_explainer() -> LimeExplanationEngine | None:
    predictor = get_predictor()
    if predictor is None:
        return None
    cfg = load_config()
    bg_path = resolve_path(cfg["models"]["output_dir"]) / "shap_background.npy"
    background = np.load(bg_path) if bg_path.exists() else None
    return LimeExplanationEngine(predictor, background=background)


def models_ready() -> bool:
    return get_predictor() is not None


def _intensity_from_features(features: dict[str, float]) -> float | None:
    for key in ("Flow Packets/s", "Flow Bytes/s"):
        if key in features:
            return min(1.0, abs(float(features[key])) / 1e5)
    return None


def _enrich_prediction(
    pred: PredictionResult,
    features: dict[str, float],
    *,
    asset_criticality: float | None = None,
) -> dict[str, Any]:
    confidence = pred.multiclass_confidence if pred.is_attack else pred.binary_confidence
    intensity = _intensity_from_features(features)
    risk = compute_risk(
        pred.attack_type,
        confidence,
        pred.is_attack,
        intensity,
        asset_criticality=asset_criticality,
    )
    rec = recommend(
        pred.attack_type,
        risk["severity"],
        confidence=confidence,
        traffic_intensity=intensity,
        certainty=pred.certainty,
        is_attack=pred.is_attack,
    )
    return {
        "is_attack": pred.is_attack,
        "attack_type": pred.attack_type,
        "confidence": confidence,
        "binary_proba_attack": pred.binary_proba_attack,
        "class_probabilities": pred.class_probabilities,
        "risk_score": risk["risk_score"],
        "severity": risk["severity"],
        "risk_factors": risk.get("factors"),
        "recommendation": rec,
        "certainty": pred.certainty,
        "threshold": pred.threshold,
    }


def run_prediction(
    features: dict[str, float],
    db: Session | None = None,
    persist: bool = True,
    allow_missing_features: bool = False,
    asset_criticality: float | None = None,
) -> dict[str, Any]:
    predictor = get_predictor()
    if predictor is None:
        raise RuntimeError("Models not trained. Run scripts/01_prepare_data.py and scripts/02_train_models.py")

    pred: PredictionResult = predictor.predict_row(features, allow_missing=allow_missing_features)
    payload = _enrich_prediction(pred, features, asset_criticality=asset_criticality)

    incident_id = None
    if persist and db is not None and pred.is_attack:
        incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
        row = Incident(
            incident_code=incident_id,
            attack_type=pred.attack_type,
            is_attack=1,
            confidence=payload["confidence"],
            risk_score=payload["risk_score"],
            severity=payload["severity"],
            recommendation=payload["recommendation"]["primary"],
            explanation="",
            status="Detected",
            asset_criticality=asset_criticality,
        )
        db.add(row)
        db.commit()

    payload["incident_id"] = incident_id
    return payload


def run_prediction_batch(
    rows: list[dict[str, float]],
    db: Session | None = None,
    persist: bool = False,
    allow_missing_features: bool = False,
    asset_criticality: float | None = None,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("Batch must contain at least one feature vector")
    if len(rows) > 500:
        raise ValueError("Batch size limited to 500 flows per request")

    results: list[dict[str, Any]] = []
    for i, features in enumerate(rows):
        item = run_prediction(
            features,
            db=db,
            persist=persist,
            allow_missing_features=allow_missing_features,
            asset_criticality=asset_criticality,
        )
        item["flow_index"] = i
        results.append(item)

    attacks = [r for r in results if r["is_attack"]]
    by_type: dict[str, int] = {}
    for r in attacks:
        by_type[r["attack_type"]] = by_type.get(r["attack_type"], 0) + 1
    highest = max(results, key=lambda r: r["risk_score"]) if results else None

    return {
        "total_flows": len(results),
        "attack_flows": len(attacks),
        "benign_flows": len(results) - len(attacks),
        "attack_percentage": round(100.0 * len(attacks) / len(results), 2),
        "by_attack_type": by_type,
        "highest_risk": {
            "flow_index": highest["flow_index"],
            "attack_type": highest["attack_type"],
            "risk_score": highest["risk_score"],
            "severity": highest["severity"],
        }
        if highest
        else None,
        "results": results,
    }


def run_explain(
    features: dict[str, float],
    top_k: int = 10,
    method: str = "shap",
    allow_missing_features: bool = False,
) -> dict[str, Any]:
    cfg = load_config()
    xai_cfg = cfg.get("xai", {})
    method = (method or xai_cfg.get("default_method", "shap")).lower().strip()
    top_k = int(top_k or xai_cfg.get("top_k", 10))
    if method == "lime":
        explainer = get_lime_explainer()
        if explainer is None:
            raise RuntimeError("Explainability engine unavailable — train models first.")
        return explainer.explain(features, top_k=top_k)
    explainer = get_explainer()
    if explainer is None:
        raise RuntimeError("Explainability engine unavailable — train models first.")
    return explainer.explain(features, top_k=top_k, allow_missing=allow_missing_features)


def _incident_dict(row: Incident) -> dict[str, Any]:
    return {
        "incident_id": row.incident_code,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "attack_type": row.attack_type,
        "confidence": row.confidence,
        "risk_score": row.risk_score,
        "severity": row.severity,
        "recommendation": row.recommendation,
        "status": row.status,
        "analyst_notes": getattr(row, "analyst_notes", None),
        "defense_action": getattr(row, "defense_action", None),
        "resolved_at": row.resolved_at.isoformat() if getattr(row, "resolved_at", None) else None,
        "asset_criticality": getattr(row, "asset_criticality", None),
        "allowed_next_statuses": sorted(INCIDENT_TRANSITIONS.get(row.status or "Detected", set())),
    }


def get_incident(db: Session, incident_id: str) -> dict[str, Any] | None:
    row = db.query(Incident).filter(Incident.incident_code == incident_id).first()
    if not row:
        return None
    return _incident_dict(row)


def update_incident_status(
    db: Session,
    incident_id: str,
    status: str,
    *,
    analyst_notes: str | None = None,
    defense_action: str | None = None,
) -> dict[str, Any]:
    row = db.query(Incident).filter(Incident.incident_code == incident_id).first()
    if not row:
        raise KeyError(f"Unknown incident: {incident_id}")
    current = row.status or "Detected"
    target = status.strip()
    allowed = INCIDENT_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(f"Invalid transition {current} → {target}. Allowed: {sorted(allowed)}")
    row.status = target
    if analyst_notes is not None:
        row.analyst_notes = analyst_notes
    if defense_action is not None:
        row.defense_action = defense_action
    if target in {"Resolved", "FalsePositive"}:
        row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return _incident_dict(row)


def start_simulation_from_incident(db: Session, incident_id: str) -> dict[str, Any]:
    from simulation.engine.core import simulation_engine

    incident = get_incident(db, incident_id)
    if incident is None:
        raise KeyError(f"Unknown incident: {incident_id}")
    session = simulation_engine.start(
        attack_type=incident["attack_type"],
        confidence=float(incident["confidence"] or 0.9),
        incident_id=incident_id,
        risk_score=float(incident["risk_score"] or 0),
        severity=incident["severity"],
        recommendation={
            "primary": incident["recommendation"],
            "actions": [incident["recommendation"]],
            "advisory_only": True,
        },
    )
    row = db.query(Incident).filter(Incident.incident_code == incident_id).first()
    if row and (row.status or "Detected") in INCIDENT_TRANSITIONS and "Simulating" in INCIDENT_TRANSITIONS.get(
        row.status or "Detected", set()
    ):
        row.status = "Simulating"
        db.commit()
    elif row:
        # Allow force-set when already simulating / from Detected path
        if row.status != "Simulating":
            try:
                update_incident_status(db, incident_id, "Simulating")
            except ValueError:
                row.status = "Simulating"
                db.commit()
    return session


def list_incidents(db: Session, limit: int = 50) -> list[dict[str, Any]]:
    rows = db.query(Incident).order_by(Incident.created_at.desc()).limit(limit).all()
    return [_incident_dict(r) for r in rows]


def analytics_summary(db: Session) -> dict[str, Any]:
    rows = db.query(Incident).all()
    by_sev: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for r in rows:
        by_sev[r.severity or "UNKNOWN"] = by_sev.get(r.severity or "UNKNOWN", 0) + 1
        by_type[r.attack_type or "UNKNOWN"] = by_type.get(r.attack_type or "UNKNOWN", 0) + 1
        by_status[r.status or "UNKNOWN"] = by_status.get(r.status or "UNKNOWN", 0) + 1
    return {
        "total_incidents": len(rows),
        "by_severity": by_sev,
        "by_attack_type": by_type,
        "by_status": by_status,
    }


def sample_feature_template() -> dict[str, float]:
    predictor = get_predictor()
    if predictor is None:
        return {}
    return {name: 0.0 for name in predictor.bundle.feature_names}


def load_demo_flow(attack_hint: str | None = None) -> dict[str, Any]:
    """Load one processed test row for demos."""
    from ml.preprocessing.dataset import load_processed

    try:
        test = load_processed("test")
    except FileNotFoundError:
        return {"features": sample_feature_template(), "label": None}
    if attack_hint and attack_hint != "BENIGN":
        subset = test[test["Label"] == attack_hint]
        if subset.empty:
            subset = test[test["is_attack"] == 1]
    elif attack_hint == "BENIGN":
        subset = test[test["is_attack"] == 0]
    else:
        subset = test[test["is_attack"] == 1]
    if subset.empty:
        subset = test
    row = subset.sample(1, random_state=None).iloc[0]
    features = {c: float(row[c]) for c in predictor.bundle.feature_names} if (predictor := get_predictor()) else {}
    return {"features": features, "label": str(row["Label"])}


def load_demo_flows(attack_hint: str | None = None, n: int = 10) -> dict[str, Any]:
    """Load multiple processed test rows for batch demos."""
    from ml.preprocessing.dataset import load_processed

    n = max(1, min(100, int(n)))
    try:
        test = load_processed("test")
    except FileNotFoundError:
        return {"items": [], "count": 0}
    if attack_hint and attack_hint != "BENIGN":
        subset = test[test["Label"] == attack_hint]
        if subset.empty:
            subset = test[test["is_attack"] == 1]
    elif attack_hint == "BENIGN":
        subset = test[test["is_attack"] == 0]
    else:
        subset = test
    if subset.empty:
        return {"items": [], "count": 0}
    sample = subset.sample(min(n, len(subset)), random_state=None)
    predictor = get_predictor()
    if predictor is None:
        return {"items": [], "count": 0}
    items = []
    for _, row in sample.iterrows():
        features = {c: float(row[c]) for c in predictor.bundle.feature_names}
        items.append({"features": features, "label": str(row["Label"])})
    return {"items": items, "count": len(items)}


def parse_flows_csv(content: str | bytes, *, max_rows: int = 500) -> list[dict[str, float]]:
    """Parse a CSV of flow features into dict rows (schema-validated later by predictor)."""
    import io

    import pandas as pd

    text = content.decode("utf-8-sig") if isinstance(content, (bytes, bytearray)) else content
    df = pd.read_csv(io.StringIO(text))
    if df.empty:
        raise ValueError("CSV contains no rows")
    if len(df) > max_rows:
        raise ValueError(f"CSV limited to {max_rows} rows (got {len(df)})")
    # Drop non-feature helper columns if present
    drop = [c for c in ("Label", "is_attack", "Flow ID", "Timestamp") if c in df.columns]
    df = df.drop(columns=drop, errors="ignore")
    rows: list[dict[str, float]] = []
    for _, row in df.iterrows():
        features: dict[str, float] = {}
        for k, v in row.items():
            try:
                features[str(k).strip()] = float(v)
            except (TypeError, ValueError):
                continue
        if features:
            rows.append(features)
    if not rows:
        raise ValueError("No numeric feature rows found in CSV")
    return rows


def export_incidents_csv(db: Session, limit: int = 1000) -> str:
    import csv
    import io

    items = list_incidents(db, limit=limit)
    buf = io.StringIO()
    fields = [
        "incident_id",
        "created_at",
        "attack_type",
        "confidence",
        "risk_score",
        "severity",
        "recommendation",
        "status",
        "defense_action",
        "resolved_at",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for item in items:
        writer.writerow({k: item.get(k) for k in fields})
    return buf.getvalue()


def export_analytics_payload(db: Session) -> dict[str, Any]:
    return {
        "analytics": analytics_summary(db),
        "incidents": list_incidents(db, limit=1000),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "note": "Decision-support export from Aegis IDS prototype — not live packet capture.",
    }
