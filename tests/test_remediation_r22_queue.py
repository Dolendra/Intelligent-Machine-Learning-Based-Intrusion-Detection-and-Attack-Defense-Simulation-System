"""R-22 (ARCH-9): the ingest queue keeps bounded storage and its detections are retrievable."""
from __future__ import annotations

import time

from ingestion.queue import IngestDetectQueue


def _fake_predict(flows):
    return {"total_flows": len(flows), "attack_flows": 1, "benign_flows": len(flows) - 1,
            "attack_percentage": 100.0 / len(flows), "items": [{"flow_index": i, "is_attack": i == 0}
                                                                for i in range(len(flows))]}


def _wait(q, job_ids, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        if all((j := q.get(i)) is None or j.status in ("done", "error") for i in job_ids):
            return
        time.sleep(0.02)
    raise AssertionError("queue did not drain")


def test_finished_jobs_are_bounded():
    q = IngestDetectQueue(max_jobs=500, history=5)
    q.set_predict_fn(_fake_predict)
    q.start()
    try:
        ids = [q.submit([{"a": 1.0}, {"a": 2.0}]).job_id for _ in range(40)]
        _wait(q, ids)
        st = q.status()
        assert st["tracked_jobs"] <= 5                      # was 40 (never evicted)
        assert q.get(ids[0]) is None and q.get(ids[-1]) is not None
        assert st["metrics"]["flows_processed"] == 80
    finally:
        q.stop(wait=True)


def test_results_are_retrievable_and_inputs_released():
    q = IngestDetectQueue(history=5)
    q.set_predict_fn(_fake_predict)
    q.start()
    try:
        job = q.submit([{"a": 1.0}, {"a": 2.0}, {"a": 3.0}])
        _wait(q, [job.job_id])
        d = q.get(job.job_id).as_dict(include_results=True)
        assert d["status"] == "done" and d["flow_count"] == 3
        assert len(d["result"]["items"]) == 3 and d["result"]["items"][0]["is_attack"] is True
        assert q.get(job.job_id).flows == []                # input flows not retained
        assert "result" not in q.get(job.job_id).as_dict()  # summary-only by default
    finally:
        q.stop(wait=True)


def test_api_route_returns_results_on_request():
    from fastapi.testclient import TestClient

    from backend.main import app
    from ingestion.queue import QueueJob, ingest_queue

    job = QueueJob(job_id="r22-job", source="test", flows=[{"a": 1.0}])
    job.status, job.result = "done", _fake_predict([{"a": 1.0}])
    with ingest_queue._cv:
        ingest_queue._jobs[job.job_id] = job
    c = TestClient(app)
    assert "result" not in c.get("/api/ingest/queue/r22-job").json()
    assert c.get("/api/ingest/queue/r22-job", params={"include_results": True}).json()["result"]["total_flows"] == 1
    with ingest_queue._cv:
        ingest_queue._jobs.pop(job.job_id, None)
