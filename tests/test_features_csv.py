"""Tests for CSV parsing and dual feature-selector helpers."""
from ml.features.pipeline import FeatureBundle
from backend.services.pipeline import parse_flows_csv


def test_parse_flows_csv_basic():
    csv = "Flow Duration,Total Fwd Packets\n1.0,2.0\n3.5,4.0\n"
    rows = parse_flows_csv(csv)
    assert len(rows) == 2
    assert rows[0]["Flow Duration"] == 1.0


def test_feature_bundle_selected_for_fallback():
    # Minimal stub: only need selected lists + transform helpers conceptually
    class _Dummy:
        pass

    bundle = FeatureBundle(
        feature_names=["a", "b"],
        scaler=_Dummy(),  # type: ignore[arg-type]
        selector=None,
        selected_features=["a"],
        label_encoder=_Dummy(),  # type: ignore[arg-type]
        multiclass_selector=None,
        selected_features_multiclass=[],
    )
    assert bundle.selected_for("binary") == ["a"]
    assert bundle.selected_for("multiclass") == ["a"]
