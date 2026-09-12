"""CI-safe demo vectors: bundled demo_flows.json when processed split is absent."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import pipeline as svc

client = TestClient(app)

pytestmark = pytest.mark.skipif(not svc.models_ready(), reason="Train models first")


def test_bundled_demo_ddos_is_attack_without_processed(monkeypatch):
    def _boom(_split: str):
        raise FileNotFoundError("processed missing")

    monkeypatch.setattr("ml.preprocessing.dataset.load_processed", _boom)
    demo = svc.load_demo_flow("DDoS")
    assert demo.get("source") == "bundled_demo_flows"
    assert demo.get("label") == "DDoS"
    assert demo["features"]
    # Not the all-zero template
    assert any(abs(float(v)) > 0 for v in demo["features"].values())

    pred = client.post("/api/predict", json={"features": demo["features"], "persist": False})
    assert pred.status_code == 200
    body = pred.json()
    assert body["is_attack"] is True
    assert float(body["binary_proba_attack"]) >= float(body.get("threshold") or 0.85)


def test_demo_flows_json_artifact_exists():
    from ids_config import load_config, resolve_path

    path = resolve_path(load_config()["models"]["output_dir"]) / "demo_flows.json"
    assert path.exists(), "Commit models/trained_models/demo_flows.json for CI demos"
