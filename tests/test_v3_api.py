"""v3 API: Zero-Day Gate, research overview, Live Traffic Monitor, RBAC mapping, config cache."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.middleware.api_auth import permission_for_request
from backend.services import pipeline as svc
from research.serving import GATE_DIR

client = TestClient(app)
gate_ready = (GATE_DIR / "aegis_osr_bundle.joblib").exists()
needs_models = pytest.mark.skipif(not svc.models_ready(), reason="Train models first")
needs_gate = pytest.mark.skipif(not gate_ready, reason="Run scripts/51_train_zero_day_gate.py")


def _demo_features(attack_type: str = "DDoS") -> dict:
    return client.get("/api/demo/flow", params={"attack_type": attack_type}).json()["features"]


def test_rbac_mapping_for_v3_routes():
    assert permission_for_request("GET", "/api/research/overview") == "read_models"
    assert permission_for_request("GET", "/api/zero-day/status") == "read_models"
    assert permission_for_request("GET", "/api/live/scenarios") == "read_models"
    assert permission_for_request("POST", "/api/zero-day/assess") == "write_detect"


def test_research_overview_shape():
    r = client.get("/api/research/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["proposed"] == "Aegis-OSR"
    assert set(body["status"]) >= {"loafo", "temporal", "cross", "gate"}
    assert any(m["group"] == "proposed" for m in body["methods_catalog"])


def test_research_protocol_unknown_is_404():
    assert client.get("/api/research/openset/bogus").status_code == 404


@needs_gate
def test_zero_day_status_and_assess():
    st = client.get("/api/zero-day/status").json()
    assert st["available"] is True and "BENIGN" in st["known_classes"]
    r = client.post("/api/zero-day/assess", json={"flows": [_demo_features()], "explain_top": 3})
    assert r.status_code == 200
    res = r.json()["results"][0]
    assert 0 < res["p_value"] <= 1
    assert res["label"] in st["known_classes"] + ["UNKNOWN-ATTACK", "ZERO-DAY-ANOMALY"]
    assert set(res["evidence"]) == {"supervised", "novelty"}


@needs_gate
def test_zero_day_assess_rejects_missing_features():
    r = client.post("/api/zero-day/assess", json={"flows": [{"Flow Duration": 1.0}]})
    assert r.status_code == 422


@needs_models
def test_predict_carries_advisory_zero_day_without_changing_verdict():
    features = _demo_features()
    body = client.post("/api/predict", json={"features": features, "persist": False}).json()
    assert body["is_attack"] is True  # frozen v1.1 verdict unchanged
    assert "zero_day" in body
    if gate_ready:
        assert body["zero_day"]["alert"] in (True, False)


@needs_models
def test_live_scenarios_and_stream():
    cat = client.get("/api/live/scenarios").json()
    ids = {s["id"] for s in cat["scenarios"]}
    assert {"enterprise_day", "ddos_wave", "zero_day", "apt_campaign"} <= ids
    if not cat["pool_available"]:
        pytest.skip("replay pool missing")
    with client.websocket_connect("/api/ws/live?scenario=ddos_wave&rate=40") as ws:
        assert ws.receive_json()["type"] == "connected"
        tick = ws.receive_json()
        assert tick["type"] == "tick" and tick["flows"]
        f = tick["flows"][0]
        assert {"truth", "frozen", "gate", "outcome"} <= set(f)
        ws.send_text(json.dumps({"action": "pause"}))
        for _ in range(3):
            msg = ws.receive_json()
            if msg.get("paused"):
                break
        assert msg["paused"] is True and msg["flows"] == []


def test_load_config_cache_returns_isolated_copies():
    from ids_config import load_config

    a = load_config()
    a["risk"]["weights"]["attack_base"] = 123
    assert load_config()["risk"]["weights"]["attack_base"] != 123
