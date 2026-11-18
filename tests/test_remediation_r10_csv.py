"""R-10 (ARCH-4, ML-13): one CSV parser for every upload path; raw MachineLearningCVE headers accepted."""
from __future__ import annotations

import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import pipeline as svc
from ingestion.schema_info import expected_feature_names

client = TestClient(app)
needs_models = pytest.mark.skipif(not svc.models_ready(), reason="frozen models required")


def _raw_cve_csv(n: int = 3) -> bytes:
    """Rows in the original MachineLearningCVE layout: leading-space headers and the duplicated
    ' Fwd Header Length' column (pandas would otherwise name it 'Fwd Header Length.1')."""
    tmpl = svc.sample_feature_template()
    feats = expected_feature_names()
    header = [" " + ("Fwd Header Length" if f == "Fwd Header Length.1" else f) for f in feats] + [" Label"]
    lines = [",".join(header)]
    for _ in range(n):
        lines.append(",".join(str(float(tmpl.get(f, 0.0))) for f in feats) + ",BENIGN")
    return ("\n".join(lines) + "\n").encode()


@needs_models
def test_raw_dataset_header_accepted_by_direct_parser():
    rows = svc.parse_flows_csv(_raw_cve_csv())
    assert len(rows) == 3 and set(rows[0]) == set(expected_feature_names())


@needs_models
@pytest.mark.parametrize("path,params", [
    ("/api/predict/batch/csv", {"persist": "false"}),
    ("/api/ingest/flows/csv", {"predict": "true", "persist": "false"}),
])
def test_every_csv_endpoint_accepts_raw_dataset_headers(path, params):
    r = client.post(path, params=params, files={"file": ("raw.csv", _raw_cve_csv(), "text/csv")})
    assert r.status_code == 200, r.text[:300]


@needs_models
def test_missing_columns_still_rejected_with_clear_message():
    df = pd.read_csv(io.BytesIO(_raw_cve_csv()))
    bad = df.drop(columns=[" Flow Duration"]).to_csv(index=False).encode()
    with pytest.raises(ValueError, match="missing 1 required feature"):
        svc.parse_flows_csv(bad)


@needs_models
def test_row_cap_enforced():
    with pytest.raises(ValueError, match="limited to 2 rows"):
        svc.parse_flows_csv(_raw_cve_csv(3), max_rows=2)
