"""Application services wrapping ML + security engines."""
from __future__ import annotations

import json
import uuid
from functools import lru_cache
from pathlib import Path
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


def run_prediction(
    features: dict[str, float],
    db: Session | None = None,
    persist: bool = True,
    allow_missing_features: bool = False,
) -> dict[str, Any]:
    predictor = get_predictor()
    if predictor is None:
        raise RuntimeError("Models not trained. Run scripts/01_prepare_data.py and scripts/02_train_models.py")

    pred: PredictionResult = predictor.predict_row(features, allow_missing=allow_missing_features)
    confidence = pred.multiclass_confidence if pred.is_attack else pred.binary_confidence
    intensity = None
    for key in ("Flow Packets/s", "Flow Bytes/s"):
        if key in features:
            intensity = min(1.0, abs(float(features[key])) / 1e5)
            break
    risk = compute_risk(pred.attack_type, confidence, pred.is_attack, intensity)
    rec = recommend(pred.attack_type, risk["severity"])

    incident_id = None
    if persist and db is not None and pred.is_attack:
        incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
        row = Incident(
            incident_code=incident_id,
            attack_type=pred.attack_type,
            is_attack=1,
            confidence=confidence,
            risk_score=risk["risk_score"],
            severity=risk["severity"],
            recommendation=rec["primary"],
            explanation="",
            status="Detected",
        )
        db.add(row)
        db.commit()

    return {
        "is_attack": pred.is_attack,
        "attack_type": pred.attack_type,
        "confidence": confidence,
        "binary_proba_attack": pred.binary_proba_attack,
        "class_probabilities": pred.class_probabilities,
        "risk_score": risk["risk_score"],
        "severity": risk["severity"],
        "recommendation": rec,
        "incident_id": incident_id,
        "certainty": pred.certainty,
        "threshold": pred.threshold,
    }


def run_explain(
    features: dict[str, float],
    top_k: int = 10,
    method: str = "shap",
    allow_missing_features: bool = False,
) -> dict[str, Any]:
    method = (method or "shap").lower().strip()
    if method == "lime":
        explainer = get_lime_explainer()
        if explainer is None:
            raise RuntimeError("Explainability engine unavailable — train models first.")
        return explainer.explain(features, top_k=top_k)
    explainer = get_explainer()
    if explainer is None:
        raise RuntimeError("Explainability engine unavailable — train models first.")
    return explainer.explain(features, top_k=top_k, allow_missing=allow_missing_features)


def get_incident(db: Session, incident_id: str) -> dict[str, Any] | None:
    row = db.query(Incident).filter(Incident.incident_code == incident_id).first()
    if not row:
        return None
    return {
        "incident_id": row.incident_code,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "attack_type": row.attack_type,
        "confidence": row.confidence,
        "risk_score": row.risk_score,
        "severity": row.severity,
        "recommendation": row.recommendation,
        "status": row.status,
    }


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
        recommendation={"primary": incident["recommendation"], "actions": [incident["recommendation"]], "advisory_only": True},
    )
    row = db.query(Incident).filter(Incident.incident_code == incident_id).first()
    if row:
        row.status = "Simulating"
        db.commit()
    return session


def list_incidents(db: Session, limit: int = 50) -> list[dict[str, Any]]:
    rows = db.query(Incident).order_by(Incident.created_at.desc()).limit(limit).all()
    return [
        {
            "incident_id": r.incident_code,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "attack_type": r.attack_type,
            "confidence": r.confidence,
            "risk_score": r.risk_score,
            "severity": r.severity,
            "recommendation": r.recommendation,
            "status": r.status,
        }
        for r in rows
    ]


def analytics_summary(db: Session) -> dict[str, Any]:
    rows = db.query(Incident).all()
    by_sev: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for r in rows:
        by_sev[r.severity or "UNKNOWN"] = by_sev.get(r.severity or "UNKNOWN", 0) + 1
        by_type[r.attack_type or "UNKNOWN"] = by_type.get(r.attack_type or "UNKNOWN", 0) + 1
    return {
        "total_incidents": len(rows),
        "by_severity": by_sev,
        "by_attack_type": by_type,
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
