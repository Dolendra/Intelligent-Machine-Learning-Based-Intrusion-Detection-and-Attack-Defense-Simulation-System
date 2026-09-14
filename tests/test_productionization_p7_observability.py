"""P7 observability — correlation, metrics, health/ready, redaction, ops snapshot."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.observability.alerts import evaluate_alerts
from backend.observability.context import bind_correlation, get_correlation, set_request_id
from backend.observability.events import log_event
from backend.observability.redact import redact_mapping
from backend.observability.registry import domain_metrics
from security.response.service import propose_action
from security.response.store import response_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_domain_metrics():
    domain_metrics.reset()
    response_store.clear()
    yield
    domain_metrics.reset()
    response_store.clear()


def test_request_id_propagated_on_response():
    r = client.get("/api/health", headers={"X-Request-ID": "req_test_p7_001"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "req_test_p7_001"


def test_structured_log_event_is_json():
    set_request_id("req_json_1")
    payload = log_event(
        "unit_test_event",
        endpoint="/api/test",
        method="GET",
        status=200,
        duration_ms=12.5,
        password="should-not-appear",
    )
    assert payload["event_type"] == "unit_test_event"
    assert payload["request_id"] == "req_json_1"
    assert payload["password"] == "[REDACTED]"
    assert payload["phase"] == "P7"
    # Must be JSON-serializable ops record
    line = json.dumps(payload, separators=(",", ":"))
    assert "should-not-appear" not in line
    assert json.loads(line)["duration_ms"] == 12.5


def test_sensitive_field_redaction():
    raw = {
        "username": "analyst",
        "password": "ChangeMe!",
        "Authorization": "Bearer super-secret-token",
        "nested": {"api_key": "abc", "ok": 1},
    }
    clean = redact_mapping(raw)
    assert clean["password"] == "[REDACTED]"
    assert clean["Authorization"] == "[REDACTED]"
    assert clean["nested"]["api_key"] == "[REDACTED]"
    assert clean["nested"]["ok"] == 1
    assert clean["username"] == "analyst"


def test_correlation_bind():
    with bind_correlation(request_id="r1", job_id="j1", incident_id="INC-1", action_id="ra-1"):
        c = get_correlation()
        assert c["request_id"] == "r1"
        assert c["job_id"] == "j1"
        assert c["incident_id"] == "INC-1"
        assert c["action_id"] == "ra-1"


def test_metrics_increments_on_request_and_validation():
    before = domain_metrics.snapshot()["api"]["requests_total"]
    client.get("/api/health")
    after = domain_metrics.snapshot()["api"]["requests_total"]
    assert after >= before + 1

    client.post("/api/response/actions/propose", json={"attack_type": 123})
    assert domain_metrics.snapshot()["security"]["validation_failures"] >= 1


def test_response_metrics_on_propose():
    before = domain_metrics.snapshot()["response"]["actions_proposed"]
    propose_action(attack_type="DDoS", source_ip="1.2.3.4")
    assert domain_metrics.snapshot()["response"]["actions_proposed"] >= before + 1


def test_health_is_liveness():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_reports_dependencies():
    r = client.get("/api/ready")
    # Models may or may not be present in CI — either 200 ready or 503 NOT_READY
    if r.status_code == 200:
        body = r.json()
        assert body["ready"] is True
        assert "dependencies" in body
        assert body["dependencies"]["database"]["status"] == "ok"
        # No filesystem paths leaked
        blob = json.dumps(body)
        assert "trained_models" not in blob or "models/trained" not in blob
    else:
        assert r.status_code == 503
        detail = r.json()["detail"]
        assert detail["code"] == "NOT_READY"
        assert "missing" in detail
        assert "traceback" not in json.dumps(detail).lower()


def test_ops_status_shape():
    r = client.get("/api/ops/status")
    assert r.status_code == 200
    body = r.json()
    assert body["phase"] == "P7"
    assert body["prometheus"] is False
    assert "dependencies" in body
    assert "performance" in body
    assert "security" in body
    assert "response" in body
    assert "alerts" in body
    assert "retention" in body


def test_metrics_includes_domain():
    r = client.get("/api/metrics")
    assert r.status_code == 200
    body = r.json()
    assert body["phase"] == "P7"
    assert "domain" in body
    assert body["domain"]["phase"] == "P7"


def test_security_status_observability_p7():
    r = client.get("/api/security/status")
    assert r.status_code == 200
    obs = r.json()["observability"]
    assert obs["phase"] == "P7"
    assert obs["ops_endpoint"] == "/api/ops/status"
    assert obs["structured_json_logs"] is True
    assert obs["prometheus"] is False


def test_alert_evaluation_database_down():
    alerts = evaluate_alerts(
        deps={"database": {"status": "unavailable"}, "models": {"status": "ok"}, "queue": {"status": "ok", "depth": 0}},
        http_metrics={"requests_total": 100, "errors_5xx": 1},
        domain={"security": {}, "pcap": {}, "response": {}},
    )
    assert any(a["id"] == "database_unavailable" for a in alerts)


def test_alert_queue_backlog():
    alerts = evaluate_alerts(
        deps={"database": {"status": "ok"}, "models": {"status": "ok"}, "queue": {"status": "ok", "depth": 90}},
        http_metrics={"requests_total": 10, "errors_5xx": 0},
        domain={"security": {}, "pcap": {}, "response": {}},
        queue_depth=90,
    )
    assert any(a["id"] == "queue_backlog_critical" for a in alerts)


def test_no_secret_in_ops_or_ready():
    for path in ("/api/ops/status", "/api/ready", "/api/metrics"):
        r = client.get(path)
        text = r.text.lower()
        assert "changeme" not in text
        assert "bearer " not in text
        assert "password" not in text or "[redacted]" in text
