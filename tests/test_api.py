"""API smoke tests — skip predict if models are missing."""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.pipeline import models_ready

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "version" in r.json()


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"


def test_models_endpoint():
    r = client.get("/api/models")
    assert r.status_code == 200
    body = r.json()
    assert "application_version" in body
    assert "models_loaded" in body


def test_recommendation_endpoint():
    r = client.post("/api/recommendation", json={"attack_type": "PortScan", "severity": "MEDIUM"})
    assert r.status_code == 200
    body = r.json()
    assert body["advisory_only"] is True
    assert "rule_hits" in body


def test_risk_with_asset_criticality():
    r = client.post(
        "/api/risk",
        json={
            "attack_type": "DDoS",
            "confidence": 0.9,
            "is_attack": True,
            "traffic_intensity": 0.8,
            "asset_criticality": 5,
        },
    )
    assert r.status_code == 200
    assert r.json()["risk_score"] > 0
    assert "asset_criticality" in r.json()["factors"]


def test_simulation_endpoints():
    start = client.post("/api/simulation/start", json={"attack_type": "DoS", "confidence": 0.9})
    assert start.status_code == 200
    sid = start.json()["id"]
    adv = client.post("/api/simulation/advance", json={"session_id": sid})
    assert adv.status_code == 200
    assert adv.json()["state"] == "normal"


@pytest.mark.skipif(not models_ready(), reason="Train models first")
def test_predict_requires_features():
    tmpl = client.get("/api/features/template").json()["features"]
    r = client.post("/api/predict", json={"features": tmpl, "persist": False})
    assert r.status_code == 200
    assert "attack_type" in r.json()


@pytest.mark.skipif(not models_ready(), reason="Train models first")
def test_predict_batch():
    tmpl = client.get("/api/features/template").json()["features"]
    r = client.post(
        "/api/predict/batch",
        json={"flows": [tmpl, tmpl], "persist": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_flows"] == 2
    assert "results" in body
    assert len(body["results"]) == 2


def test_export_endpoints():
    r = client.get("/api/export/incidents.csv")
    assert r.status_code == 200
    assert "incident_id" in r.text.splitlines()[0]
    j = client.get("/api/export/incidents.json")
    assert j.status_code == 200
    assert "analytics" in j.json()


def test_simulation_has_phase_guide():
    start = client.post("/api/simulation/start", json={"attack_type": "DDoS", "confidence": 0.9})
    assert start.status_code == 200
    body = start.json()
    assert "phase_guide" in body
    assert "comparison" in body
    assert len(body["phase_guide"]) >= 5
