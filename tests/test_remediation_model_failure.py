"""P1-A7: model loading and failure handling (frozen v1.1 predictor)."""
from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.observability import health_checks
from backend.services import pipeline as svc
from ml.prediction.predictor import IDSPredictor

client = TestClient(app)
needs_models = pytest.mark.skipif(not svc.models_ready(), reason="frozen models required")


@pytest.fixture
def corrupt_models(monkeypatch):
    svc.get_predictor.cache_clear()

    def boom(*a, **k):
        raise EOFError("truncated joblib")

    monkeypatch.setattr(IDSPredictor, "from_artifacts", classmethod(lambda cls, *a, **k: boom()))
    yield
    monkeypatch.undo()
    svc.get_predictor.cache_clear()


@needs_models
def test_corrupt_artifacts_give_503_not_500(corrupt_models, caplog):
    feats = {k: float(v) for k, v in svc.sample_feature_template().items()}
    with caplog.at_level(logging.ERROR, logger="aegis.models"):
        r = client.post("/api/predict", json={"features": feats, "persist": False})
    assert r.status_code == 503, r.text[:200]
    assert any("frozen model load failed" in rec.getMessage() for rec in caplog.records)


@needs_models
def test_corrupt_artifacts_make_readiness_fail(corrupt_models):
    rep = health_checks.readiness_report()
    assert rep["ready"] is False and "models" in rep["missing"]


@needs_models
def test_recovers_after_artifacts_are_fixed(corrupt_models, monkeypatch):
    assert svc.get_predictor() is None
    monkeypatch.undo()                                   # "artifacts restored"
    assert svc.get_predictor() is not None               # no restart needed
