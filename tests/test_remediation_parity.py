"""P1-A5 (audit ML pipeline A.1, stages 7/14/15): training/inference feature parity of the frozen v1.1 model.

Verification only: no model, threshold or artifact is changed. Fails loudly if any of the
feature-schema sources drift apart or if inference stops using the training-fitted transform.
"""
from __future__ import annotations

import json
import random

import pytest

from backend.services import pipeline as svc
from ids_config import ROOT

needs_models = pytest.mark.skipif(not svc.models_ready(), reason="frozen models required")
MODEL_DIR = ROOT / "models" / "trained_models"


def _schema_features() -> list[str]:
    raw = json.loads((ROOT / "ingestion" / "schema" / "cicids2017_v1_1.json").read_text(encoding="utf-8"))
    feats = raw.get("features") or raw.get("feature_names") or raw.get("columns")
    return [f["name"] if isinstance(f, dict) else f for f in feats]


@needs_models
def test_all_schema_sources_list_the_same_78_features_in_the_same_order():
    bundle = svc.get_predictor().bundle
    names = list(bundle.feature_names)
    assert len(names) == 78
    assert _schema_features() == names                                   # ingestion schema
    demo = json.loads((MODEL_DIR / "demo_flows.json").read_text(encoding="utf-8"))
    first = (demo.get("items") or demo.get("flows") or list(demo.get("by_label", {}).values()))[0]
    feats = first.get("features", first)
    assert list(feats.keys()) == names                                   # committed demo vectors
    meta = ROOT / "data" / "processed" / "meta.json"                     # git-ignored, local only
    if meta.exists():
        m = json.loads(meta.read_text(encoding="utf-8"))
        assert (m.get("feature_names") or m.get("features")) == names


@needs_models
def test_inference_uses_the_training_fitted_transform():
    pred = svc.get_predictor()
    bundle = pred.bundle
    assert bundle.scaler.n_features_in_ == 78                           # fit on the 78-feature train frame
    assert bundle.selector.get_support().sum() == 40 == len(bundle.selected_features)
    assert bundle.multiclass_selector.get_support().sum() == 40 == len(bundle.selected_features_multiclass)
    assert pred.binary_model.n_features_in_ == 40
    assert pred.multiclass_model.n_features_in_ == 40


@needs_models
def test_prediction_is_independent_of_input_key_order():
    feats = {k: float(v) for k, v in svc.sample_feature_template().items()}
    keys = list(feats)
    random.Random(0).shuffle(keys)
    shuffled = {k: feats[k] for k in keys}
    p = svc.get_predictor()
    a, b = p.predict_row(feats), p.predict_row(shuffled)
    assert (a.is_attack, a.attack_type, a.binary_proba_attack) == (b.is_attack, b.attack_type, b.binary_proba_attack)


@needs_models
def test_gate_features_are_a_subset_of_the_frozen_schema():
    from research.serving import get_gate

    gate = get_gate()
    if gate is None:
        pytest.skip("gate artifacts required")
    assert set(gate.features) <= set(svc.get_predictor().bundle.feature_names)
