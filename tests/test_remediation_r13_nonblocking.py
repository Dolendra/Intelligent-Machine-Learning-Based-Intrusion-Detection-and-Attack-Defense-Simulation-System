"""R-13 (ARCH-7 / SEC-9): slow upload processing no longer blocks the event loop."""
from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from backend.main import app

CRLF = "\r\n"


def _multipart(filename: str, payload: bytes):
    b = "r13boundary"
    body = (f"--{b}{CRLF}Content-Disposition: form-data; name=\"file\"; filename=\"{filename}\"{CRLF}"
            f"Content-Type: application/octet-stream{CRLF}{CRLF}").encode() + payload + f"{CRLF}--{b}--{CRLF}".encode()
    return body, {"content-type": f"multipart/form-data; boundary={b}"}


@pytest.mark.parametrize("path,target", [
    ("/api/ingest/flows/csv", "ingestion.pipeline.ingest_flows_csv"),
    ("/api/predict/batch/csv", "backend.services.pipeline.parse_flows_csv_detailed"),
])
def test_health_stays_responsive_during_slow_upload(monkeypatch, path, target):
    """A 2-second blocking parse used to freeze every other request for its whole duration."""
    mod, name = target.rsplit(".", 1)
    import importlib

    module = importlib.import_module(mod)

    def slow(*a, **k):
        time.sleep(2.0)
        raise ValueError("stub: slow parse")

    monkeypatch.setattr(module, name, slow)

    async def scenario():
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            body, headers = _multipart("x.csv", b"a,b\n1,2\n")
            t0 = time.perf_counter()
            upload = asyncio.create_task(c.post(path, content=body, headers=headers))
            await asyncio.sleep(0.2)                      # the upload is now inside the slow parse
            r = await c.get("/api/health")
            # If the parse blocks the loop, neither the sleep nor /health can finish before it
            # ends (~2 s). Off-loop, /health completes ~0.2 s after the upload started.
            health_done = time.perf_counter() - t0
            await upload
            return r.status_code, health_done

    status, latency = asyncio.run(scenario())
    assert status == 200
    assert latency < 1.2, f"/api/health finished {latency:.2f}s after the upload started (blocked)"
