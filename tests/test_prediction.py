"""Prediction / feature validation unit tests."""
from __future__ import annotations

import pytest

from backend.services.pipeline import get_predictor, load_demo_flow, models_ready, run_prediction
from ml.prediction.predictor import FeatureValidationError


@pytest.mark.skipif(not models_ready(), reason="Train models first")
def test_missing_features_rejected():
    predictor = get_predictor()
    assert predictor is not None
    with pytest.raises(FeatureValidationError):
        predictor.predict_row({"Flow Duration": 1.0}, allow_missing=False)


@pytest.mark.skipif(not models_ready(), reason="Train models first")
def test_demo_prediction_ok():
    demo = load_demo_flow("DDoS")
    result = run_prediction(demo["features"], db=None, persist=False, allow_missing_features=False)
    assert "attack_type" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert 0.0 <= result["risk_score"] <= 100.0
    assert result["certainty"] in {"likely_benign", "uncertain", "likely_attack"}
