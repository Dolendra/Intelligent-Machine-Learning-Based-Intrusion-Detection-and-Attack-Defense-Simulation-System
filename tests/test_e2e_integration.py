"""Phase 10 end-to-end tests: framework endpoints, the R3 results endpoint, and the full flow
predict -> incident -> response proposal -> framework comparison, through the HTTP API."""
from __future__ import annotations

import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _ready() -> bool:
    try:
        from backend.services import pipeline as svc
        from research.serving import GATE_DIR
        return svc.models_ready() and (GATE_DIR / "aegis_osr_bundle.joblib").exists()
    except Exception:  # noqa: BLE001
        return False


needs_models = pytest.mark.skipif(not _ready(), reason="frozen models + gate artifacts required")


def _rows(family: str, n: int = 1) -> list[dict]:
    from ids_config import ROOT

    pool = pd.read_parquet(ROOT / "research_artifacts" / "replay" / "replay_pool.parquet")
    drop = {"family", "fine_label", "day", "dataset"}
    return [{k: float(v) for k, v in r.items() if k not in drop}
            for _, r in pool[pool["family"] == family].head(n).iterrows()]


# ----------------------------------------------------------------------------- framework catalogue
def test_framework_modules_lists_catalogue_and_active_pipeline_from_config():
    body = client.get("/api/framework/modules").json()
    assert [m["name"] for m in body["modules"]["policy"]] == ["frozen", "gate", "union"]
    assert {m["name"] for m in body["modules"]["open_set"]} == {"aegis_osr_gate", "none"}
    assert body["active"] == {"detector": "frozen_v11", "open_set": "aegis_osr_gate", "policy": "frozen",
                              "explainer": "shap", "adapter": None}


def test_framework_assess_validates_input():
    assert client.post("/api/framework/assess", json={"flows": []}).status_code == 422
    assert client.post("/api/framework/assess", json={"flows": "x"}).status_code == 422
    assert client.post("/api/framework/assess", json={"flows": [{}] * 501}).status_code == 422


@needs_models
def test_framework_assess_rejects_unknown_module():
    r = client.post("/api/framework/assess", json={"flows": _rows("BENIGN"), "policy": "bogus"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "INVALID_MODULE"


# ----------------------------------------------------------------------------- R3 results endpoint
def test_r3_endpoint_is_404_before_analysis_and_serves_verdicts_after(tmp_path, monkeypatch):
    import backend.routes.v3 as v3

    monkeypatch.setattr(v3, "R3_ANALYSIS", tmp_path / "analysis")
    assert client.get("/api/research/r3").status_code == 404
    d = tmp_path / "analysis" / "run_x"
    d.mkdir(parents=True)
    hyp = {"meta": {"seeds": [101, 102]},
           "A1": {"description": "LOAFO", "verdict": "supported",
                  "per_model": {"xgb_ref": {"mean": 0.2, "t_p": 0.001, "holm_p": 0.004, "n_seeds": 2, "extra": 1}}}}
    rel = {"RS1": {"rho": -0.2, "verdict": "rejected", "n": 40}, "RS2": {"rho": 0.1, "verdict": "rejected"},
           "phase7_gate": {"open": False}}
    (d / "hypotheses.json").write_text(json.dumps(hyp), encoding="utf-8")
    (d / "reliability.json").write_text(json.dumps(rel), encoding="utf-8")
    (d / "MANIFEST.json").write_text("{}", encoding="utf-8")
    body = client.get("/api/research/r3").json()
    assert body["analysis"] == "run_x" and body["hypotheses"]["A1"]["verdict"] == "supported"
    assert body["hypotheses"]["A1"]["per_model"]["xgb_ref"] == {"mean": 0.2, "t_p": 0.001, "holm_p": 0.004,
                                                                 "n_seeds": 2}
    assert body["hypotheses"]["A5"]["verdict"] is None          # not in this analysis: reported as missing
    assert body["reliability"]["RS1"]["verdict"] == "rejected" and body["reliability"]["phase7_gate_open"] is False


# ----------------------------------------------------------------------------- full flow
@needs_models
def test_end_to_end_predict_incident_response_and_framework_comparison():
    from database.db import Incident, SessionLocal

    # 1. a known attack through the public prediction API raises and persists an incident
    dos = _rows("DoS", 1)[0]
    pred = client.post("/api/predict", json={"features": dos, "persist": True, "source_ref": "e2e-dos"}).json()
    assert pred["is_attack"] is True and pred["detection_decision"]["raises_incident"] is True
    inc_id = pred["incident_id"]
    assert inc_id and client.get(f"/api/incidents/{inc_id}").json()["attack_type"] == pred["attack_type"]

    # 2. the incident drives a response proposal (dry-run by default) that is listed for the incident
    prop = client.post(f"/api/incidents/{inc_id}/response/propose")
    assert prop.status_code == 200, prop.text
    actions = client.get(f"/api/incidents/{inc_id}/response/actions").json()["items"]
    assert actions, "the proposed action is listed for the incident"

    # 3. the framework compares policies on the same traffic without persisting anything
    flows = _rows("BENIGN", 5) + _rows("DoS", 3) + _rows("Heartbleed", 3)
    with SessionLocal() as db:
        before = db.query(Incident).count()
    res = {p: client.post("/api/framework/assess", json={"flows": flows, "policy": p}).json()
           for p in ("frozen", "gate", "union")}
    with SessionLocal() as db:
        assert db.query(Incident).count() == before            # read-only
    assert all(r["persisted"] is False and r["total"] == len(flows) for r in res.values())
    assert res["frozen"]["incidents"] <= res["union"]["incidents"] and res["gate"]["incidents"] <= res["union"]["incidents"]
    # the default framework pipeline agrees with the service verdict for the persisted flow
    one = client.post("/api/framework/assess", json={"flows": [dos]}).json()["results"][0]
    assert one["detection"]["family"] == pred["attack_type"]
    assert one["decision"]["raises_incident"] == pred["detection_decision"]["raises_incident"]
