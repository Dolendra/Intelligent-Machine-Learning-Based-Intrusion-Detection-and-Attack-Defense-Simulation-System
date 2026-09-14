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
from backend.services.seed import seed_demo_incidents
from backend.middleware.rate_limit import attach_rate_limit
from backend.middleware.api_auth import attach_api_auth
from backend.middleware.security_headers import attach_security_headers
from backend.middleware.metrics_mw import attach_metrics
from backend.middleware.logging_mw import attach_request_logging
from backend.middleware.errors import attach_error_handlers
from database.db import init_db
from ids_config import load_config

cfg = load_config()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import logging
    import os

    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("aegis.api").exception("Database init failed: %s", exc)
        raise RuntimeError(f"Database initialization failed: {exc}") from exc

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg["api"]["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
attach_error_handlers(app)
attach_rate_limit(app)
attach_api_auth(app)
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
