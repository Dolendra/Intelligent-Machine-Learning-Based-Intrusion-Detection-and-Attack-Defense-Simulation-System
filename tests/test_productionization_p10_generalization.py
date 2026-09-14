"""P10 — Generalization report structure (frozen evaluation; no retrain)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "models" / "trained_models" / "generalization_report.json"
DOC = ROOT / "docs" / "GENERALIZATION.md"


def test_generalization_doc_exists() -> None:
    assert DOC.is_file(), "docs/GENERALIZATION.md missing"


def test_generalization_report_core_fields() -> None:
    assert REPORT.is_file(), "Run scripts/41_generalization_report.py first"
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    assert data.get("experiment_id") == "EXP-017"
    assert data.get("phase") == "P10"
    assert data.get("frozen_models", {}).get("no_retrain") is True
    assert data.get("frozen_models", {}).get("no_tuning_on_temporal_holdout") is True

    bin_cmp = data["comparison"]["binary"]
    assert "iid_test" in bin_cmp and "friday_temporal" in bin_cmp
    assert "degradation_iid_minus_friday" in bin_cmp
    assert abs(float(bin_cmp["iid_test"]["f1"]) - 0.9904784130688448) < 1e-9

    families = {r["attack_type"] for r in data["class_wise"]["friday_temporal"]}
    assert families == {"Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"}

    drift = data["drift"]
    assert drift["iid_train_to_test"]["flagged_psi_ge_0.2_count"] == 0
    assert "not_a_claim_of" in drift["iid_train_to_test"]
    assert data["external_dataset"]["conclusion"].startswith("External-dataset")
    assert data["unknown_zero_day"]["status"] == "out_of_scope"
    assert "research_vs_production" in data
