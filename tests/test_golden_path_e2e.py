"""Golden-path API integration: demo flow → predict → explain → incident → simulate → recover."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import pipeline as svc

client = TestClient(app)

pytestmark = pytest.mark.skipif(not svc.models_ready(), reason="Train models first")


def test_golden_path_detection_to_recovery():
    demo = client.get("/api/demo/flow", params={"attack_type": "DDoS"})
    assert demo.status_code == 200
    features = demo.json()["features"]
    assert isinstance(features, dict) and features

    pred = client.post("/api/predict", json={"features": features, "persist": True, "source_ref": "e2e-golden-1"})
    assert pred.status_code == 200
    body = pred.json()
    assert body["is_attack"] is True
    assert body["risk_score"] >= 0
    assert body["recommendation"]["advisory_only"] is True
    incident_id = body.get("incident_id")
    assert incident_id

    expl = client.post("/api/explain", json={"features": features, "top_k": 5, "method": "shap"})
    assert expl.status_code == 200
    assert expl.json().get("top_features")

    cf = client.post("/api/explain/counterfactual", json={"features": features, "top_k": 3})
    assert cf.status_code == 200
    assert "edits" in cf.json()

    trace = client.get(f"/api/incidents/{incident_id}/trace")
    assert trace.status_code == 200
    assert trace.json().get("steps")

    sim = client.post(f"/api/incidents/{incident_id}/simulate")
    assert sim.status_code == 200
    sid = sim.json()["id"]

    state = sim.json()["state"]
    steps = 0
    while state != "recovered" and steps < 12:
        adv = client.post("/api/simulation/advance", json={"session_id": sid})
        assert adv.status_code == 200
        state = adv.json()["state"]
        steps += 1
    assert state == "recovered"
    assert adv.json()["latencies"]["detection_s"] is not None

    # Lifecycle advance on incident (status may already be Simulating after sim start)
    detail = client.get(f"/api/incidents/{incident_id}")
    assert detail.status_code == 200
    current = detail.json()
    next_statuses = current.get("allowed_next_statuses") or []
    target = "Investigating" if "Investigating" in next_statuses else (next_statuses[0] if next_statuses else None)
    if target:
        patch = client.patch(
            f"/api/incidents/{incident_id}",
            json={"status": target, "analyst_notes": "golden-path e2e"},
        )
        assert patch.status_code == 200
        assert patch.json()["status"] == target
        assert "golden-path e2e" in str(patch.json().get("analyst_notes") or "")
