"""Correctness tests: SHAP shapes, severity edges, source_ref, family ranking."""
from __future__ import annotations

import numpy as np

from explainability.shap_engine import ExplanationEngine
from ml.prediction.predictor import IDSPredictor
from security.risk.engine import severity_label


def test_shap_select_samples_features_classes():
    # (1, 40, 7)
    arr = np.zeros((1, 40, 7))
    arr[0, 3, 2] = 0.5
    out = ExplanationEngine._select_class_shap(arr, class_index=2, n_features=40)
    assert out.shape == (40,)
    assert out[3] == 0.5


def test_shap_select_classes_samples_features():
    # (7, 1, 40)
    arr = np.zeros((7, 1, 40))
    arr[2, 0, 5] = 0.7
    out = ExplanationEngine._select_class_shap(arr, class_index=2, n_features=40)
    assert out.shape == (40,)
    assert out[5] == 0.7


def test_shap_select_list_layout():
    sv = [np.ones((1, 10)) * i for i in range(4)]
    out = ExplanationEngine._select_class_shap(sv, class_index=2, n_features=10)
    assert out.shape == (10,)
    assert float(out[0]) == 2.0


def test_severity_fractional_boundaries():
    assert severity_label(30.5) == "LOW"
    assert severity_label(60.5) == "MEDIUM"
    assert severity_label(80.5) == "HIGH"


def test_family_probabilities_drop_benign():
    class _M:
        classes_ = np.array([0, 1, 2])

    class _B:
        def decode_attack_labels(self, raw):
            return np.array(["BENIGN", "DDoS", "DoS"])[raw]

        def attack_class_names(self):
            return ["DDoS", "DoS"]

    pred = IDSPredictor.__new__(IDSPredictor)
    pred.multiclass_model = _M()
    pred.bundle = _B()
    attack_type, conf, probs = IDSPredictor._family_probabilities(pred, np.array([0.52, 0.25, 0.15]))
    assert "BENIGN" not in probs
    assert attack_type == "DDoS"
    assert abs(sum(probs.values()) - 1.0) < 1e-6
    assert conf == probs["DDoS"]


def test_source_ref_not_invented_from_port():
    from backend.services.pipeline import _flow_source_ref

    assert _flow_source_ref({"Destination Port": 80.0}) is None
    assert _flow_source_ref({"Destination Port": 80.0}, explicit="src:1.2.3.4") == "src:1.2.3.4"
