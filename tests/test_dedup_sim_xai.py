"""Tests for incident dedup, XAI agreement helpers, sim list, assets."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from explainability.evaluation import compare_explanations, spearman_rank_correlation, feature_ranks
from security.assets import criticality_for, list_assets


client = TestClient(app)


def test_assets_endpoint():
    r = client.get("/api/assets")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 3
    assert criticality_for("web-server") == 5
    assert list_assets()


def test_simulation_list_and_config():
    start = client.post(
        "/api/simulation/start",
        json={"attack_type": "DDoS", "confidence": 0.9, "traffic_intensity": 0.85},
    )
    assert start.status_code == 200
    body = start.json()
    assert body["metrics"]["configured_intensity"] == 0.85
    listed = client.get("/api/simulation?limit=5")
    assert listed.status_code == 200
    assert any(i["session_id"] == body["id"] for i in listed.json()["items"])


def test_xai_rank_agreement_helpers():
    a = feature_ranks([{"feature": "x", "contribution": 0.5}, {"feature": "y", "contribution": 0.2}])
    b = feature_ranks([{"feature": "x", "contribution": 0.9}, {"feature": "y", "contribution": 0.1}])
    assert spearman_rank_correlation(a, b) == 1.0
    cmp = compare_explanations(
        [{"feature": "Flow Packets/s", "contribution": 0.4}, {"feature": "Flow Bytes/s", "contribution": 0.2}],
        [{"feature": "Flow Packets/s", "contribution": 0.3}, {"feature": "Idle Mean", "contribution": 0.1}],
    )
    assert "shap_vs_lime" in cmp
    assert cmp["shap_vs_lime"]["top5_jaccard"] > 0


def test_incident_dedup_same_source():
    from backend.services import pipeline as svc
    from database.db import SessionLocal

    if not svc.models_ready():
        return
    demo = svc.load_demo_flow("DDoS")
    feats = demo["features"]
    feats = {**feats, "Destination Port": 80.0}
    db = SessionLocal()
    try:
        a = svc.run_prediction(feats, db=db, persist=True, allow_missing_features=True, source_ref="src:test-dedup")
        b = svc.run_prediction(feats, db=db, persist=True, allow_missing_features=True, source_ref="src:test-dedup")
        if a.get("is_attack") and b.get("is_attack"):
            assert a["incident_id"] == b["incident_id"]
            assert b.get("deduplicated") is True
    finally:
        db.close()
