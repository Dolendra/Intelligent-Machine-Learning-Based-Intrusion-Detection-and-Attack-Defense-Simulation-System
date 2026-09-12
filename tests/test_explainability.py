"""Explainability smoke tests."""
from backend.services.pipeline import models_ready, run_explain, load_demo_flow
import pytest


@pytest.mark.skipif(not models_ready(), reason="Train models first")
def test_shap_and_lime_explain():
    demo = load_demo_flow("DDoS")
    features = demo["features"]
    assert features
    shap = run_explain(features, top_k=5, method="shap")
    lime = run_explain(features, top_k=5, method="lime")
    assert shap["method"] == "shap"
    assert lime["method"] == "lime"
    assert len(shap["top_features"]) >= 1
    assert len(lime["top_features"]) >= 1
