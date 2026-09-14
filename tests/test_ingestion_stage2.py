"""Stage-2 ingestion schema + CSV adapter tests."""
from __future__ import annotations

import io

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from ingestion.pipeline import ingest_flows_csv, ingestion_capabilities
from ingestion.schema_info import expected_feature_names, schema_summary

client = TestClient(app)


def test_schema_summary_has_version_and_78_features():
    summary = schema_summary()
    assert summary["schema_version"] == "1.1.0"
    assert summary["feature_count"] == 78
    names = expected_feature_names()
    assert len(names) == 78
    assert "Destination Port" in names
    assert "Flow Duration" in names


def test_ingest_capabilities_endpoint():
    r = client.get("/api/ingest/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "2-phase-a"
    assert body["schema"]["schema_version"] == "1.1.0"
    assert body["flows_csv"]["available"] is True
    assert "pcap" in body


def test_ingest_flows_csv_roundtrip():
    names = expected_feature_names()
    row = {n: 1.0 for n in names}
    csv = pd.DataFrame([row]).to_csv(index=False)
    result = ingest_flows_csv(csv)
    assert result.ok is True
    assert len(result.flows) == 1
    assert set(result.flows[0]) == set(names)


def test_ingest_flows_csv_rejects_missing_columns():
    csv = "Destination Port,Flow Duration\n80,1\n"
    result = ingest_flows_csv(csv)
    assert result.ok is False
    assert result.detail.get("code") == "SCHEMA_MISMATCH"


def test_ingest_flows_csv_api():
    names = expected_feature_names()
    buf = io.BytesIO(pd.DataFrame([{n: 0.0 for n in names}]).to_csv(index=False).encode("utf-8"))
    r = client.post(
        "/api/ingest/flows/csv",
        files={"file": ("flows.csv", buf, "text/csv")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["flow_count"] == 1
    assert body["schema"]["schema_version"] == "1.1.0"


def test_ingest_pcap_returns_not_implemented():
    r = client.post(
        "/api/ingest/pcap",
        files={"file": ("sample.pcap", b"\xd4\xc3\xb2\xa1not-a-real-pcap", "application/vnd.tcpdump.pcap")},
    )
    assert r.status_code == 501
    detail = r.json()["detail"]
    assert detail["code"] in {"PCAP_EXTRACTOR_NOT_CONFIGURED", "PCAP_EXTRACTOR_NOT_WIRED", "PCAP_NOT_AVAILABLE"}
