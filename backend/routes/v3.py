"""v3 routes: Aegis-OSR Zero-Day Gate, research results, and the Live Traffic Monitor."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.schemas.api import ZeroDayAssessRequest
from ids_config import ROOT, load_config

router = APIRouter()
ARTIFACTS = ROOT / "research_artifacts"


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# --------------------------------------------------------------------------- zero-day gate
@router.get("/zero-day/status")
def zero_day_status():
    from research.serving import gate_error, get_gate

    gate = get_gate()
    if gate is None:
        return {"available": False, "reason": gate_error()}
    return gate.status()


@router.post("/zero-day/assess")
def zero_day_assess(body: ZeroDayAssessRequest):
    from research.serving import gate_error, get_gate

    gate = get_gate()
    if gate is None:
        raise HTTPException(status_code=503, detail={"code": "GATE_NOT_READY", "message": gate_error()})
    try:
        results = gate.assess(body.flows, explain_top=body.explain_top, alpha=body.alpha)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_FEATURES", "message": str(exc)}) from exc
    return {
        "alpha": body.alpha or gate.alpha,
        "total": len(results),
        "alerts": sum(r["alert"] for r in results),
        "novel": sum(r["novel"] for r in results),
        "results": results,
    }


@router.get("/zero-day/alerts")
def zero_day_alerts(limit: int = 50, gate_only: bool = False):
    """Persisted Zero-Day Gate alerts for analyst review.

    Under the operational default policy ``frozen`` a gate-only alert raises no incident, so this
    list is where it can be reviewed. Gate-only alerts carry ``review_label = "Zero-Day
    Candidate"``; they are advisory and cannot authorize containment (security.response).
    """
    from database.db import SessionLocal, ZeroDayAlert
    from security.detection_policy import GATE_ONLY_LABEL

    limit = max(1, min(int(limit), 500))
    with SessionLocal() as db:
        q = db.query(ZeroDayAlert)
        if gate_only:
            q = q.filter(ZeroDayAlert.frozen_is_attack == 0)
        rows = q.order_by(ZeroDayAlert.id.desc()).limit(limit).all()
        items = [{
            "id": r.id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "origin": r.origin,
            "source_ref": r.source_ref,
            "policy": r.policy,
            "raised_incident": bool(r.raised_incident),
            "incident_code": r.incident_code,
            "gate_only": not bool(r.frozen_is_attack),
            "review_label": GATE_ONLY_LABEL if not r.frozen_is_attack else r.frozen_attack_type,
            "gate_label": r.gate_label,
            "p_value": r.p_value,
            "alpha": r.alpha,
            "family_hint": r.family_predicted,
            "frozen_attack_type": r.frozen_attack_type,
            "gate_model_version": r.gate_model_version,
        } for r in rows]
    return {"total": len(items), "advisory": True, "items": items}


# --------------------------------------------------------------------------- research results
_PROTOCOLS = {"loafo": "openset_loafo", "temporal": "openset_temporal", "cross": "openset_cross"}


@router.get("/research/overview")
def research_overview():
    """Compact digest of every v3 research artifact for the Research Lab UI."""
    from research.digest import build_overview

    return build_overview(ARTIFACTS)


R3_ANALYSIS = ARTIFACTS / "r3" / "analysis"
R3_HYPOTHESES = ("A1", "A2", "A4", "A5", "A6", "A7")


def _latest_r3_analysis() -> Path | None:
    if not R3_ANALYSIS.exists():
        return None
    runs = [p for p in R3_ANALYSIS.iterdir() if (p / "hypotheses.json").exists() and (p / "MANIFEST.json").exists()]
    return max(runs, key=lambda p: (p / "MANIFEST.json").stat().st_mtime) if runs else None


def _model_row(r: dict) -> dict:
    keys = ("mean", "t_p", "holm_p", "hierarchical_bootstrap_95ci", "n_seeds", "folds_positive", "folds",
            "tost_p", "noninferiority_p", "realised_fpr_smoothed", "realised_fpr_deterministic", "in_band")
    return {k: r[k] for k in keys if k in r}


@router.get("/research/r3")
def research_r3():
    """Pre-registered R3 results (docs/research/R3_AMENDMENT.md): verdicts, per-model effects, reliability study."""
    d = _latest_r3_analysis()
    if d is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_RUN", "message": "R3 analysis not generated yet"})
    hyp, rel = _read_json(d / "hypotheses.json"), _read_json(d / "reliability.json")
    if hyp is None or rel is None:
        raise HTTPException(status_code=500, detail={"code": "CORRUPT", "message": f"unreadable analysis in {d.name}"})
    out = {"analysis": d.name, "meta": hyp.get("meta", {}), "hypotheses": {}}
    for h in R3_HYPOTHESES:
        block = hyp.get(h, {})
        per = block.get("per_model") or block.get("per_model_method") or {}
        out["hypotheses"][h] = {"description": block.get("description"), "verdict": block.get("verdict"),
                                "per_model": {m: _model_row(r) for m, r in per.items()}}
    out["reliability"] = {k: {kk: rel[k].get(kk) for kk in ("rho", "day_cluster_ci95", "n", "clusters", "verdict")}
                          for k in ("RS1", "RS2")}
    out["reliability"]["phase7_gate_open"] = rel.get("phase7_gate", {}).get("open")
    return out


# --------------------------------------------------------------------------- framework (Phase 9/10)
@router.get("/framework/modules")
def framework_modules():
    """Registered framework modules and the pipeline the service is configured to run."""
    from framework import AegisPipeline, registry

    try:
        active = AegisPipeline.from_config().describe()
    except Exception as exc:  # noqa: BLE001 — a bad config must not hide the catalogue
        active = {"error": str(exc)}
    return {"modules": registry.describe(), "active": active}


@router.post("/framework/assess")
def framework_assess(body: dict):
    """Run flows through a chosen module combination. Read-only: nothing is persisted and no incident is raised.

    Body: ``{"flows": [...], "policy": "frozen|gate|union", "open_set": "aegis_osr_gate|none"}``
    """
    from framework import AegisPipeline, UnknownModuleError
    from ml.prediction.predictor import FeatureValidationError

    flows = body.get("flows")
    if not isinstance(flows, list) or not flows or not all(isinstance(f, dict) for f in flows):
        raise HTTPException(status_code=422, detail={"code": "INVALID_BATCH", "message": "flows must be a non-empty list"})
    if len(flows) > 500:
        raise HTTPException(status_code=422, detail={"code": "BATCH_TOO_LARGE", "message": "at most 500 flows"})
    overrides = {k: body[k] for k in ("policy", "open_set") if body.get(k)}
    try:
        pipe = AegisPipeline.from_config(explainer=None, **overrides)
        results = pipe.process(flows)
    except FeatureValidationError as exc:  # a ValueError subclass: must be caught first
        raise HTTPException(status_code=422, detail={"code": "INVALID_FEATURES", "message": str(exc)}) from exc
    except (UnknownModuleError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_MODULE", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "MODEL_NOT_READY", "message": str(exc)}) from exc
    return {"pipeline": pipe.describe(), "persisted": False, "total": len(results),
            "incidents": sum(r.decision.raises_incident for r in results),
            "results": [r.to_dict() for r in results]}


@router.get("/research/openset/{protocol}")
def research_protocol(protocol: str):
    if protocol not in _PROTOCOLS:
        raise HTTPException(status_code=404, detail={"code": "UNKNOWN_PROTOCOL", "message": protocol})
    data = _read_json(ARTIFACTS / f"{_PROTOCOLS[protocol]}_summary.json")
    if data is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_RUN", "message": f"{protocol} results not generated yet"})
    return data


# --------------------------------------------------------------------------- live monitor
@router.get("/live/scenarios")
def live_scenarios():
    from backend.services.live_stream import MAX_RATE, POOL_PATH, scenario_catalog

    return {
        "scenarios": scenario_catalog(),
        "max_rate": MAX_RATE,
        "pool_available": POOL_PATH.exists(),
        "disclaimer": "Replay of held-out CICIDS2017 flows (not live packet capture). Source/destination "
                      "addresses are synthetic and for visualization only.",
    }


def _auth_enabled() -> bool:
    from security.auth.posture import auth_enabled, kill_switch_allowed

    return auth_enabled() and not kill_switch_allowed("DISABLE_API_AUTH")


async def _authorize_ws(websocket: WebSocket, path: str, permission: str) -> dict | None:
    """Same contract as /ws/events: bearer token via ?token= or Authorization header."""
    from security.rbac import has_permission
    from security.security_events import security_event

    if not _auth_enabled():
        return {"role": "anonymous", "username": None}
    token = websocket.query_params.get("token") or ""
    hdr = websocket.headers.get("authorization") or ""
    if not token and hdr.lower().startswith("bearer "):
        token = hdr.split(" ", 1)[1].strip()
    if not token:
        security_event("ws_unauthorized", path=path, code="UNAUTHORIZED")
        await websocket.close(code=4401)
        return None
    from security.auth.service import AuthError, identity_from_bearer

    try:
        identity = identity_from_bearer(token)
    except AuthError as exc:
        security_event("ws_unauthorized", path=path, code=exc.code)
        await websocket.close(code=4401)
        return None
    role = str(identity.get("role") or "viewer")
    if not has_permission(role, permission):
        security_event("ws_forbidden", path=path, code="FORBIDDEN", user=identity.get("username"), role=role)
        await websocket.close(code=4403)
        return None
    return {"role": role, "username": identity.get("username")}


@router.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    """Stream replayed flows scored by the frozen detector and the Zero-Day Gate.

    Client → server messages (JSON): {"action": "pause"|"resume"|"reset"} or
    {"action": "set", "scenario": "...", "rate": 40}.
    """
    from backend.services.live_stream import SCENARIOS, TICK_SECONDS, LiveSession, load_pool

    who = await _authorize_ws(websocket, "/api/ws/live", "read_models")
    if who is None:
        return
    await websocket.accept()
    scenario = websocket.query_params.get("scenario") or "enterprise_day"
    try:
        rate = int(websocket.query_params.get("rate") or 20)
    except ValueError:
        rate = 20
    try:
        load_pool()
        session = LiveSession(scenario=scenario if scenario in SCENARIOS else "enterprise_day", rate=rate)
    except FileNotFoundError as exc:
        await websocket.send_json({"type": "error", "code": "POOL_MISSING", "message": str(exc)})
        await websocket.close(code=1011)
        return

    await websocket.send_json({"type": "connected", "scenario": session.scenario, "rate": session.rate, **who})
    loop = asyncio.get_running_loop()
    try:
        while True:
            started = loop.time()
            msg = await asyncio.to_thread(session.tick)  # model scoring off the event loop
            await websocket.send_json(msg)
            remaining = TICK_SECONDS - (loop.time() - started)
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=max(remaining, 0.01))
            except asyncio.TimeoutError:
                continue
            try:
                cmd = json.loads(raw)
            except json.JSONDecodeError:
                continue
            action = cmd.get("action")
            if action == "pause":
                session.paused = True
            elif action == "resume":
                session.paused = False
            elif action == "reset":
                session.reset()
            elif action == "set":
                try:
                    session.set(scenario=cmd.get("scenario"), rate=cmd.get("rate"))
                except ValueError as exc:
                    await websocket.send_json({"type": "error", "code": "BAD_SCENARIO", "message": str(exc)})
    except WebSocketDisconnect:
        return
    except Exception:  # noqa: BLE001 — never leak stack traces over the socket
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
