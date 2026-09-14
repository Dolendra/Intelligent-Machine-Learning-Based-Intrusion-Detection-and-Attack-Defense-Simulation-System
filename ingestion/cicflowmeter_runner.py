"""Optional CICFlowMeter / CLI helpers for Stage-2 PCAP→CSV extraction."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from ingestion.normalize import normalize_flow_frame
from ingestion.validate import align_dataframe


def cicflowmeter_available() -> bool:
    return bool(shutil.which("cicflowmeter"))


def run_cicflowmeter(pcap_path: Path, out_csv: Path | None = None, *, timeout_s: int = 300) -> tuple[Path | None, dict[str, Any]]:
    """Run `cicflowmeter -f <pcap> -c <csv>` when the binary is on PATH."""
    if not cicflowmeter_available():
        return None, {
            "code": "PCAP_EXTRACTOR_NOT_CONFIGURED",
            "message": "cicflowmeter not found on PATH",
            "available": False,
        }
    pcap_path = Path(pcap_path)
    if not pcap_path.exists():
        return None, {"code": "PCAP_NOT_FOUND", "message": f"missing {pcap_path}", "available": True}

    if out_csv is None:
        out_csv = Path(tempfile.mkdtemp(prefix="aegis_cic_")) / f"{pcap_path.stem}_flows.csv"
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["cicflowmeter", "-f", str(pcap_path), "-c", str(out_csv)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, check=False)
    except subprocess.TimeoutExpired:
        return None, {"code": "PCAP_EXTRACTOR_TIMEOUT", "message": f"cicflowmeter timed out after {timeout_s}s", "cmd": cmd}
    except OSError as exc:
        return None, {"code": "PCAP_EXTRACTOR_FAILED", "message": str(exc), "cmd": cmd}

    if proc.returncode != 0 or not out_csv.exists():
        return None, {
            "code": "PCAP_EXTRACTOR_FAILED",
            "message": (proc.stderr or proc.stdout or "cicflowmeter failed").strip()[:800],
            "returncode": proc.returncode,
            "cmd": cmd,
        }
    return out_csv, {"code": "OK", "cmd": cmd, "csv": str(out_csv), "available": True}


def dataframe_from_cicflowmeter_csv(csv_path: Path, *, fill_missing: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw = pd.read_csv(csv_path)
    normalized = normalize_flow_frame(raw)
    aligned, validation = align_dataframe(normalized, fill_missing=fill_missing)
    return aligned, validation.as_dict()
