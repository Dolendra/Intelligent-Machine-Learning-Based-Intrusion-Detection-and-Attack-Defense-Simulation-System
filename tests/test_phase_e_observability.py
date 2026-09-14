"""Stage-2 Phase E: in-process metrics + observability contract."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.middleware.metrics_mw import process_metrics

client = TestClient(app)


def test_metrics_endpoint_shape():
    # Generate at least one recorded request
    client.get("/api/health")
    r = client.get("/api/metrics")
    assert r.status_code == 200
    body = r.json()
    assert body["scope"] == "single_process"
    assert body["resets_on_restart"] is True
    assert "requests_total" in body
    assert "p95_latency_ms" in body
    assert body["requests_total"] >= 1


def test_security_status_phase_e_observability():
    r = client.get("/api/security/status")
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "2-phase-f"
    assert body["observability"]["metrics_endpoint"] == "/api/metrics"
    assert body["observability"]["prometheus"] is False
    assert body["controlled_response"]["live_mitigation"] is False


def test_metrics_middleware_records(monkeypatch):
    before = process_metrics.snapshot()["requests_total"]
    client.get("/api/ready")
    after = process_metrics.snapshot()["requests_total"]
    assert after >= before + 1
