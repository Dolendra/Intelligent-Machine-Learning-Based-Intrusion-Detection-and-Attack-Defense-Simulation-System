"""Final freeze checks: artifact consistency + SHAP contribution alignment."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pytest

from backend.services import pipeline as svc
from ids_config import ROOT, load_config, resolve_path
from ml.features.pipeline import FeatureBundle
from simulation.engine.core import SimulationEngine

pytestmark = pytest.mark.skipif(not svc.models_ready(), reason="Train models first")


def _model_dir() -> Path:
    return resolve_path(load_config()["models"]["output_dir"])


def test_final_artifact_consistency():
    out = _model_dir()
    for name in ("feature_bundle.joblib", "binary_best.joblib", "multiclass_best.joblib"):
        assert (out / name).exists(), name

    bundle: FeatureBundle = FeatureBundle.load(out / "feature_bundle.joblib")
    binary = joblib.load(out / "binary_best.joblib")
    multi = joblib.load(out / "multiclass_best.joblib")

    bin_classes = [int(c) for c in list(getattr(binary, "classes_", []))]
    assert bin_classes == [0, 1]

    assert bundle.attack_label_encoder is not None
    attack_names = [str(c) for c in bundle.attack_label_encoder.classes_]
    assert "BENIGN" not in attack_names
    assert len(attack_names) >= 2

    multi_classes = list(getattr(multi, "classes_", []))
    # Encoded ints must match attack encoder length
    assert len(multi_classes) == len(attack_names)
    assert "BENIGN" not in [str(c) for c in multi_classes]

    op_path = out / "threshold_operating_point.json"
    assert op_path.exists()
    op = json.loads(op_path.read_text(encoding="utf-8"))
    assert abs(float(op["operating_threshold"]) - 0.85) < 1e-9
    assert abs(float(op["uncertainty_lower"]) - 0.10) < 1e-9
    assert abs(float(op["uncertainty_upper"]) - 0.95) < 1e-9

    cfg = load_config()
    assert abs(float(cfg["models"]["binary_threshold"]) - 0.85) < 1e-9
    assert abs(float(cfg["models"]["uncertainty_lower"]) - 0.10) < 1e-9
    assert abs(float(cfg["models"]["uncertainty_upper"]) - 0.95) < 1e-9

    predictor = svc.get_predictor()
    assert predictor is not None
    assert abs(float(predictor.binary_threshold) - 0.85) < 1e-9


def test_shap_contribution_count_matches_features():
    demo = svc.load_demo_flow("DDoS")
    feats = demo["features"]
    exp = svc.run_explain(feats, method="shap", top_k=40, allow_missing_features=True)
    predictor = svc.get_predictor()
    assert predictor is not None
    task = "multiclass" if exp.get("is_attack") else "binary"
    n_selected = len(predictor.bundle.selected_for(task))
    # top_k may truncate; ensure reported features never exceed selected count
    assert len(exp.get("top_features") or []) <= n_selected
    assert exp.get("predicted_class_index") is not None
    # If SHAP succeeded without fallback, every contribution maps to a selected feature name
    names = set(predictor.bundle.selected_for(task))
    for item in exp.get("top_features") or []:
        assert item["feature"] in names


def test_simulation_timing_is_deterministic():
    eng = SimulationEngine()
    a = eng.start("DDoS", 0.95)
    b = eng.start("DDoS", 0.95)
    for _ in range(7):
        a = eng.advance(a["id"])
        b = eng.advance(b["id"])
    assert a["state"] == b["state"] == "recovered"
    assert a["latencies"]["detection_s"] == b["latencies"]["detection_s"]
    assert a["latencies"]["defense_s"] == b["latencies"]["defense_s"]
    assert a["latencies"]["recovery_s"] == b["latencies"]["recovery_s"]
    # Rapid advances still produce multi-second simulated timeline
    assert float(a["timeline"][-1]["t_s"]) >= 10.0
