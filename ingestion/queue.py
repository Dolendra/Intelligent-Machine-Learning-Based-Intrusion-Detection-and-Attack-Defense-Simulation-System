"""In-process ingest→detect queue (Stage-2 Phase B prototype — not distributed)."""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable


PredictFn = Callable[[list[dict[str, float]]], dict[str, Any]]


@dataclass
class QueueJob:
    job_id: str
    source: str
    flows: list[dict[str, float]]
    created_at: float = field(default_factory=time.time)
    status: str = "queued"  # queued | running | done | error
    started_at: float | None = None
    finished_at: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    @property
    def latency_ms(self) -> float | None:
        if self.started_at is None or self.finished_at is None:
            return None
        return round((self.finished_at - self.started_at) * 1000.0, 3)

    @property
    def wait_ms(self) -> float | None:
        if self.started_at is None:
            return None
        return round((self.started_at - self.created_at) * 1000.0, 3)

    def as_dict(self, *, include_flows: bool = False) -> dict[str, Any]:
        payload = {
            "job_id": self.job_id,
            "source": self.source,
            "status": self.status,
            "flow_count": len(self.flows),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "wait_ms": self.wait_ms,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "result_summary": None,
        }
        if self.result is not None:
            payload["result_summary"] = {
                "total_flows": self.result.get("total_flows"),
                "attack_flows": self.result.get("attack_flows"),
                "benign_flows": self.result.get("benign_flows"),
                "attack_percentage": self.result.get("attack_percentage"),
            }
        if include_flows:
            payload["flows"] = self.flows
            payload["result"] = self.result
        return payload


class IngestDetectQueue:
    """Single-worker FIFO queue for offline/batch flow detection."""

    def __init__(self, *, max_jobs: int = 100, history: int = 50) -> None:
        self._max_jobs = max_jobs
        self._history = history
        self._cv = threading.Condition()
        self._pending: deque[str] = deque()
        self._jobs: dict[str, QueueJob] = {}
        self._done: deque[str] = deque(maxlen=history)
        self._predict_fn: PredictFn | None = None
        self._worker: threading.Thread | None = None
        self._stop = False
        self._metrics = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "flows_processed": 0,
            "total_detect_ms": 0.0,
        }

    def set_predict_fn(self, fn: PredictFn | None) -> None:
        with self._cv:
            self._predict_fn = fn

    def start(self) -> None:
        with self._cv:
            if self._worker and self._worker.is_alive():
                return
            self._stop = False
            self._worker = threading.Thread(target=self._loop, name="aegis-ingest-queue", daemon=True)
            self._worker.start()

    def stop(self, *, wait: bool = False) -> None:
        with self._cv:
            self._stop = True
            self._cv.notify_all()
            worker = self._worker
        if wait and worker is not None:
            worker.join(timeout=5)

    def submit(self, flows: list[dict[str, float]], *, source: str = "api") -> QueueJob:
        if not flows:
            raise ValueError("flows must be non-empty")
        with self._cv:
            if len(self._pending) >= self._max_jobs:
                raise RuntimeError("ingest queue is full")
            job = QueueJob(job_id=str(uuid.uuid4()), source=source, flows=list(flows))
            self._jobs[job.job_id] = job
            self._pending.append(job.job_id)
            self._metrics["submitted"] += 1
            self._cv.notify()
            return job

    def get(self, job_id: str) -> QueueJob | None:
        with self._cv:
            return self._jobs.get(job_id)

    def status(self) -> dict[str, Any]:
        with self._cv:
            completed = self._metrics["completed"]
            detect_ms = self._metrics["total_detect_ms"]
            flows = self._metrics["flows_processed"]
            avg_detect = (detect_ms / completed) if completed else None
            avg_per_flow = (detect_ms / flows) if flows else None
            return {
                "mode": "in_process",
                "worker_alive": bool(self._worker and self._worker.is_alive()),
                "queued": len(self._pending),
                "tracked_jobs": len(self._jobs),
                "max_jobs": self._max_jobs,
                "metrics": {
                    **self._metrics,
                    "avg_detect_latency_ms": None if avg_detect is None else round(avg_detect, 3),
                    "avg_ms_per_flow": None if avg_per_flow is None else round(avg_per_flow, 3),
                    "approx_flows_per_sec": None if not avg_per_flow else round(1000.0 / avg_per_flow, 3),
                },
                "recent_job_ids": list(self._done)[-10:],
                "notes": [
                    "Prototype in-process queue only — not Redis/Kafka/distributed workers.",
                    "Use for offline batch staging and latency measurement on a single API process.",
                ],
            }

    def _loop(self) -> None:
        while True:
            with self._cv:
                while not self._pending and not self._stop:
                    self._cv.wait(timeout=0.5)
                if self._stop and not self._pending:
                    return
                if not self._pending:
                    continue
                job_id = self._pending.popleft()
                job = self._jobs[job_id]
                predict_fn = self._predict_fn
                job.status = "running"
                job.started_at = time.time()

            try:
                if predict_fn is None:
                    raise RuntimeError("predict function not configured")
                result = predict_fn(job.flows)
                with self._cv:
                    job.result = result
                    job.status = "done"
                    job.finished_at = time.time()
                    self._metrics["completed"] += 1
                    self._metrics["flows_processed"] += len(job.flows)
                    if job.latency_ms is not None:
                        self._metrics["total_detect_ms"] += job.latency_ms
                    self._done.append(job.job_id)
            except Exception as exc:  # noqa: BLE001
                with self._cv:
                    job.status = "error"
                    job.error = str(exc)
                    job.finished_at = time.time()
                    self._metrics["failed"] += 1
                    self._done.append(job.job_id)


# Process-wide singleton for the API
ingest_queue = IngestDetectQueue()
