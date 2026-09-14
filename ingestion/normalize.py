"""Normalize common CICFlowMeter / flow-CSV column aliases to MachineLearningCVE names."""
from __future__ import annotations

import re
from typing import Iterable

import pandas as pd

from ingestion.schema_info import expected_feature_names

# Common modern CICFlowMeter abbreviations → frozen CICIDS2017 MachineLearningCVE names.
# Keys are normalized (lower, stripped, spaces collapsed). Values are schema names.
_ALIAS_TO_CANONICAL: dict[str, str] = {
    # Ports / basics
    "dst port": "Destination Port",
    "dstport": "Destination Port",
    "destination port": "Destination Port",
    "flow duration": "Flow Duration",
    # Packet counts / lengths
    "tot fwd pkts": "Total Fwd Packets",
    "total fwd packets": "Total Fwd Packets",
    "tot bwd pkts": "Total Backward Packets",
    "total backward packets": "Total Backward Packets",
    "totlen fwd pkts": "Total Length of Fwd Packets",
    "total length of fwd packets": "Total Length of Fwd Packets",
    "totlen bwd pkts": "Total Length of Bwd Packets",
    "total length of bwd packets": "Total Length of Bwd Packets",
    "fwd pkt len max": "Fwd Packet Length Max",
    "fwd packet length max": "Fwd Packet Length Max",
    "fwd pkt len min": "Fwd Packet Length Min",
    "fwd packet length min": "Fwd Packet Length Min",
    "fwd pkt len mean": "Fwd Packet Length Mean",
    "fwd packet length mean": "Fwd Packet Length Mean",
    "fwd pkt len std": "Fwd Packet Length Std",
    "fwd packet length std": "Fwd Packet Length Std",
    "bwd pkt len max": "Bwd Packet Length Max",
    "bwd packet length max": "Bwd Packet Length Max",
    "bwd pkt len min": "Bwd Packet Length Min",
    "bwd packet length min": "Bwd Packet Length Min",
    "bwd pkt len mean": "Bwd Packet Length Mean",
    "bwd packet length mean": "Bwd Packet Length Mean",
    "bwd pkt len std": "Bwd Packet Length Std",
    "bwd packet length std": "Bwd Packet Length Std",
    "flow byts/s": "Flow Bytes/s",
    "flow bytes/s": "Flow Bytes/s",
    "flow pkts/s": "Flow Packets/s",
    "flow packets/s": "Flow Packets/s",
    "flow iat mean": "Flow IAT Mean",
    "flow iat std": "Flow IAT Std",
    "flow iat max": "Flow IAT Max",
    "flow iat min": "Flow IAT Min",
    "fwd iat tot": "Fwd IAT Total",
    "fwd iat total": "Fwd IAT Total",
    "fwd iat mean": "Fwd IAT Mean",
    "fwd iat std": "Fwd IAT Std",
    "fwd iat max": "Fwd IAT Max",
    "fwd iat min": "Fwd IAT Min",
    "bwd iat tot": "Bwd IAT Total",
    "bwd iat total": "Bwd IAT Total",
    "bwd iat mean": "Bwd IAT Mean",
    "bwd iat std": "Bwd IAT Std",
    "bwd iat max": "Bwd IAT Max",
    "bwd iat min": "Bwd IAT Min",
    "fwd psh flags": "Fwd PSH Flags",
    "bwd psh flags": "Bwd PSH Flags",
    "fwd urg flags": "Fwd URG Flags",
    "bwd urg flags": "Bwd URG Flags",
    "fwd header len": "Fwd Header Length",
    "fwd header length": "Fwd Header Length",
    "bwd header len": "Bwd Header Length",
    "bwd header length": "Bwd Header Length",
    "fwd pkts/s": "Fwd Packets/s",
    "fwd packets/s": "Fwd Packets/s",
    "bwd pkts/s": "Bwd Packets/s",
    "bwd packets/s": "Bwd Packets/s",
    "pkt len min": "Min Packet Length",
    "min packet length": "Min Packet Length",
    "pkt len max": "Max Packet Length",
    "max packet length": "Max Packet Length",
    "pkt len mean": "Packet Length Mean",
    "packet length mean": "Packet Length Mean",
    "pkt len std": "Packet Length Std",
    "packet length std": "Packet Length Std",
    "pkt len var": "Packet Length Variance",
    "packet length variance": "Packet Length Variance",
    "fin flag cnt": "FIN Flag Count",
    "fin flag count": "FIN Flag Count",
    "syn flag cnt": "SYN Flag Count",
    "syn flag count": "SYN Flag Count",
    "rst flag cnt": "RST Flag Count",
    "rst flag count": "RST Flag Count",
    "psh flag cnt": "PSH Flag Count",
    "psh flag count": "PSH Flag Count",
    "ack flag cnt": "ACK Flag Count",
    "ack flag count": "ACK Flag Count",
    "urg flag cnt": "URG Flag Count",
    "urg flag count": "URG Flag Count",
    "cwe flag cnt": "CWE Flag Count",
    "cwe flag count": "CWE Flag Count",
    "ece flag cnt": "ECE Flag Count",
    "ece flag count": "ECE Flag Count",
    "down/up ratio": "Down/Up Ratio",
    "pkt size avg": "Average Packet Size",
    "average packet size": "Average Packet Size",
    "fwd seg size avg": "Avg Fwd Segment Size",
    "avg fwd segment size": "Avg Fwd Segment Size",
    "bwd seg size avg": "Avg Bwd Segment Size",
    "avg bwd segment size": "Avg Bwd Segment Size",
    "fwd header length.1": "Fwd Header Length.1",
    "fwd byts/b avg": "Fwd Avg Bytes/Bulk",
    "fwd avg bytes/bulk": "Fwd Avg Bytes/Bulk",
    "fwd pkts/b avg": "Fwd Avg Packets/Bulk",
    "fwd avg packets/bulk": "Fwd Avg Packets/Bulk",
    "fwd blk rate avg": "Fwd Avg Bulk Rate",
    "fwd avg bulk rate": "Fwd Avg Bulk Rate",
    "bwd byts/b avg": "Bwd Avg Bytes/Bulk",
    "bwd avg bytes/bulk": "Bwd Avg Bytes/Bulk",
    "bwd pkts/b avg": "Bwd Avg Packets/Bulk",
    "bwd avg packets/bulk": "Bwd Avg Packets/Bulk",
    "bwd blk rate avg": "Bwd Avg Bulk Rate",
    "bwd avg bulk rate": "Bwd Avg Bulk Rate",
    "subflow fwd pkts": "Subflow Fwd Packets",
    "subflow fwd packets": "Subflow Fwd Packets",
    "subflow fwd byts": "Subflow Fwd Bytes",
    "subflow fwd bytes": "Subflow Fwd Bytes",
    "subflow bwd pkts": "Subflow Bwd Packets",
    "subflow bwd packets": "Subflow Bwd Packets",
    "subflow bwd byts": "Subflow Bwd Bytes",
    "subflow bwd bytes": "Subflow Bwd Bytes",
    "init fwd win byts": "Init_Win_bytes_forward",
    "init_win_bytes_forward": "Init_Win_bytes_forward",
    "init bwd win byts": "Init_Win_bytes_backward",
    "init_win_bytes_backward": "Init_Win_bytes_backward",
    "fwd act data pkts": "act_data_pkt_fwd",
    "act_data_pkt_fwd": "act_data_pkt_fwd",
    "fwd seg size min": "min_seg_size_forward",
    "min_seg_size_forward": "min_seg_size_forward",
    "active mean": "Active Mean",
    "active std": "Active Std",
    "active max": "Active Max",
    "active min": "Active Min",
    "idle mean": "Idle Mean",
    "idle std": "Idle Std",
    "idle max": "Idle Max",
    "idle min": "Idle Min",
}


