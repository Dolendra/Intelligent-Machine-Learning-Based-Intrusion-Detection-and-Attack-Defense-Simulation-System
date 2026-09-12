"""Unit tests for calibration helpers and PDF export."""
import os

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np
from fastapi.testclient import TestClient

from backend.main import app
from ml.evaluation.calibration import calibration_report, expected_calibration_error

client = TestClient(app)


def test_ece_perfectly_calibrated():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.0, 0.0, 1.0, 1.0])
    assert expected_calibration_error(y, p, n_bins=2) == 0.0


def test_calibration_report_keys():
    rng = np.random.RandomState(0)
    y = rng.randint(0, 2, size=200)
    p = rng.rand(200)
    report = calibration_report(y, p, n_bins=5)
    assert "brier_score" in report
    assert "ece" in report
    assert 0.0 <= report["ece"] <= 1.0


def test_pdf_export():
    r = client.get("/api/export/report.pdf")
    assert r.status_code == 200
    assert "pdf" in r.headers.get("content-type", "")
    assert r.content[:4] == b"%PDF"
