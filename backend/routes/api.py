"""FastAPI route handlers."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.schemas.api import (
    BatchPredictRequest,
    ControlledResponsePlanRequest,
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


@router.get("/security/status")
def security_status():
    """Stage-2 Phase F: auth/RBAC + observability + cyber-range validation honesty (no secrets)."""
    import os

    from backend.middleware.security_headers import security_headers_summary
    from database.url import database_info
    from security.rbac import rbac_summary

    cfg = load_config()
    auth = cfg.get("api", {}).get("auth", {}) or {}
    rl = cfg.get("api", {}).get("rate_limit", {}) or {}
    key_configured = bool(os.getenv("AEGIS_API_KEY") or auth.get("api_key"))
    default_rl_paths = [
        "/api/predict",
        "/api/ingest",
        "/api/explain",
        "/api/recommendation",
        "/api/response",
        "/api/simulation",
    ]
    return {
        "stage": "2-phase-f",
        "auth": {
            "enabled": bool(auth.get("enabled", False)),
            "api_key_configured": key_configured,
            "header": auth.get("header", "X-API-Key"),
            "role_header": auth.get("role_header", "X-Aegis-Role"),
            "default_role": auth.get("default_role", "analyst"),
            "enforce_rbac": bool(auth.get("enforce_rbac", True)),
        },
        "rate_limit": {
            "enabled": bool(rl.get("enabled", False)),
            "requests_per_window": rl.get("requests_per_window"),
            "window_seconds": rl.get("window_seconds"),
            "paths": list(rl.get("paths") or default_rl_paths),
        },
        "security_headers": security_headers_summary(),
        "observability": {
            "metrics_endpoint": "/api/metrics",
            "request_logging": True,
            "prometheus": False,
            "opentelemetry": False,
            "load_smoke_script": "scripts/26_api_load_smoke.py",
        },
        "cyber_range_validation": {
            "live_cyber_range": False,
            "live_mitigation": False,
            "efficacy_are_assumptions": True,
            "mode": "controlled_visualization",
            "script": "scripts/27_cyber_range_sim_validate.py",
            "module": "simulation.validation",
        },
        "controlled_response": {
            "live_mitigation": False,
            "simulation": True,
            "advisory_only": True,
            "plan_endpoint": "/api/response/plan",
        },
        "database": database_info(),
        "rbac": rbac_summary(),
        "notes": [
            "Auth and rate limiting remain disabled by default for the research/demo baseline.",
            "Enable api.auth.enabled and set AEGIS_API_KEY for Stage-2 hardening.",
            "Enable api.rate_limit.enabled to protect predict/ingest/response surfaces.",
            "Controlled response is advisory + simulation only — no live network mitigation.",
            "/api/metrics is in-process only (resets on restart); not a multi-node SRE stack.",
            "Cyber-range validation checks the simulation state machine — not a physical range or real defense efficacy.",
            "PostgreSQL is optional via IDS_DB_URL; SQLite remains the default.",
        ],
    }


@router.get("/metrics")
def process_metrics_endpoint():
    """Stage-2 Phase E: in-process request counters and latency samples (not Prometheus)."""
    from backend.middleware.metrics_mw import process_metrics

    snap = process_metrics.snapshot()
    try:
        from ingestion.queue import ingest_queue

        snap["ingest_queue"] = ingest_queue.status().get("metrics")
    except Exception:  # noqa: BLE001
        snap["ingest_queue"] = None
    return snap


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


@router.get("/ingest/capabilities")
def ingest_capabilities():
    """Stage-2 Phase A: schema version + extractor status (does not claim live capture)."""
    from ingestion.pipeline import ingestion_capabilities

    return ingestion_capabilities()


@router.post("/ingest/flows/csv")
async def ingest_flows_csv(
    file: UploadFile = File(...),
    predict: bool = False,
    persist: bool = False,
    db: Session = Depends(get_db),
):
    """Offline MachineLearningCVE-compatible CSV → schema-validated flows (optional predict)."""
    from ingestion.pipeline import ingest_flows_csv as _ingest

    raw = await file.read()
    result = _ingest(raw, fill_missing=False, max_rows=500)
    payload = result.as_dict()
    if not result.ok:
        raise HTTPException(
            status_code=422,
            detail={
                "code": result.detail.get("code", "INGEST_FAILED"),
                "message": result.validation.get("message") or result.detail.get("message") or "ingest failed",
                "validation": result.validation,
                "schema_version": (result.schema or {}).get("schema_version"),
            },
        )
    if predict:
        try:
            batch = svc.run_prediction_batch(result.flows, db=db, persist=persist, allow_missing_features=False)
            payload["prediction"] = batch
        except FeatureValidationError as exc:
            raise HTTPException(status_code=422, detail={"code": "INVALID_FEATURES", "message": str(exc)}) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail={"code": "MODEL_NOT_READY", "message": str(exc)}) from exc
    # Avoid huge payloads by default when only validating
    if not predict:
        payload["flows"] = payload["flows"][:5]
        payload["flows_truncated"] = True
    return payload


@router.post("/ingest/pcap")
async def ingest_pcap(
    request: Request,
    file: UploadFile = File(...),
    predict: bool = False,
    persist: bool = False,
    db: Session = Depends(get_db),
):
    """Offline PCAP upload — validates file, then cicflowmeter when installed; otherwise 501."""
    import tempfile
    from pathlib import Path

    from ingestion.audit import audit_ingest_event
    from ingestion.pcap_validation import validate_pcap_upload
    from ingestion.pipeline import ingest_pcap as _ingest_pcap

    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
    suffix = Path(file.filename or "capture.pcap").suffix or ".pcap"
    raw = await file.read()
    check = validate_pcap_upload(filename=file.filename, content=raw)
    if not check.ok:
        audit_ingest_event(
            event="pcap_rejected",
            source="pcap",
            request_id=request_id,
            filename=file.filename,
            sha256=check.sha256,
            size_bytes=check.size_bytes,
            code=check.code,
            predict=predict,
        )
        status = 413 if check.code == "PCAP_TOO_LARGE" else 422
        raise HTTPException(
            status_code=status,
            detail={
                "code": check.code,
                "message": check.message,
                "validation": check.as_dict(),
            },
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)
    try:
        result = _ingest_pcap(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if not result.ok:
        code = result.detail.get("code", "PCAP_NOT_AVAILABLE")
        status = 501 if code in {"PCAP_EXTRACTOR_NOT_CONFIGURED", "PCAP_EXTRACTOR_NOT_WIRED"} else 422
        audit_ingest_event(
            event="pcap_extract_failed",
            source="pcap",
            request_id=request_id,
            filename=file.filename,
            sha256=check.sha256,
            size_bytes=check.size_bytes,
            code=code,
            schema_version=(result.schema or {}).get("schema_version"),
            predict=predict,
        )
        raise HTTPException(
            status_code=status,
            detail={
                "code": code,
                "message": result.detail.get("message", "PCAP extraction failed"),
                "capabilities": result.detail,
                "schema_version": (result.schema or {}).get("schema_version"),
                "validation": result.validation,
                "upload": check.as_dict(),
            },
        )

    payload = result.as_dict()
    payload["upload"] = check.as_dict()
    audit_ingest_event(
        event="pcap_accepted",
        source="pcap",
        request_id=request_id,
        filename=file.filename,
        sha256=check.sha256,
        size_bytes=check.size_bytes,
        code="OK",
        flow_count=len(result.flows),
        schema_version=(result.schema or {}).get("schema_version"),
        predict=predict,
    )
    if predict:
        try:
            batch = svc.run_prediction_batch(result.flows, db=db, persist=persist, allow_missing_features=False)
            payload["prediction"] = batch
        except FeatureValidationError as exc:
            raise HTTPException(status_code=422, detail={"code": "INVALID_FEATURES", "message": str(exc)}) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail={"code": "MODEL_NOT_READY", "message": str(exc)}) from exc
    if not predict:
        payload["flows"] = payload["flows"][:5]
        payload["flows_truncated"] = True
    return payload


def _ensure_ingest_queue_worker() -> None:
    """Lazy-start the shared ingest→detect worker (CSV and PCAP use the same queue)."""
    from ingestion.queue import ingest_queue

    if ingest_queue.status().get("worker_alive"):
        return
    from backend.services import pipeline as _svc
    from database.db import SessionLocal

    def _predict_batch(flows: list[dict[str, float]]) -> dict:
        db = SessionLocal()
        try:
            return _svc.run_prediction_batch(flows, db=db, persist=False, allow_missing_features=False)
        finally:
            db.close()

    ingest_queue.set_predict_fn(_predict_batch)
    ingest_queue.start()


@router.get("/ingest/queue")
def ingest_queue_status():
    """Stage-2 Phase B: in-process queue depth + latency metrics."""
    from ingestion.queue import ingest_queue

    return ingest_queue.status()


@router.post("/ingest/queue/submit")
async def ingest_queue_submit(
    file: UploadFile = File(...),
):
    """Enqueue schema-validated CSV flows for async detection (in-process worker)."""
    from ingestion.pipeline import ingest_flows_csv as _ingest
    from ingestion.queue import ingest_queue

    _ensure_ingest_queue_worker()

    raw = await file.read()
    result = _ingest(raw, fill_missing=False, max_rows=500)
    if not result.ok:
        raise HTTPException(
            status_code=422,
            detail={
                "code": result.detail.get("code", "INGEST_FAILED"),
                "message": result.validation.get("message") or "ingest failed",
                "validation": result.validation,
            },
        )
    try:
        job = ingest_queue.submit(result.flows, source="csv_upload")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "QUEUE_FULL", "message": str(exc)}) from exc
    return {"ok": True, "job": job.as_dict()}


@router.post("/ingest/queue/submit-pcap")
async def ingest_queue_submit_pcap(
    request: Request,
    file: UploadFile = File(...),
):
    """Validate PCAP → cicflowmeter → enqueue flows on the *same* detect worker as CSV.

    Does not invent a second prediction pipeline. Returns 501 when cicflowmeter is absent.
    """
    import tempfile
    from pathlib import Path

    from ingestion.audit import audit_ingest_event
    from ingestion.pcap_validation import validate_pcap_upload
    from ingestion.pipeline import ingest_pcap as _ingest_pcap
    from ingestion.queue import ingest_queue

    _ensure_ingest_queue_worker()

    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
    suffix = Path(file.filename or "capture.pcap").suffix or ".pcap"
    raw = await file.read()
    check = validate_pcap_upload(filename=file.filename, content=raw)
    if not check.ok:
        audit_ingest_event(
            event="pcap_queue_rejected",
            source="pcap_queue",
            request_id=request_id,
            filename=file.filename,
            sha256=check.sha256,
            size_bytes=check.size_bytes,
            code=check.code,
        )
        status = 413 if check.code == "PCAP_TOO_LARGE" else 422
        raise HTTPException(
            status_code=status,
            detail={"code": check.code, "message": check.message, "validation": check.as_dict()},
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = Path(tmp.name)
    try:
        result = _ingest_pcap(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if not result.ok:
        code = result.detail.get("code", "PCAP_NOT_AVAILABLE")
        status = 501 if code in {"PCAP_EXTRACTOR_NOT_CONFIGURED", "PCAP_EXTRACTOR_NOT_WIRED"} else 422
        audit_ingest_event(
            event="pcap_queue_extract_failed",
            source="pcap_queue",
            request_id=request_id,
            filename=file.filename,
            sha256=check.sha256,
            size_bytes=check.size_bytes,
            code=code,
            schema_version=(result.schema or {}).get("schema_version"),
        )
        raise HTTPException(
            status_code=status,
            detail={
                "code": code,
                "message": result.detail.get("message", "PCAP extraction failed"),
                "capabilities": result.detail,
                "schema_version": (result.schema or {}).get("schema_version"),
                "validation": result.validation,
                "upload": check.as_dict(),
            },
        )

    try:
        job = ingest_queue.submit(result.flows, source="pcap_upload")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "QUEUE_FULL", "message": str(exc)}) from exc

    audit_ingest_event(
        event="pcap_queue_submitted",
        source="pcap_queue",
        request_id=request_id,
        filename=file.filename,
        sha256=check.sha256,
        size_bytes=check.size_bytes,
        code="OK",
        flow_count=len(result.flows),
        schema_version=(result.schema or {}).get("schema_version"),
        extra={"job_id": job.job_id},
    )
    return {"ok": True, "job": job.as_dict(), "upload": check.as_dict(), "flow_count": len(result.flows)}


@router.get("/ingest/queue/{job_id}")
def ingest_queue_job(job_id: str):
    from ingestion.queue import ingest_queue

    job = ingest_queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": job_id})
    return job.as_dict()


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


@router.post("/response/plan")
def response_plan(body: ControlledResponsePlanRequest):
    """Stage-2 Phase D: advisory playbook + optional simulation preview (not live mitigation)."""
    from backend.services.controlled_response import build_response_plan

    return build_response_plan(
        attack_type=body.attack_type,
        severity=body.severity,
        confidence=body.confidence,
        traffic_intensity=body.traffic_intensity,
        certainty=body.certainty,
        is_attack=body.is_attack,
        asset_criticality=body.asset_criticality,
        risk_score=body.risk_score,
        start_simulation=body.start_simulation,
        incident_id=body.incident_id,
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
