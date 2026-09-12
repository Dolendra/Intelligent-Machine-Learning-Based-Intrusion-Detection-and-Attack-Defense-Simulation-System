"""FastAPI route handlers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.schemas.api import (
    ExplainRequest,
    HealthResponse,
    PredictRequest,
    PredictResponse,
    RecommendationRequest,
    RiskRequest,
    SimulationAdvanceRequest,
    SimulationFromPredictionRequest,
    SimulationStartRequest,
)
from backend.services import pipeline as svc
from database.db import get_db
from ids_config import load_config
from ml.prediction.predictor import FeatureValidationError
from security.recommendations.engine import recommend
from security.risk.engine import compute_risk
from simulation.engine.core import simulation_engine

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    cfg = load_config()
    return HealthResponse(
        status="ok",
        models_loaded=svc.models_ready(),
        version=cfg["project"]["version"],
    )


@router.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest, db: Session = Depends(get_db)):
    try:
        result = svc.run_prediction(
            body.features,
            db=db,
            persist=body.persist,
            allow_missing_features=body.allow_missing_features,
        )
        return PredictResponse(**result)
    except FeatureValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_FEATURES", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "MODEL_NOT_READY", "message": str(exc)}) from exc


@router.post("/explain")
def explain(body: ExplainRequest):
    try:
        return svc.run_explain(
            body.features,
            top_k=body.top_k,
            method=body.method,
            allow_missing_features=body.allow_missing_features,
        )
    except FeatureValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_FEATURES", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "MODEL_NOT_READY", "message": str(exc)}) from exc


@router.post("/risk")
def risk(body: RiskRequest):
    return compute_risk(body.attack_type, body.confidence, body.is_attack, body.traffic_intensity)


@router.post("/recommendation")
def recommendation(body: RecommendationRequest):
    return recommend(body.attack_type, body.severity)


@router.post("/simulation/start")
def simulation_start(body: SimulationStartRequest):
    return simulation_engine.start(body.attack_type, body.confidence, incident_id=body.incident_id)


@router.post("/simulation/from-prediction")
def simulation_from_prediction(body: SimulationFromPredictionRequest, db: Session = Depends(get_db)):
    try:
        if body.incident_id:
            return svc.start_simulation_from_incident(db, body.incident_id)
        if not body.attack_type:
            raise HTTPException(
                status_code=422,
                detail={"code": "MISSING_ATTACK", "message": "Provide incident_id or attack_type"},
            )
        return simulation_engine.start(
            attack_type=body.attack_type,
            confidence=float(body.confidence or 0.9),
            risk_score=body.risk_score,
            severity=body.severity,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc


@router.post("/simulation/advance")
def simulation_advance(body: SimulationAdvanceRequest):
    try:
        return simulation_engine.advance(body.session_id, body.action)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc


@router.get("/simulation/{session_id}")
def simulation_get(session_id: str):
    try:
        return simulation_engine.get(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc


@router.get("/incidents")
def incidents(limit: int = 50, db: Session = Depends(get_db)):
    return {"items": svc.list_incidents(db, limit=limit)}


@router.get("/incidents/{incident_id}")
def incident_detail(incident_id: str, db: Session = Depends(get_db)):
    item = svc.get_incident(db, incident_id)
    if item is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Unknown incident"})
    return item


@router.post("/incidents/{incident_id}/simulate")
def incident_simulate(incident_id: str, db: Session = Depends(get_db)):
    try:
        return svc.start_simulation_from_incident(db, incident_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc


@router.get("/analytics")
def analytics(db: Session = Depends(get_db)):
    return svc.analytics_summary(db)


@router.get("/features/template")
def feature_template():
    return {"features": svc.sample_feature_template()}


@router.get("/demo/flow")
def demo_flow(attack_type: str | None = None):
    return svc.load_demo_flow(attack_type)
