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


def test_recommendation_endpoint():
    r = client.post("/api/recommendation", json={"attack_type": "PortScan", "severity": "MEDIUM"})
    assert r.status_code == 200
    assert r.json()["advisory_only"] is True


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
