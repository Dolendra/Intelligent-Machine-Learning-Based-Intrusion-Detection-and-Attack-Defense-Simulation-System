"""Stage-2 Phase B ingest queue tests."""
from __future__ import annotations

import io
import time

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from ingestion.queue import IngestDetectQueue
from ingestion.schema_info import expected_feature_names

client = TestClient(app)


def test_queue_processes_job_with_mock_predict():
    q = IngestDetectQueue(max_jobs=10, history=10)

    def _predict(flows):
        time.sleep(0.01)
        return {
            "total_flows": len(flows),
            "attack_flows": 0,
            "benign_flows": len(flows),
            "attack_percentage": 0.0,
        }

    q.set_predict_fn(_predict)
    q.start()
    names = expected_feature_names()
    job = q.submit([{n: 0.0 for n in names}], source="unit")
    deadline = time.time() + 2
    while time.time() < deadline:
        cur = q.get(job.job_id)
        assert cur is not None
        if cur.status in {"done", "error"}:
            break
        time.sleep(0.02)
    cur = q.get(job.job_id)
    assert cur is not None
    assert cur.status == "done"
    assert cur.latency_ms is not None and cur.latency_ms >= 0
    status = q.status()
    assert status["metrics"]["completed"] >= 1
    assert status["metrics"]["flows_processed"] >= 1
    q.stop()


def test_queue_api_submit_and_poll():
    names = expected_feature_names()
    buf = io.BytesIO(pd.DataFrame([{n: 0.0 for n in names}]).to_csv(index=False).encode("utf-8"))
    r = client.post("/api/ingest/queue/submit", files={"file": ("flows.csv", buf, "text/csv")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    job_id = body["job"]["job_id"]

    deadline = time.time() + 15
    final = None
    while time.time() < deadline:
        jr = client.get(f"/api/ingest/queue/{job_id}")
        assert jr.status_code == 200
        final = jr.json()
        if final["status"] in {"done", "error"}:
            break
        time.sleep(0.05)
    assert final is not None
    assert final["status"] == "done", final
    assert final["result_summary"]["total_flows"] == 1

    st = client.get("/api/ingest/queue")
    assert st.status_code == 200
    assert "metrics" in st.json()


def test_capabilities_reports_phase_b_queue():
    r = client.get("/api/ingest/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "2-phase-b"
    assert body["queue"]["available"] is True