def _norm_key(name: str) -> str:
    s = str(name).replace("\ufeff", "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def build_alias_map(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Map normalized alias → canonical schema name (identity for expected names)."""
    mapping = dict(_ALIAS_TO_CANONICAL)
    for name in expected_feature_names():
        mapping[_norm_key(name)] = name
    if extra:
        for k, v in extra.items():
            mapping[_norm_key(k)] = v
    return mapping


def rename_columns_to_schema(columns: Iterable[str], *, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Return {original_col: canonical_or_original} rename map."""
    aliases = build_alias_map(extra)
    out: dict[str, str] = {}
    for col in columns:
        key = _norm_key(col)
        out[col] = aliases.get(key, col.strip())
    return out


def normalize_flow_frame(df: pd.DataFrame, *, extra: dict[str, str] | None = None) -> pd.DataFrame:
    """Rename known aliases; if Fwd Header Length.1 missing, duplicate Fwd Header Length when present."""
    rename = rename_columns_to_schema(df.columns, extra=extra)
    work = df.rename(columns=rename).copy()
    # Deduplicate identical names after aliasing (keep first)
    if work.columns.duplicated().any():
        work = work.loc[:, ~work.columns.duplicated()].copy()
    if "Fwd Header Length.1" not in work.columns and "Fwd Header Length" in work.columns:
        work["Fwd Header Length.1"] = work["Fwd Header Length"]
    return work
