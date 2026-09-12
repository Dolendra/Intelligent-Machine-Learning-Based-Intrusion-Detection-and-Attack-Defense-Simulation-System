"""Quick tests for selection scoring, intensity, CSV validation."""
import pytest

from backend.services.pipeline import models_ready, parse_flows_csv, sample_feature_template
from ml.evaluation.selection import binary_selection_score
from ml.features.intensity import _rank_vs_percentiles, clear_intensity_cache, intensity_from_features


def test_binary_selection_prefers_high_recall_low_fpr():
    weak = binary_selection_score({"recall": 0.7, "f1": 0.7, "pr_auc": 0.7, "fpr": 0.2, "infer_seconds_val": 0.5})
    strong = binary_selection_score({"recall": 0.99, "f1": 0.98, "pr_auc": 0.99, "fpr": 0.01, "infer_seconds_val": 0.1})
    assert strong > weak


def test_percentile_rank_monotonic():
    pct = {"50": 10.0, "75": 20.0, "90": 40.0, "95": 60.0, "99": 100.0}
    assert _rank_vs_percentiles(5, pct) < _rank_vs_percentiles(50, pct) < _rank_vs_percentiles(200, pct)


def test_csv_rejects_non_numeric():
    if models_ready():
        feats = sample_feature_template()
        header = ",".join(feats.keys())
        values = []
        for i, k in enumerate(feats.keys()):
            values.append("abc" if i == 0 else "0.0")
        csv = header + "\n" + ",".join(values) + "\n"
    else:
        csv = "Flow Duration,Total Fwd Packets\n1.0,abc\n"
    with pytest.raises(ValueError, match="invalid numeric"):
        parse_flows_csv(csv)


def test_intensity_fallback_without_reference():
    clear_intensity_cache()
    v = intensity_from_features({"Flow Packets/s": 50000})
    assert v is not None
    assert 0.0 < v <= 1.0
