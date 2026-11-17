"""User decision 2026-11-18 (audit ML-4): the operational incident policy defaults to "frozen"."""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import pipeline as svc
from research.serving import GATE_DIR
from security.detection_policy import GATE_ONLY_LABEL, POLICIES, configured_policy

client = TestClient(app)
ready = svc.models_ready() and (GATE_DIR / "aegis_osr_bundle.joblib").exists()
needs_models = pytest.mark.skipif(not ready, reason="frozen models + gate artifacts required")


def test_operational_default_is_frozen():
    assert configured_policy() == "frozen"


def test_union_and_gate_remain_selectable():
    assert {"union", "gate"} <= set(POLICIES)


def _heartbleed() -> dict:
    from ids_config import ROOT

    pool = pd.read_parquet(ROOT / "research_artifacts" / "replay" / "replay_pool.parquet")
    row = pool[pool["family"] == "Heartbleed"].iloc[0]
    return {k: float(v) for k, v in row.items() if k not in {"family", "fine_label", "day", "dataset"}}


@needs_models
def test_gate_only_alert_is_recorded_for_review_without_incident():
    ref = "policy-frozen-review"
    body = client.post("/api/predict", json={"features": _heartbleed(), "persist": True,
                                             "source_ref": ref}).json()
    assert body["is_attack"] is False and body["zero_day"]["alert"] is True
    assert body["incident_id"] is None                                   # frozen is the authority
    assert body["detection_decision"]["policy"] == "frozen"
    out = client.get("/api/zero-day/alerts", params={"gate_only": True, "limit": 500}).json()
    mine = [i for i in out["items"] if i["source_ref"] == ref]
    assert mine and out["advisory"] is True
    item = mine[0]
    assert item["review_label"] == GATE_ONLY_LABEL and item["gate_only"] is True
    assert item["raised_incident"] is False and item["policy"] == "frozen"


def test_alert_list_limit_is_bounded():
    r = client.get("/api/zero-day/alerts", params={"limit": 100000})
    assert r.status_code == 200 and r.json()["total"] <= 500
