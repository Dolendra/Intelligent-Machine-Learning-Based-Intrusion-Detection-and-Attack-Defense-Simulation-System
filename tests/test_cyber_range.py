"""Cyber range: reproducibility, real (computed) detection, response effects, API and RBAC."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cyberrange import RangeConfig, RangeRun, run_headless
from cyberrange.engine import POOL_PATH
from cyberrange.scenarios import SCENARIOS

pytestmark = pytest.mark.skipif(not POOL_PATH.exists(), reason="replay pool not built")


def _strip(m: dict) -> dict:
    m = dict(m)
    m.pop("wall_seconds", None)
    return m


def test_same_seed_reproduces_exactly():
    a = run_headless(RangeConfig(scenario="ddos", seed=11))
    b = run_headless(RangeConfig(scenario="ddos", seed=11))
    assert _strip(a) == _strip(b)


def test_different_seed_changes_traffic():
    a = run_headless(RangeConfig(scenario="dos", seed=1))
    b = run_headless(RangeConfig(scenario="dos", seed=2))
    assert a["flows_total"] != b["flows_total"]


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_every_scenario_completes_with_ground_truth_and_events(scenario):
    run = RangeRun(RangeConfig(scenario=scenario, seed=3))
    view = run.complete()
    assert view["done"] and view["state"] == "COMPLETED"
    types = {e["event_type"] for e in run.events}
    assert {"simulation.started", "topology.ready", "attack.stage_changed", "simulation.completed"} <= types
    seqs = [e["sequence"] for e in run.events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    assert all(e["run_id"] == run.id for e in run.events)
    assert view["metrics"]["attack_flows_sent"] > 0


def test_detection_is_computed_not_scripted():
    """Zero-day traffic is invisible to the frozen model; only the gate can raise the incident."""
    frozen = run_headless(RangeConfig(scenario="zero_day", detector="frozen", seed=1))
    gate = run_headless(RangeConfig(scenario="zero_day", detector="gate", seed=1))
    assert frozen["attack_flow_recall_frozen"] == 0.0
    assert frozen["detection_latency_s"] is None
    assert gate["detection_latency_s"] is not None


def test_defenses_have_measurable_tradeoffs():
    monitor = run_headless(RangeConfig(scenario="dos", defense="monitor_only", seed=4))
    block = run_headless(RangeConfig(scenario="dos", defense="block_source", seed=4))
    isolate = run_headless(RangeConfig(scenario="dos", defense="isolate_host", seed=4))
    limit = run_headless(RangeConfig(scenario="dos", defense="rate_limit", seed=4))
    assert monitor["attack_success_after_defense"] is None  # monitoring changes nothing
    assert block["attack_success_after_defense"] == 0.0
    assert 0.1 < limit["attack_success_after_defense"] < 0.3  # ~20% pass-through
    assert isolate["collateral_rate"] > 0.1 > block["collateral_rate"]  # isolation hurts users
    assert block["availability_mean_during_attack"] > monitor["availability_mean_during_attack"]


def test_manual_mode_waits_for_the_analyst_and_rejects_bad_actions():
    run = RangeRun(RangeConfig(scenario="ddos", seed=5, response_mode="manual"))
    with pytest.raises(ValueError):
        run.respond("block_source")  # nothing detected yet
    while not run.awaiting_decision and not run.done:
        run.step(1)
    assert run.awaiting_decision and run.state == "RESPONSE_OPTIONS"
    with pytest.raises(ValueError):
        run.respond("launch_missiles")
    run.respond("block_source")
    with pytest.raises(ValueError):
        run.respond("rate_limit")  # only one response per incident
    view = run.complete()
    m = view["metrics"]
    assert m["defense_applied"] == "block_source"
    # only *detected* sources are blocked, so a DDoS source caught a moment later leaks a little
    assert m["attack_success_after_defense"] < 0.05
    assert m["attackers_detected"] == m["attackers_total"] == 4


def test_api_lifecycle_and_rbac(monkeypatch):
    from backend.main import app

    client = TestClient(app)
    sc = client.get("/api/range/scenarios").json()
    assert {s["id"] for s in sc["items"]} == set(SCENARIOS)
    run = client.post("/api/range/runs", json={"scenario": "port_scan", "seed": 2, "response_mode": "manual"}).json()
    rid = run["run_id"]
    v = client.post(f"/api/range/runs/{rid}/step", json={"seconds": 30}).json()
    assert v["t"] == 30 and v["awaiting_decision"]
    assert client.post(f"/api/range/runs/{rid}/respond", json={"action": "nope"}).status_code == 409
    assert client.post(f"/api/range/runs/{rid}/respond", json={"action": "block_source"}).status_code == 200
    done = client.post(f"/api/range/runs/{rid}/complete").json()
    assert done["state"] == "COMPLETED" and done["metrics"]["attack_success_after_defense"] == 0.0
    assert client.get("/api/range/runs/does-not-exist").status_code == 404
    assert client.post("/api/range/runs", json={"scenario": "nope"}).status_code == 422
    big = {"scenarios": list(SCENARIOS), "defenses": ["block_source", "rate_limit", "isolate_host", "monitor_only"],
           "seeds": [1, 2, 3]}
    assert client.post("/api/range/experiments/sweep", json=big).status_code == 422


def test_rbac_mapping_for_range_paths():
    from backend.middleware.api_auth import permission_for_request

    assert permission_for_request("GET", "/api/range/scenarios") == "read_models"
    assert permission_for_request("POST", "/api/range/runs") == "write_simulation"
