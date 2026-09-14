"""Adapters that produce CICIDS2017-compatible feature frames."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.cicflowmeter_runner import dataframe_from_cicflowmeter_csv, run_cicflowmeter
from ingestion.normalize import normalize_flow_frame
from ingestion.validate import align_dataframe


def load_machinelearningcve_csv(content: str | bytes | Path) -> pd.DataFrame:
    """Load a MachineLearningCVE-style flow CSV into a DataFrame."""
    if isinstance(content, Path):
        text = content.read_text(encoding="utf-8-sig")
    elif isinstance(content, (bytes, bytearray)):
        text = content.decode("utf-8-sig")
    else:
        text = content
    return pd.read_csv(io.StringIO(text))


def adapt_flows_csv(content: str | bytes | Path, *, fill_missing: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]:
    df = load_machinelearningcve_csv(content)
    normalized = normalize_flow_frame(df)
    aligned, result = align_dataframe(normalized, fill_missing=fill_missing)
    info = result.as_dict()
    info["normalized"] = True
    return aligned, info


def pcap_extractor_status() -> dict[str, Any]:
    """Report whether an external PCAP→flow tool is available."""
    import shutil

    tools = {
        "cicflowmeter": bool(shutil.which("cicflowmeter")),
        "zeek": bool(shutil.which("zeek") or shutil.which("bro")),
        "tshark": bool(shutil.which("tshark")),
    }
    available = any(tools.values())
    return {
        "available": available,
        "tools": tools,
        "status": "ready" if tools["cicflowmeter"] else ("partial" if available else "not_configured"),
        "message": (
            "cicflowmeter detected — PCAP→CSV extraction enabled."
            if tools["cicflowmeter"]
            else (
                "Optional tools found, but cicflowmeter adapter is the supported Stage-2 path."
                if available
                else "No PCAP flow extractor installed. Use MachineLearningCVE-compatible CSV upload, "
                "or install CICFlowMeter (`cicflowmeter` on PATH) and retry."
            )
        ),
        "recommended": "CICFlowMeter export aligned to schema cicids2017_v1_1",
        "cli": "python -m ingestion pcap -i capture.pcap --align",
    }


def extract_flows_from_pcap(pcap_path: Path, *, fill_missing: bool = False) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    """Attempt PCAP→flows via cicflowmeter when available."""
    status = pcap_extractor_status()
    csv_path, meta = run_cicflowmeter(Path(pcap_path))
    if csv_path is None:
        return None, {**status, **meta, "pcap": str(pcap_path)}
    aligned, validation = dataframe_from_cicflowmeter_csv(csv_path, fill_missing=fill_missing)
    if not validation.get("ok"):
        return None, {
            **status,
            **meta,
            "code": "SCHEMA_MISMATCH_AFTER_EXTRACT",
            "validation": validation,
            "pcap": str(pcap_path),
            "csv": str(csv_path),
        }
    return aligned, {
        **status,
        **meta,
        "code": "OK",
        "validation": validation,
        "pcap": str(pcap_path),
        "csv": str(csv_path),
        "rows": len(aligned),
    }
