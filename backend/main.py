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
from backend.middleware.logging_mw import attach_request_logging
from database.db import init_db
from ids_config import load_config

cfg = load_config()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import os

    init_db()
    demo_mode = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"}
    if demo_mode:
        n = seed_demo_incidents()
        if n:
            print(f"Seeded {n} demo incidents (DEMO_MODE=true)")
    yield


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
attach_rate_limit(app)
attach_api_auth(app)
attach_request_logging(app)


@app.get("/")
def root():
    return {
        "name": cfg["project"]["name"],
        "version": cfg["project"]["version"],
        "docs": "/docs",
        "health": "/api/health",
    }
