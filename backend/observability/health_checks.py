"""Dependency health checks for readiness (no secret/path leakage to clients)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ids_config import ROOT, load_config


def _safe_bool(ok: bool) -> str:
    return "ok" if ok else "unavailable"


def check_database() -> dict[str, Any]:
    try:
        from database.db import SessionLocal
        from sqlalchemy import text

        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok", "detail": "reachable"}
    except Exception:  # noqa: BLE001
        return {"status": "unavailable", "detail": "database_check_failed"}


def check_models() -> dict[str, Any]:
    try:
        from backend.services import pipeline as svc

        ready = bool(svc.models_ready())
        return {"status": _safe_bool(ready), "detail": "loaded" if ready else "not_loaded"}
    except Exception:  # noqa: BLE001
        return {"status": "unavailable", "detail": "model_check_failed"}


def check_pcap_extractor() -> dict[str, Any]:
    try:
        from ingestion.adapters import pcap_extractor_status

        st = pcap_extractor_status()
        available = bool(st.get("available") or st.get("installed") or st.get("cicflowmeter"))
        return {
            "status": "ok" if available else "degraded",
            "detail": "available" if available else "optional_extractor_missing",
        }
    except Exception:  # noqa: BLE001
        found = False
        for name in ("cicflowmeter", "cicflowmeter.exe"):
            for part in os.getenv("PATH", "").split(os.pathsep):
                if part and (Path(part) / name).exists():
                    found = True
                    break
            if found:
                break
        return {
            "status": "ok" if found else "degraded",
            "detail": "available" if found else "optional_extractor_missing",
        }


def check_queue() -> dict[str, Any]:
    try:
        from ingestion.queue import ingest_queue

        st = ingest_queue.status()
        worker = bool(st.get("worker_alive") or st.get("running"))
        depth = int(st.get("queued") or st.get("depth") or 0)
        return {
            "status": "ok" if worker else "down",
            "detail": "running" if worker else "not_running",
            "depth": depth,
        }
    except Exception:  # noqa: BLE001
        return {"status": "down", "detail": "queue_check_failed", "depth": None}


def check_filesystem() -> dict[str, Any]:
    try:
        data_dir = ROOT / "database"
        data_dir.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".aegis_fs_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return {"status": "ok", "detail": "writable"}
    except Exception:  # noqa: BLE001
        return {"status": "unavailable", "detail": "filesystem_not_writable"}


def dependency_status(*, include_optional: bool = True) -> dict[str, Any]:
    deps = {
        "database": check_database(),
        "models": check_models(),
        "queue": check_queue(),
        "filesystem": check_filesystem(),
    }
    if include_optional:
        deps["pcap_extractor"] = check_pcap_extractor()
    return deps


def readiness_report() -> dict[str, Any]:
    """Required deps must be ok for ready=true. Optional deps may be degraded."""
    deps = dependency_status(include_optional=True)
    required = ("database", "models", "filesystem")
    missing = [name for name in required if deps[name]["status"] != "ok"]
    ready = not missing
    # Public payload — no filesystem paths or exception text
    public_deps = {
        name: {"status": info["status"], "detail": info.get("detail")}
        for name, info in deps.items()
    }
    if "queue" in deps:
        public_deps["queue"]["depth"] = deps["queue"].get("depth")
    cfg = load_config()
    return {
        "ready": ready,
        "status": "ready" if ready else "not_ready",
        "code": None if ready else "NOT_READY",
        "missing": missing,
        "dependencies": public_deps,
        "version": cfg.get("project", {}).get("version"),
        "phase": "P7",
    }
