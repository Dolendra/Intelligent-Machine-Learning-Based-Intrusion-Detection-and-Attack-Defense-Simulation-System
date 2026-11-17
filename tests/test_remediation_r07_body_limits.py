"""R-07 (SEC-4): body-size limits hold for chunked / streamed bodies, not only Content-Length."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.main import app
from backend.middleware.request_limits import RequestSizeLimitMiddleware, limit_for_path

client = TestClient(app)
MB = 1024 * 1024
CRLF = "\r\n"


def _chunks(total: int, chunk: int = 64 * 1024, fill: bytes = b"a"):
    sent = 0
    while sent < total:
        n = min(chunk, total - sent)
        sent += n
        yield fill * n


def _code(r):
    return (r.json().get("detail") or {}).get("code")


def _multipart(field: str, filename: str, payload_iter):
    boundary = "aegisboundary"
    head = (f"--{boundary}{CRLF}"
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"{CRLF}'
            f"Content-Type: application/octet-stream{CRLF}{CRLF}").encode()

    def body():
        yield head
        yield from payload_iter
        yield f"{CRLF}--{boundary}--{CRLF}".encode()

    return body(), {"content-type": f"multipart/form-data; boundary={boundary}"}


def test_chunked_json_over_limit_is_rejected():
    r = client.patch("/api/incidents/INC-NOPE", content=_chunks(5 * MB),
                     headers={"content-type": "application/json"})
    assert r.status_code == 413 and _code(r) == "REQUEST_TOO_LARGE"


def test_chunked_pcap_multipart_over_limit_is_rejected_by_middleware():
    body, headers = _multipart("file", "x.pcap", _chunks(40 * MB, fill=b"\x00"))
    r = client.post("/api/ingest/pcap", content=body, headers=headers)
    # REQUEST_TOO_LARGE comes from the middleware; before R-07 the whole 40 MB was read and the
    # handler answered PCAP_TOO_LARGE.
    assert r.status_code == 413 and _code(r) == "REQUEST_TOO_LARGE"


def test_chunked_csv_multipart_over_limit_is_rejected():
    body, headers = _multipart("file", "x.csv", _chunks(40 * MB, fill=b"1,"))
    r = client.post("/api/predict/batch/csv", content=body, headers=headers)
    assert r.status_code == 413 and _code(r) == "REQUEST_TOO_LARGE"


def test_declared_content_length_over_limit_still_rejected_early():
    r = client.patch("/api/incidents/INC-NOPE", content=b"{" + b" " * (2 * MB) + b"}",
                     headers={"content-type": "application/json"})
    assert r.status_code == 413 and _code(r) == "REQUEST_TOO_LARGE"


def test_invalid_content_length_is_rejected():
    mini = FastAPI()

    @mini.post("/api/x")
    async def x():
        return {"ok": True}

    mini.add_middleware(RequestSizeLimitMiddleware, enabled=True)
    r = TestClient(mini).post("/api/x", content=b"{}", headers={"content-length": "-5",
                                                                "content-type": "application/json"})
    assert r.status_code == 400


def test_small_chunked_json_passes_through():
    r = client.patch("/api/incidents/INC-NOPE", content=_chunks(10, fill=b" "),
                     headers={"content-type": "application/json"})
    assert r.status_code != 413


def test_handler_never_sees_more_than_limit_plus_one_chunk():
    """Isolated app: the handler's read is cut off, so it cannot buffer the whole stream."""
    seen = {"bytes": 0}
    mini = FastAPI()

    @mini.post("/api/sink")
    async def sink(request: Request):
        async for part in request.stream():
            seen["bytes"] += len(part)
        return {"ok": True}

    mini.add_middleware(RequestSizeLimitMiddleware, enabled=True)
    limit = limit_for_path("/api/sink", "application/json")
    chunk = 64 * 1024
    r = TestClient(mini).post("/api/sink", content=_chunks(limit * 4, chunk=chunk),
                              headers={"content-type": "application/json"})
    assert r.status_code == 413
    assert seen["bytes"] <= limit + chunk
