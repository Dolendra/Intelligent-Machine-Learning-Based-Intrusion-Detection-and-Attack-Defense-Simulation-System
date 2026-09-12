"""FastAPI route handlers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.schemas.api import (
    BatchPredictRequest,
    ExplainRequest,
    HealthResponse,
    IncidentUpdateRequest,
    PredictRequest,
    PredictResponse,
    RecommendationRequest,
    RiskRequest,
    SimulationAdvanceRequest,
    SimulationFromPredictionRequest,
    SimulationStartRequest,
)
from backend.services import pipeline as svc
from backend.services.events import event_hub
from backend.services.report_pdf import build_analytics_pdf
from database.db import SessionLocal, get_db
from ids_config import load_config
from ml.prediction.predictor import FeatureValidationError
from security.recommendations.engine import recommend
from security.risk.engine import compute_risk
from simulation.engine.core import simulation_engine

router = APIRouter()


def _demo_allow_missing(requested: bool) -> bool:
    """Missing features are demo-only; never honor the flag outside DEMO_MODE."""
    import os

    demo = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"}
    return bool(requested) and demo


@router.get("/health", response_model=HealthResponse)
def health():
    cfg = load_config()
    return HealthResponse(
        status="ok",
        models_loaded=svc.models_ready(),
        version=cfg["project"]["version"],
    )


@router.get("/ready")
def ready():
    """Readiness probe — 503 until model artifacts are loadable."""
    cfg = load_config()
    if not svc.models_ready():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "MODEL_NOT_READY",
                "message": "Model artifacts not loaded",
                "models_loaded": False,
                "version": cfg["project"]["version"],
            },
        )
    return {
        "status": "ready",
        "models_loaded": True,
        "version": cfg["project"]["version"],
    }


@router.get("/models")
def models():
    return svc.model_info()


@router.get("/models/health")
def models_health():
    return svc.model_health()


@router.get("/models/comparison")
def models_comparison():
    try:
        return svc.training_comparison()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "NO_REPORT", "message": str(exc)}) from exc


@router.get("/models/shap/global")
def models_shap_global(top_k: int = 15, refresh: bool = False):
    try:
        return svc.global_shap_summary(top_k=top_k, refresh=refresh)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "MODEL_NOT_READY", "message": str(exc)}) from exc


@router.get("/experiments")
def experiments():
    return svc.experiment_index()


@router.get("/drift")
def drift():
    return svc.drift_status()


@router.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest, db: Session = Depends(get_db)):
    # Strict by default; allow_missing only when DEMO_MODE explicitly enables demos
    allow_missing = _demo_allow_missing(body.allow_missing_features)
    try:
        result = svc.run_prediction(
            body.features,
            db=db,
            persist=body.persist,
            allow_missing_features=allow_missing,
            asset_criticality=body.asset_criticality,
            source_ref=body.source_ref,
            asset_id=body.asset_id,
        )
        return PredictResponse(**result)
    except FeatureValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_FEATURES", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "MODEL_NOT_READY", "message": str(exc)}) from exc


@router.post("/predict/batch")
def predict_batch(body: BatchPredictRequest, db: Session = Depends(get_db)):
    allow_missing = _demo_allow_missing(body.allow_missing_features)
    try:
        return svc.run_prediction_batch(
            body.flows,
            db=db,
            persist=body.persist,
            allow_missing_features=allow_missing,
            asset_criticality=body.asset_criticality,
        )
    except FeatureValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_FEATURES", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_BATCH", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "MODEL_NOT_READY", "message": str(exc)}) from exc


@router.post("/predict/batch/csv")
async def predict_batch_csv(
    file: UploadFile = File(...),
    persist: bool = False,
    allow_missing_features: bool = False,
    db: Session = Depends(get_db),
):
    raw = await file.read()
    allow_missing = _demo_allow_missing(allow_missing_features)
    try:
        flows = svc.parse_flows_csv(raw)
        return svc.run_prediction_batch(
            flows,
            db=db,
            persist=persist,
            allow_missing_features=allow_missing,
        )
    except FeatureValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_FEATURES", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_CSV", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "MODEL_NOT_READY", "message": str(exc)}) from exc


@router.post("/explain")
def explain(body: ExplainRequest):
    allow_missing = _demo_allow_missing(body.allow_missing_features)
    try:
        return svc.run_explain(
            body.features,
            top_k=body.top_k,
            method=body.method,
            allow_missing_features=allow_missing,
        )
    except FeatureValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_FEATURES", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "MODEL_NOT_READY", "message": str(exc)}) from exc


@router.post("/explain/counterfactual")
def explain_counterfactual(body: ExplainRequest):
    allow_missing = _demo_allow_missing(body.allow_missing_features)
    try:
        return svc.run_counterfactual(
            body.features,
            allow_missing_features=allow_missing,
            max_edits=min(8, max(1, body.top_k)),
        )
    except FeatureValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_FEATURES", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "MODEL_NOT_READY", "message": str(exc)}) from exc


@router.post("/risk")
def risk(body: RiskRequest):
    return compute_risk(
        body.attack_type,
        body.confidence,
        body.is_attack,
        body.traffic_intensity,
        asset_criticality=body.asset_criticality,
    )


@router.post("/recommendation")
def recommendation(body: RecommendationRequest):
    return recommend(
        body.attack_type,
        body.severity,
        confidence=body.confidence,
        traffic_intensity=body.traffic_intensity,
        certainty=body.certainty,
        is_attack=body.is_attack,
    )


@router.post("/simulation/start")
def simulation_start(body: SimulationStartRequest):
    return simulation_engine.start(
        body.attack_type,
        body.confidence,
        incident_id=body.incident_id,
        risk_score=body.risk_score,
        severity=body.severity,
        traffic_intensity=body.traffic_intensity,
        asset_criticality=body.asset_criticality,
    )


@router.get("/simulation")
def simulation_list(limit: int = 20):
    return {"items": simulation_engine.list_recent(limit=limit)}


@router.get("/assets")
def assets_list():
    from security.assets import list_assets

    return {"items": list_assets()}


@router.get("/campaigns")
def campaigns_list(limit: int = 30, db: Session = Depends(get_db)):
    from security.correlation import list_campaigns

    return {"items": list_campaigns(db, limit=limit)}


@router.get("/campaigns/{campaign_id}")
def campaign_detail(campaign_id: str, db: Session = Depends(get_db)):
    from security.correlation import campaign_summary

    summary = campaign_summary(db, campaign_id)
    if summary["incident_count"] == 0:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Unknown campaign"})
    return summary


@router.post("/campaigns/{campaign_id}/simulate")
def campaign_simulate(campaign_id: str, db: Session = Depends(get_db)):
    from security.correlation import campaign_summary

    summary = campaign_summary(db, campaign_id)
    if summary["incident_count"] == 0:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Unknown campaign"})
    return simulation_engine.start_campaign(
        campaign_id=campaign_id,
        progression=list(summary.get("progression") or summary.get("attack_types") or []),
    )


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


@router.get("/incidents/{incident_id}/trace")
def incident_trace(incident_id: str, db: Session = Depends(get_db)):
    from backend.services.decision_trace import build_trace_from_incident

    trace = build_trace_from_incident(db, incident_id)
    if trace is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Unknown incident"})
    return trace


@router.patch("/incidents/{incident_id}")
def incident_update(incident_id: str, body: IncidentUpdateRequest, db: Session = Depends(get_db)):
    try:
        return svc.update_incident_status(
            db,
            incident_id,
            body.status,
            analyst_notes=body.analyst_notes,
            defense_action=body.defense_action,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_TRANSITION", "message": str(exc)}) from exc


@router.post("/incidents/{incident_id}/simulate")
def incident_simulate(incident_id: str, db: Session = Depends(get_db)):
    try:
        return svc.start_simulation_from_incident(db, incident_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc


@router.get("/analytics")
def analytics(db: Session = Depends(get_db)):
    return svc.analytics_summary(db)


@router.get("/export/incidents.json")
def export_incidents_json(db: Session = Depends(get_db)):
    return svc.export_analytics_payload(db)


@router.get("/export/incidents.csv")
def export_incidents_csv(db: Session = Depends(get_db)):
    csv_text = svc.export_incidents_csv(db)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aegis_incidents.csv"},
    )


@router.get("/export/analytics.json")
def export_analytics_json(db: Session = Depends(get_db)):
    return svc.analytics_summary(db)


@router.get("/export/report.pdf")
def export_report_pdf(db: Session = Depends(get_db)):
    payload = svc.export_analytics_payload(db)
    pdf_bytes = build_analytics_pdf(payload)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=aegis_analytics_report.pdf"},
    )


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    """Push analytics snapshots + incident notifications for dashboard refresh."""
    import asyncio

    await event_hub.connect(websocket)
    try:
        await websocket.send_json({"type": "connected", "message": "Aegis event stream"})
        while True:
            db = SessionLocal()
            try:
                snap = svc.analytics_summary(db)
                recent = svc.list_incidents(db, limit=8)
            finally:
                db.close()
            await websocket.send_json(
                {
                    "type": "analytics",
                    "analytics": snap,
                    "incidents": recent,
                }
            )
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=4.0)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        await event_hub.disconnect(websocket)
    except Exception:
        await event_hub.disconnect(websocket)


@router.get("/features/template")
def feature_template():
    return {"features": svc.sample_feature_template()}


@router.get("/demo/flow")
def demo_flow(attack_type: str | None = None):
    return svc.load_demo_flow(attack_type)


@router.get("/demo/flows")
def demo_flows(attack_type: str | None = None, n: int = 10):
    return svc.load_demo_flows(attack_type, n=n)
