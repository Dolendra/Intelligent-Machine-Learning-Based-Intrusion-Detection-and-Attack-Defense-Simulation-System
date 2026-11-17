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


# --------------------------------------------------------------------------- research results
_PROTOCOLS = {"loafo": "openset_loafo", "temporal": "openset_temporal", "cross": "openset_cross"}


@router.get("/research/overview")
def research_overview():
    """Compact digest of every v3 research artifact for the Research Lab UI."""
    from research.digest import build_overview

    return build_overview(ARTIFACTS)


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
