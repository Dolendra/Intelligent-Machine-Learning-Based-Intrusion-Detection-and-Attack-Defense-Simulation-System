"""IDS Platform API entrypoint."""
from __future__ import annotations

import sys
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.routes.api import router
from backend.routes.v3 import router as v3_router
from backend.routes.range import router as range_router
from backend.services.seed import seed_demo_incidents
from backend.middleware.rate_limit import attach_rate_limit
from backend.middleware.api_auth import attach_api_auth
from backend.middleware.security_headers import attach_security_headers
from backend.middleware.request_limits import attach_request_limits
from backend.middleware.metrics_mw import attach_metrics
from backend.middleware.logging_mw import attach_request_logging
from backend.middleware.errors import attach_error_handlers
from database.db import init_db
from ids_config import load_config
from security.auth.posture import enforce_startup_posture

cfg = load_config()
# R-05/R-06: fail closed. Raises InsecureConfigurationError (the process does not start) when
# auth is off outside AEGIS_ENV=development/test, a security kill switch is set outside
# development/test, or auth is on without a strong token secret.
SECURITY_POSTURE = enforce_startup_posture()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import logging
    import os

    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("aegis.api").exception("Database init failed: %s", exc)
        raise RuntimeError(f"Database initialization failed: {exc}") from exc

    # R-05 (SEC-2): with auth enabled, refuse to serve while any active account still accepts
    # a password that was published in this repository.
    if SECURITY_POSTURE.auth_enabled:
        from security.auth.posture import InsecureConfigurationError
        from security.auth.users import user_store

        legacy = user_store.users_with_legacy_passwords()
        if legacy:
            raise InsecureConfigurationError(
                f"Refusing to start: accounts {legacy} still use a published default password; "
                "rotate them with scripts/70_rotate_credentials.py"
            )

    # Stage-2 Phase B: in-process ingest→detect queue (prototype, single process)
    try:
        from backend.services import pipeline as svc
        from database.db import SessionLocal
        from ingestion.queue import ingest_queue

        def _predict_batch(flows: list[dict[str, float]]) -> dict:
            db = SessionLocal()
            try:
                return svc.run_prediction_batch(flows, db=db, persist=False, allow_missing_features=False)
            finally:
                db.close()

        ingest_queue.set_predict_fn(_predict_batch)
        ingest_queue.start()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("aegis.api").warning("Ingest queue not started: %s", exc)

    demo_mode = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"}
    if demo_mode:
        n = seed_demo_incidents()
        if n:
            print(f"Seeded {n} demo incidents (DEMO_MODE=true)")

    # P9: reclaim in-flight response states left by process crash
    try:
        from backend.recovery import run_startup_recovery

        summary = run_startup_recovery()
        if summary.get("reclaimed_executing") or summary.get("reclaimed_approved"):
            logging.getLogger("aegis.api").warning("Startup recovery: %s", summary)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("aegis.api").warning("Startup recovery skipped: %s", exc)

    yield
    try:
        from ingestion.queue import ingest_queue

        ingest_queue.stop()
    except Exception:
        pass


app = FastAPI(
    title=cfg["project"]["name"],
    version=cfg["project"]["version"],
    description=(
        "Intelligent ML-based intrusion detection with explainability, "
        "risk scoring, defensive recommendations, and attack–defense simulation."
    ),
    lifespan=lifespan,
)

import os as _os

_cors_origins = list(cfg["api"].get("cors_origins") or ["http://localhost:5173"])
_cors_strict = bool(cfg["api"].get("cors_strict", False)) or _os.getenv("AEGIS_CORS_STRICT", "").lower() in {
    "1",
    "true",
    "yes",
}
if _cors_strict:
    _cors_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    _cors_headers = [
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "X-Request-ID",
        "X-Aegis-Role",
    ]
else:
    # Local Vite demo convenience — enable AEGIS_CORS_STRICT=true for production posture
    _cors_methods = ["*"]
    _cors_headers = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=_cors_methods,
    allow_headers=_cors_headers,
)

app.include_router(router, prefix="/api")
app.include_router(v3_router, prefix="/api")
app.include_router(range_router, prefix="/api")
attach_error_handlers(app)
attach_request_limits(app)
attach_api_auth(app)
# R-17 (SEC-11): the rate limiter is added after auth, so it wraps it and also counts requests
# that fail authentication (online key/token guessing used to be unlimited).
attach_rate_limit(app)
attach_security_headers(app)
attach_metrics(app)
attach_request_logging(app)


@app.get("/")
def root():
    return {
        "name": cfg["project"]["name"],
        "version": cfg["project"]["version"],
        "docs": "/docs",
        "health": "/api/health",
        "ready": "/api/ready",
    }
