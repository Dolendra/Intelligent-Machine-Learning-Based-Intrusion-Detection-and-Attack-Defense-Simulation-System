"""R-04 (ARCH-10, ML-22): Zero-Day Gate failures are visible, isolated per row, and not cached forever."""
from __future__ import annotations

import logging

import pytest

import research.serving as serving
from backend.observability import health_checks
from backend.services import pipeline as svc


class _FlakyGate:
    """Fails on any batch containing a row marked bad; scores other rows."""

    def assess(self, rows, explain_top=5, alpha=None):
        if any(r.get("bad") for r in rows):
            raise ValueError("missing features")
        return [{"alert": False, "label": "BENIGN", "p_value": 0.5} for _ in rows]


def test_one_bad_row_does_not_nullify_the_batch(monkeypatch, caplog):
    monkeypatch.setattr(serving, "get_gate", lambda: _FlakyGate())
    rows = [{"a": 1.0}, {"bad": True}, {"a": 2.0}]
    with caplog.at_level(logging.WARNING, logger="aegis.zero_day"):
        res, status = svc.zero_day_assessment_with_status(rows)
    assert status == ["ok", "error", "ok"]
    assert res[0] is not None and res[1] is None and res[2] is not None
    assert any("zero_day_gate_row_error" in r.getMessage() for r in caplog.records)


def test_unavailable_gate_is_reported_not_silent(monkeypatch, caplog):
    monkeypatch.setattr(serving, "get_gate", lambda: None)
    monkeypatch.setattr(serving, "gate_error", lambda: "artifacts not found")
    with caplog.at_level(logging.WARNING, logger="aegis.zero_day"):
        res, status = svc.zero_day_assessment_with_status([{"a": 1.0}])
    assert res == [None] and status == ["unavailable"]
    assert any("zero_day_gate_unavailable" in r.getMessage() for r in caplog.records)


def test_backwards_compatible_wrapper(monkeypatch):
    monkeypatch.setattr(serving, "get_gate", lambda: _FlakyGate())
    assert len(svc.zero_day_assessment([{"a": 1.0}, {"bad": True}])) == 2


@pytest.mark.parametrize("policy,required", [("frozen", False), ("union", True), ("gate", True)])
def test_readiness_requires_gate_only_when_policy_uses_it(monkeypatch, policy, required):
    import security.detection_policy as dp

    monkeypatch.setattr(dp, "configured_policy", lambda: policy)
    monkeypatch.setattr(serving, "get_gate", lambda: None)
    rep = health_checks.readiness_report()
    assert rep["dependencies"]["zero_day_gate"]["status"] == "unavailable"
    assert ("zero_day_gate" in rep["missing"]) is required
    if required:
        assert rep["ready"] is False


def test_failed_gate_load_is_retried_after_cooldown(monkeypatch):
    calls = {"n": 0}

    class Boom:
        def __init__(self):
            calls["n"] += 1
            raise FileNotFoundError("nope")

    monkeypatch.setattr(serving, "_gate", None)
    monkeypatch.setattr(serving, "_gate_error", None)
    monkeypatch.setattr(serving, "ZeroDayGate", Boom)
    assert serving.get_gate() is None and calls["n"] == 1
    assert serving.get_gate() is None and calls["n"] == 1            # within cool-down: no retry
    monkeypatch.setattr(serving, "_gate_error_at", serving._gate_error_at - serving.RETRY_SECONDS - 1)
    assert serving.get_gate() is None and calls["n"] == 2            # retried after cool-down
    monkeypatch.setattr(serving, "_gate_error", None)


def test_missing_predictor_is_not_cached(monkeypatch, tmp_path):
    svc.get_predictor.cache_clear()
    real = svc.resolve_path

    monkeypatch.setattr(svc, "resolve_path", lambda p: tmp_path)       # no artifacts there
    assert svc.get_predictor() is None
    monkeypatch.setattr(svc, "resolve_path", real)                     # artifacts "restored"
    restored = svc.get_predictor()
    if (real(svc.load_config()["models"]["output_dir"]) / "binary_best.joblib").exists():
        assert restored is not None
