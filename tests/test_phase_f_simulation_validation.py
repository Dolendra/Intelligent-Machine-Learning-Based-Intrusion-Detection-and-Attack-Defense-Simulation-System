"""Stage-2 Phase F: cyber-range simulation validation (controlled visualization)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from simulation.validation import DEFAULT_FAMILIES, validate_families, validate_session, run_family_to_recovered
from simulation.engine.core import SimulationEngine

client = TestClient(app)


def test_validate_all_families_advisory():
    report = validate_families(DEFAULT_FAMILIES)
    assert report["live_cyber_range"] is False
    assert report["live_mitigation"] is False
    assert report["efficacy_are_assumptions"] is True
    assert report["all_ok"] is True
    assert len(report["results"]) == len(DEFAULT_FAMILIES)
    for row in report["results"]:
        assert row["ok"] is True
        assert row["advisory_only"] is True
        assert row["final_state"] == "recovered"
        assert row["deterministic"] is True


def test_ddos_session_shape():
    run = run_family_to_recovered("DDoS", engine=SimulationEngine())
    errors = validate_session(run["final"], attack_type="DDoS")
    assert errors == []


def test_security_status_phase_f():
    r = client.get("/api/security/status")
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "2-phase-f"
    assert body["cyber_range_validation"]["live_cyber_range"] is False
    assert body["cyber_range_validation"]["script"] == "scripts/27_cyber_range_sim_validate.py"
    assert body["controlled_response"]["live_mitigation"] is False
