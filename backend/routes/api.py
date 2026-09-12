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
    SimulationStartRequest,
)
from backend.services import pipeline as svc
from database.db import get_db
from ids_config import load_config
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
        result = svc.run_prediction(body.features, db=db, persist=body.persist)
        return PredictResponse(**result)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/explain")
def explain(body: ExplainRequest):
    try:
        return svc.run_explain(body.features, top_k=body.top_k, method=body.method)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/risk")
def risk(body: RiskRequest):
    return compute_risk(body.attack_type, body.confidence, body.is_attack, body.traffic_intensity)


@router.post("/recommendation")
def recommendation(body: RecommendationRequest):
    return recommend(body.attack_type, body.severity)


@router.post("/simulation/start")
def simulation_start(body: SimulationStartRequest):
    return simulation_engine.start(body.attack_type, body.confidence)


@router.post("/simulation/advance")
def simulation_advance(body: SimulationAdvanceRequest):
    try:
        return simulation_engine.advance(body.session_id, body.action)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/simulation/{session_id}")
def simulation_get(session_id: str):
    try:
        return simulation_engine.get(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/incidents")
def incidents(limit: int = 50, db: Session = Depends(get_db)):
    return {"items": svc.list_incidents(db, limit=limit)}


@router.get("/analytics")
def analytics(db: Session = Depends(get_db)):
    return svc.analytics_summary(db)


@router.get("/features/template")
def feature_template():
    return {"features": svc.sample_feature_template()}


@router.get("/demo/flow")
def demo_flow(attack_type: str | None = None):
    return svc.load_demo_flow(attack_type)
