"""Submission polish: DEMO_MODE missing-feature gate on batch routes."""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

from backend.main import app
from backend.services import pipeline as svc

client = TestClient(app)


def test_batch_allow_missing_ignored_outside_demo_mode(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.setenv("DEMO_MODE", "false")
    # Incomplete vector should 422 when DEMO_MODE is off, even if flag requested
    r = client.post(
        "/api/predict/batch",
        json={"flows": [{"Destination Port": 80}], "allow_missing_features": True, "persist": False},
    )
    assert r.status_code in {422, 503}
    if r.status_code == 422:
        assert r.json()["detail"]["code"] in {"INVALID_FEATURES", "VALIDATION_ERROR", "INVALID_BATCH"}


def test_demo_allow_missing_helper():
    from backend.routes.api import _demo_allow_missing

    os.environ["DEMO_MODE"] = "false"
    assert _demo_allow_missing(True) is False
    os.environ["DEMO_MODE"] = "true"
    assert _demo_allow_missing(True) is True
    assert _demo_allow_missing(False) is False
    os.environ["DEMO_MODE"] = "false"
