"""P11 — Empirical mitigation harness (CONTROLLED test plane)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from empirical.controlled_plane import ControlledTestPlane
from empirical.experiment import ScenarioSpec, run_experiment, run_trial
from empirical.metrics import mitigation_effectiveness
from security.response.adapters import reset_test_adapter, test_network_adapter
from security.response.store import response_store

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "EMPIRICAL_MITIGATION.md"
REPORT = ROOT / "models" / "trained_models" / "empirical_mitigation_report.json"


@pytest.fixture(autouse=True)
def _reset():
    response_store.clear()
    reset_test_adapter()
    yield
    response_store.clear()
    reset_test_adapter()


def test_empirical_doc_exists() -> None:
    assert DOC.is_file()


def test_traffic_decision_block_gates_plane() -> None:
    plane = ControlledTestPlane(attacker_ip="203.0.113.99")
    # Before control: accept
    pre, _ = plane.run_window(n_attack=20, n_benign=5)
    assert pre.attack_accepted == 20
    assert pre.attack_denied == 0

    from security.response.service import approve_action, propose_action

    prop = propose_action(
        attack_type="DDoS",
        source_ip=plane.attacker_ip,
        mode="CONTROLLED",
        actor="tester",
    )
    approve_action(prop["action_id"], actor="tester")
    assert test_network_adapter.snapshot()["count"] == 1

    post, _ = plane.run_window(n_attack=20, n_benign=5)
    assert post.attack_accepted == 0
    assert post.attack_denied == 20
    assert post.benign_accepted == 5  # benign IP not blocked
    assert mitigation_effectiveness(
        baseline_attack_accepted_rate=pre.as_dict()["attack_accepted_rate"],
        defended_attack_accepted_rate=post.as_dict()["attack_accepted_rate"],
    ) == 1.0


def test_recommendation_only_does_not_mitigate() -> None:
    plane = ControlledTestPlane()
    scenario = ScenarioSpec(name="t", attack_type="DDoS", experiment_id="EXP-TEST")
    trial = run_trial(
        scenario=scenario,
        condition="recommendation_only",
        trial=1,
        plane=plane,
        detection_mode="label_oracle",
        model_dir=None,
    )
    assert trial.post["attack_blocked_rate"] == 0.0
    assert trial.measured_mitigation_effectiveness == 0.0
    assert test_network_adapter.snapshot()["count"] == 0


def test_quick_experiment_separates_conditions() -> None:
    out = run_experiment(
        scenarios=[ScenarioSpec(name="ddos_block_source", attack_type="DDoS", experiment_id="EXP-018")],
        repetitions=2,
        detection_mode="label_oracle",
        model_dir=None,
    )
    cmp_ = out["comparisons"]["ddos_block_source"]
    assert cmp_["no_defense_post_attack_blocked_rate_mean"] == 0.0
    assert cmp_["recommendation_only_post_attack_blocked_rate_mean"] == 0.0
    assert cmp_["controlled_response_post_attack_blocked_rate_mean"] == 1.0


def test_report_preserves_simulation_distinction() -> None:
    if not REPORT.is_file():
        pytest.skip("empirical_mitigation_report.json not generated yet")
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    assert data["phase"] == "P11"
    assert data["honesty"]["simulation_preserved"] is True
    assert data["defense_configuration"]["live_firewall_edr"] is False
    assert "EXP-018" in data["experiment_ids"]
    assert "simulation_vs_measurement" in data
