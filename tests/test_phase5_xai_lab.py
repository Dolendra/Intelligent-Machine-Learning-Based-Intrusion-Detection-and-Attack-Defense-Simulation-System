"""Tests for Phase-5 model lab / counterfactual helpers."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.services import pipeline as svc
from explainability.counterfactual import suggest_counterfactuals
from explainability.global_importance import attack_specific_from_explanations, global_model_importance

client = TestClient(app)


def test_models_health_endpoint():
    r = client.get("/api/models/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body
    assert "models_loaded" in body


def test_experiments_and_drift_endpoints():
    e = client.get("/api/experiments")
    assert e.status_code == 200
    assert "experiments" in e.json()
    d = client.get("/api/drift")
    assert d.status_code == 200
    assert "available" in d.json() or "status" in d.json()


def test_global_shap_endpoint():
    r = client.get("/api/models/shap/global")
    assert r.status_code in {200, 503}
    if r.status_code == 200:
        body = r.json()
        assert "global" in body
        assert body["global"]["binary_top"] or body["global"]["multiclass_top"]


def test_global_importance_helper():
    predictor = svc.get_predictor()
    if predictor is None:
        return
    g = global_model_importance(predictor, top_k=5)
    assert len(g["binary_top"]) <= 5
    agg = attack_specific_from_explanations(
        [
            {
                "prediction": "DDoS",
                "top_features": [
                    {"feature": "a", "contribution": 0.5},
                    {"feature": "b", "contribution": -0.2},
                ],
            },
            {
                "prediction": "DDoS",
                "top_features": [{"feature": "a", "contribution": 0.3}],
            },
        ]
    )
    assert "DDoS" in agg["by_attack"]
    assert agg["by_attack"]["DDoS"]["top_features"][0]["feature"] == "a"


def test_counterfactual_helper_and_api():
    predictor = svc.get_predictor()
    if predictor is None:
        return
    demo = svc.load_demo_flow("DDoS")
    feats = demo["features"]
    out = suggest_counterfactuals(predictor, feats, allow_missing=True, max_edits=3)
    assert "edits" in out
    assert out["baseline"]["attack_type"]
    r = client.post("/api/explain/counterfactual", json={"features": feats, "top_k": 3})
    assert r.status_code == 200
    assert "edits" in r.json()
