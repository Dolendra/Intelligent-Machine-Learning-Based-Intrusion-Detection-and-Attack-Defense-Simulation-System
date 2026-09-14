"""P1 productionization: PCAP upload validation + API reject paths."""
from __future__ import annotations

import os

from fastapi.testclient import TestClient

from backend.main import app
from ingestion.audit import audit_ingest_event
from ingestion.pcap_validation import max_pcap_bytes, validate_pcap_upload

client = TestClient(app)


def _minimal_pcap_bytes() -> bytes:
    return b"\xd4\xc3\xb2\xa1" + b"\x02\x00\x04\x00" + b"\x00" * 16


def test_validate_pcap_accepts_classic_magic():
    ok = validate_pcap_upload(filename="a.pcap", content=_minimal_pcap_bytes())
    assert ok.ok is True
    assert ok.format_hint == "pcap"
    assert ok.sha256


def test_validate_pcap_rejects_bad_magic():
    bad = validate_pcap_upload(filename="a.pcap", content=b"PK\x03\x04" + b"\x00" * 20)
    assert bad.ok is False
    assert bad.code == "PCAP_BAD_MAGIC"


def test_validate_pcap_rejects_bad_extension():
    bad = validate_pcap_upload(filename="a.exe", content=_minimal_pcap_bytes())
    assert bad.ok is False
    assert bad.code == "PCAP_BAD_EXTENSION"


def test_validate_pcap_rejects_too_large(monkeypatch):
    monkeypatch.setenv("IDS_PCAP_MAX_BYTES", "64")
    # re-import path uses env at call time
    assert max_pcap_bytes() == 64
    blob = _minimal_pcap_bytes() + b"\x00" * 100
    bad = validate_pcap_upload(filename="big.pcap", content=blob)
    assert bad.ok is False
    assert bad.code == "PCAP_TOO_LARGE"


def test_api_rejects_bad_magic():
    r = client.post(
        "/api/ingest/pcap",
        files={"file": ("evil.pcap", b"not-a-pcap-file-header!!!!", "application/octet-stream")},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "PCAP_BAD_MAGIC"


def test_api_rejects_oversized(monkeypatch):
    monkeypatch.setenv("IDS_PCAP_MAX_BYTES", "40")
    blob = _minimal_pcap_bytes() + b"\x00" * 80
    r = client.post(
        "/api/ingest/pcap",
        files={"file": ("big.pcap", blob, "application/vnd.tcpdump.pcap")},
    )
    assert r.status_code == 413
    assert r.json()["detail"]["code"] == "PCAP_TOO_LARGE"


def test_audit_event_shape():
    evt = audit_ingest_event(
        event="pcap_rejected",
        source="pcap",
        request_id="t-1",
        filename="x.pcap",
        code="PCAP_BAD_MAGIC",
        size_bytes=10,
    )
    assert evt["event"] == "pcap_rejected"
    assert evt["baseline"] == "v1.1-research"
    assert "ts" in evt
