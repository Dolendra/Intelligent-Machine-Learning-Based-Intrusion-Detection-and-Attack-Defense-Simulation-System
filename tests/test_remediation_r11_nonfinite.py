"""R-11 (ML-8): one documented policy for NaN / Infinity / non-numeric feature values.

* JSON requests (/predict, /predict/batch, /explain, /zero-day/assess): 422, never a 500.
* CSV / PCAP-derived files: offending rows are rejected with their line number; other rows are
  scored (training also dropped non-finite rows). A file with no valid row is rejected.
"""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import pipeline as svc
from ingestion.schema_info import expected_feature_names
from ingestion.validate import align_dataframe

client = TestClient(app)
needs_models = pytest.mark.skipif(not svc.models_ready(), reason="frozen models required")


def _features() -> dict:
    return {k: float(v) for k, v in svc.sample_feature_template().items()}


def _json_body_with(value: str, key: str = "Flow Bytes/s") -> str:
    import json

    feats = _features()
    body = json.dumps({"features": feats, "persist": False})
    return body.replace(f'"{key}": {json.dumps(feats[key])}', f'"{key}": {value}')


@needs_models
@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity"])
def test_predict_json_non_finite_is_422_not_500(bad):
    r = client.post("/api/predict", content=_json_body_with(bad), headers={"content-type": "application/json"})
    assert r.status_code == 422, r.text[:200]


@needs_models
def test_batch_and_assess_json_non_finite_is_422():
    import json

    feats = _features()
    body = json.dumps({"flows": [feats], "persist": False}).replace(
        f'"Flow Duration": {json.dumps(feats["Flow Duration"])}', '"Flow Duration": Infinity')
    assert client.post("/api/predict/batch", content=body, headers={"content-type": "application/json"}).status_code == 422
    assert client.post("/api/zero-day/assess", content=body.replace('"persist": false', '"alpha": 0.01'),
                       headers={"content-type": "application/json"}).status_code == 422


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=expected_feature_names())


def test_csv_row_with_infinity_is_rejected_individually():
    good = {k: 1.0 for k in expected_feature_names()}
    bad = dict(good, **{"Flow Bytes/s": float("inf")})
    aligned, res = align_dataframe(_frame([good, bad, good]))
    assert res.ok and res.rows_in == 3 and res.rows_valid == 2 and len(aligned) == 2
    assert res.rejected_rows == [{"row": 3, "reason": "non-finite or non-numeric value",
                                  "columns": ["Flow Bytes/s"]}]


def test_csv_with_no_valid_row_is_rejected():
    good = {k: 1.0 for k in expected_feature_names()}
    aligned, res = align_dataframe(_frame([dict(good, **{"Flow Duration": float("nan")})]))
    assert not res.ok and res.rows_valid == 0 and "no valid rows" in res.message


@needs_models
def test_csv_upload_scores_good_rows_and_reports_bad_ones():
    feats = expected_feature_names()
    tmpl = _features()
    lines = [",".join(feats)]
    for i in range(3):
        vals = [str(tmpl[f]) for f in feats]
        if i == 1:
            vals[feats.index("Flow Bytes/s")] = "Infinity"
        lines.append(",".join(vals))
    r = client.post("/api/predict/batch/csv", params={"persist": "false"},
                    files={"file": ("x.csv", ("\n".join(lines) + "\n").encode(), "text/csv")})
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body["ingest_validation"]["rows_valid"] == 2
    assert body["ingest_validation"]["rejected_rows"][0]["row"] == 3
