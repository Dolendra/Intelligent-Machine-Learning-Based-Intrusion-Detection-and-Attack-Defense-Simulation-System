"""Tests for drift helpers, scenario package split, API auth middleware."""
from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from backend.middleware.api_auth import ApiKeyMiddleware
from ml.evaluation.drift import feature_drift_report, population_stability_index
from simulation.scenarios import START, IMPACT, apply_defense
from simulation.scenarios import ddos, portscan
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


def test_scenario_modules_registered():
    assert "DDoS" in START and "PortScan" in IMPACT
    assert START["DDoS"] is ddos.start
    assert IMPACT["PortScan"] is portscan.impact


def test_psi_identical_near_zero():
    rng = np.random.default_rng(0)
    x = rng.normal(size=1000)
    psi = population_stability_index(x, x + rng.normal(scale=0.01, size=1000))
    assert psi < 0.1


def test_feature_drift_flags_shift():
    rng = np.random.default_rng(1)
    ref = pd.DataFrame({"a": rng.normal(0, 1, 500), "b": rng.normal(0, 1, 500)})
    cur = pd.DataFrame({"a": rng.normal(3, 1, 500), "b": rng.normal(0, 1, 500)})
    report = feature_drift_report(ref, cur, ["a", "b"])
    assert report["features_compared"] == 2
    assert any(f["feature"] == "a" for f in report["top_psi"])


def test_api_key_middleware_blocks_when_enabled(monkeypatch):
    monkeypatch.delenv("DISABLE_API_AUTH", raising=False)

    async def ok(_request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/api/predict", ok, methods=["POST"]), Route("/api/health", ok)])
    app.add_middleware(ApiKeyMiddleware, enabled=True, api_key="secret", header_name="X-API-Key")
    client = TestClient(app)
    assert client.get("/api/health").status_code == 200
    assert client.post("/api/predict").status_code == 401
    assert client.post("/api/predict", headers={"X-API-Key": "secret"}).status_code == 200


def test_apply_defense_dispatch():
    class _E:
        def __init__(self, eid):
            self.id = eid
            self.traffic = "malicious"
            self.intensity = 0.9

    class _N:
        def __init__(self, nid):
            self.id = nid
            self.status = "alert"
            self.kind = "host"

    class _S:
        attack_type = "PortScan"
        edges = [_E("e_scan"), _E("e1")]
        nodes = [_N("firewall"), _N("ports")]

    detail = apply_defense(_S())
    assert "block" in detail.lower() or "Scanner" in detail
