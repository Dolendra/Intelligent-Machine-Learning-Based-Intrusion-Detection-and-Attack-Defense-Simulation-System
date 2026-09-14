"""P1 close-out: PCAP fixtures + queue wiring (CI without system cicflowmeter)."""
from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from ingestion.pcap_validation import validate_pcap_upload
from ingestion.pipeline import ingest_flows_csv
from ingestion.schema_info import expected_feature_names

client = TestClient(app)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pcap"
MINIMAL_PCAP = FIXTURES / "minimal.pcap"
GOLDEN_CSV = FIXTURES / "golden_flows.csv"


def test_fixture_files_exist():
    assert MINIMAL_PCAP.is_file()
    assert GOLDEN_CSV.is_file()
    assert MINIMAL_PCAP.stat().st_size >= 24


def test_minimal_pcap_passes_validation():
    raw = MINIMAL_PCAP.read_bytes()
    check = validate_pcap_upload(filename="minimal.pcap", content=raw)
    assert check.ok is True
    assert check.format_hint == "pcap"


def test_golden_csv_aligns_to_schema():
    result = ingest_flows_csv(GOLDEN_CSV.read_bytes(), fill_missing=False, max_rows=10)
    assert result.ok is True
    assert len(result.flows) == 1
    assert set(result.flows[0]) == set(expected_feature_names())


def test_queue_submit_pcap_returns_501_without_extractor():
    """Honest capability: do not fake extraction when cicflowmeter is absent."""
    r = client.post(
        "/api/ingest/queue/submit-pcap",
        files={"file": ("minimal.pcap", MINIMAL_PCAP.read_bytes(), "application/vnd.tcpdump.pcap")},
    )
    assert r.status_code == 501
    detail = r.json()["detail"]
    assert detail["code"] in {"PCAP_EXTRACTOR_NOT_CONFIGURED", "PCAP_EXTRACTOR_NOT_WIRED", "PCAP_NOT_AVAILABLE"}


def test_queue_submit_pcap_mocked_extract_reuses_detect_queue(monkeypatch):
    """Mock only cicflowmeter output → same queue worker as CSV."""

    def _fake_run(pcap_path, out_csv=None, *, timeout_s: int = 300):
        dest = Path(tempfile.mkdtemp(prefix="aegis_golden_")) / "flows.csv"
        shutil.copyfile(GOLDEN_CSV, dest)
        return dest, {
            "code": "OK",
            "available": True,
            "cmd": ["mock-cicflowmeter"],
            "csv": str(dest),
        }

    monkeypatch.setattr("ingestion.cicflowmeter_runner.run_cicflowmeter", _fake_run)
    # adapters imports run_cicflowmeter by name at call time from module — patch both
    monkeypatch.setattr("ingestion.adapters.run_cicflowmeter", _fake_run)

    r = client.post(
        "/api/ingest/queue/submit-pcap",
        files={"file": ("minimal.pcap", MINIMAL_PCAP.read_bytes(), "application/vnd.tcpdump.pcap")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["job"]["source"] == "pcap_upload"
    job_id = body["job"]["job_id"]

    deadline = time.time() + 20
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
    assert final["source"] == "pcap_upload"
    assert final["result_summary"]["total_flows"] == 1


def test_capabilities_lists_pcap_queue_submit():
    r = client.get("/api/ingest/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert "pcap" in body["queue"]["accepts"]
    assert body["queue"]["submit_pcap"] == "/api/ingest/queue/submit-pcap"
