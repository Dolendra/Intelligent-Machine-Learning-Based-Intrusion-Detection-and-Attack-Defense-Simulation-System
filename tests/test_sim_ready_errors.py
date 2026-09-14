"""Phase-4 simulation timestamps/series + Phase-6 ready/request-id tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from simulation.engine.core import SimulationEngine

client = TestClient(app)


def test_ready_endpoint_shape():
    r = client.get("/api/ready")
    assert r.status_code in {200, 503}
    body = r.json()
    if r.status_code == 200:
        assert body["status"] == "ready"
        assert body["ready"] is True
        assert body["dependencies"]["models"]["status"] == "ok"
    else:
        assert body["detail"]["code"] == "MODEL_NOT_READY"


def test_request_id_header_echo():
    r = client.get("/api/health", headers={"X-Request-ID": "test-rid-123"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "test-rid-123"


def test_validation_error_envelope():
    r = client.post("/api/predict", json={"features": "not-a-map"})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
    assert "request_id" in detail


def test_simulation_timestamps_and_series():
    eng = SimulationEngine()
    s = eng.start("DDoS", 0.95, traffic_intensity=0.9)
    sid = s["id"]
    for _ in range(7):
        s = eng.advance(sid)
    assert s["state"] == "recovered"
    assert s["timeline"][-1].get("timestamp")
    assert s["timeline"][-1].get("t_s") is not None
    assert s["latencies"]["detection_s"] is not None
    assert s["latencies"]["defense_s"] is not None
    assert s["latencies"]["recovery_s"] is not None
    assert len(s["series"]["labels"]) >= 5
    assert len(s["series"]["with_defense"]["traffic"]) == len(s["series"]["labels"])
    # Counterfactual risk should not drop below defended risk at recovery
    assert s["series"]["without_defense"]["risk"][-1] >= s["series"]["with_defense"]["risk"][-1]


def test_campaign_simulate_endpoint():
    # Empty campaign → 404
    r = client.post("/api/campaigns/does-not-exist/simulate")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "NOT_FOUND"


def test_golden_path_simulation_api():
    start = client.post("/api/simulation/start", json={"attack_type": "PortScan", "confidence": 0.91})
    assert start.status_code == 200
    sid = start.json()["id"]
    state = start.json()["state"]
    steps = 0
    while state != "recovered" and steps < 10:
        adv = client.post("/api/simulation/advance", json={"session_id": sid})
        assert adv.status_code == 200
        body = adv.json()
        state = body["state"]
        steps += 1
        assert "timestamp" in body["timeline"][-1]
    assert state == "recovered"
    assert body["series"]["labels"]
