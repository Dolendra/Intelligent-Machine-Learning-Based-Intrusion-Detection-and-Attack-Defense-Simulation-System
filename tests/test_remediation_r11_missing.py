"""R-11 (ML-14): missing required features never produce a silent, misleading verdict."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import pipeline as svc

client = TestClient(app)
needs_models = pytest.mark.skipif(not svc.models_ready(), reason="frozen models required")


def _ddos_minus(*drop: str) -> dict:
    demo = svc.load_demo_flow("DDoS")
    feats = dict(demo.get("features", demo))
    for k in drop:
        feats.pop(k, None)
    return feats


@needs_models
def test_missing_features_rejected_without_demo_dev(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("AEGIS_ENV", "production")        # e.g. the docker-compose container
    r = client.post("/api/predict", json={"features": _ddos_minus("Destination Port"),
                                          "persist": False, "allow_missing_features": True})
    assert r.status_code == 422


@needs_models
def test_missing_features_rejected_when_flag_not_set(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    r = client.post("/api/predict", json={"features": _ddos_minus("Destination Port"), "persist": False})
    assert r.status_code == 422


@needs_models
def test_demo_zero_fill_is_reported_and_never_raises_an_incident(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")              # AEGIS_ENV=test from conftest
    r = client.post("/api/predict", json={"features": _ddos_minus("Destination Port", "Flow Duration"),
                                          "persist": True, "allow_missing_features": True,
                                          "source_ref": "r11-missing"})
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert set(body["missing_features"]) == {"Destination Port", "Flow Duration"}
    assert body["prediction_quality"] == "degraded_missing_features"
    assert body["incident_id"] is None


@needs_models
def test_complete_input_reports_complete_quality():
    r = client.post("/api/predict", json={"features": _ddos_minus(), "persist": False})
    assert r.status_code == 200
    assert r.json()["missing_features"] == [] and r.json()["prediction_quality"] == "complete"
