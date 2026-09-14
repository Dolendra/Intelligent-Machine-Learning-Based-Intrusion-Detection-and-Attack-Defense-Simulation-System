"""High-level ingestion entrypoints for Stage-2."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ingestion.adapters import adapt_flows_csv, extract_flows_from_pcap, pcap_extractor_status
from ingestion.schema_info import schema_summary
from ingestion.validate import rows_as_feature_dicts


@dataclass
class IngestResult:
    ok: bool
    source: str
    flows: list[dict[str, float]] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    schema: dict[str, Any] = field(default_factory=dict)
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "source": self.source,
            "flow_count": len(self.flows),
            "flows": self.flows,
            "validation": self.validation,
            "schema": self.schema,
            "detail": self.detail,
        }


def ingest_flows_csv(
    content: str | bytes | Path,
    *,
    fill_missing: bool = False,
    max_rows: int = 500,
) -> IngestResult:
    aligned, validation = adapt_flows_csv(content, fill_missing=fill_missing)
    schema = schema_summary()
    if not validation.get("ok"):
        return IngestResult(
            ok=False,
            source="flows_csv",
            validation=validation,
            schema=schema,
            detail={"code": "SCHEMA_MISMATCH"},
        )
    if len(aligned) > max_rows:
        return IngestResult(
            ok=False,
            source="flows_csv",
            validation=validation,
            schema=schema,
            detail={"code": "TOO_MANY_ROWS", "max_rows": max_rows, "got": len(aligned)},
        )
    flows = rows_as_feature_dicts(aligned)
    return IngestResult(
        ok=True,
        source="flows_csv",
        flows=flows,
        validation=validation,
        schema=schema,
        detail={"code": "OK"},
    )


def ingest_pcap(pcap_path: Path, *, fill_missing: bool = False, max_rows: int = 500) -> IngestResult:
    schema = schema_summary()
    df, status = extract_flows_from_pcap(Path(pcap_path), fill_missing=fill_missing)
    if df is None:
        return IngestResult(
            ok=False,
            source="pcap",
            schema=schema,
            detail=status,
            validation=status.get("validation") or {"ok": False, "message": status.get("message", "pcap not processed")},
        )
    if len(df) > max_rows:
        return IngestResult(
            ok=False,
            source="pcap",
            schema=schema,
            detail={**status, "code": "TOO_MANY_ROWS", "max_rows": max_rows, "got": len(df)},
            validation=status.get("validation") or {"ok": True},
        )
    flows = rows_as_feature_dicts(df)
    return IngestResult(
        ok=True,
        source="pcap",
        flows=flows,
        schema=schema,
        detail={**status, "code": "OK"},
        validation=status.get("validation") or {"ok": True},
    )


def ingestion_capabilities() -> dict[str, Any]:
    from ingestion.queue import ingest_queue

    return {
        "stage": "2-phase-b",
        "baseline": "v1.1-research",
        "schema": schema_summary(),
        "flows_csv": {"available": True, "endpoint": "/api/ingest/flows/csv"},
        "pcap": pcap_extractor_status(),
        "queue": {
            "available": True,
            "endpoint": "/api/ingest/queue",
            "mode": "in_process",
            "status": ingest_queue.status(),
        },
        "notes": [
            "v1.1 research baseline remains frozen on MachineLearningCVE flow features.",
            "CSV alias normalization maps common CICFlowMeter abbreviations onto schema v1.1.",
            "PCAP extraction uses cicflowmeter when installed; otherwise fails safely (501).",
            "Phase B adds an in-process ingest→detect queue for batch staging and latency metrics.",
        ],
    }
