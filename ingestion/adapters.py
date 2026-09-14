"""Adapters that produce CICIDS2017-compatible feature frames."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pandas as pd

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
    aligned, result = align_dataframe(df, fill_missing=fill_missing)
    return aligned, result.as_dict()


def pcap_extractor_status() -> dict[str, Any]:
    """Report whether an external PCAP→flow tool is available.

    Stage-2 Phase A scaffolds the contract; CICFlowMeter/Zeek integration is optional.
    """
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
        "status": "ready" if available else "not_configured",
        "message": (
            "External flow extractor detected."
            if available
            else "No PCAP flow extractor installed. Use MachineLearningCVE-compatible CSV upload, "
            "or install CICFlowMeter/Zeek and configure ingestion adapters."
        ),
        "recommended": "CICFlowMeter-compatible export matching schema cicids2017_v1_1",
    }


def extract_flows_from_pcap(pcap_path: Path) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    """Attempt PCAP→flows. Returns (None, status) when extractor is not configured."""
    status = pcap_extractor_status()
    if not status["available"]:
        return None, {
            **status,
            "code": "PCAP_EXTRACTOR_NOT_CONFIGURED",
            "pcap": str(pcap_path),
        }
    # Placeholder for future subprocess integration — do not invent fake flows.
    return None, {
        **status,
        "code": "PCAP_EXTRACTOR_NOT_WIRED",
        "message": (
            "A flow extractor binary was found, but the Aegis adapter is not wired yet. "
            "Export MachineLearningCVE-compatible CSV offline and use /api/ingest/flows/csv."
        ),
        "pcap": str(pcap_path),
    }
