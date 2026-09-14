"""Column alias normalization for Stage-2 ingestion."""
from __future__ import annotations

import io

import pandas as pd

from ingestion.adapters import adapt_flows_csv
from ingestion.normalize import normalize_flow_frame, rename_columns_to_schema
from ingestion.schema_info import expected_feature_names


def test_alias_map_dst_port_and_tot_fwd():
    rename = rename_columns_to_schema(["Dst Port", "Tot Fwd Pkts", "Flow Duration"])
    assert rename["Dst Port"] == "Destination Port"
    assert rename["Tot Fwd Pkts"] == "Total Fwd Packets"
    assert rename["Flow Duration"] == "Flow Duration"


def test_normalize_duplicates_fwd_header_length_dot1():
    df = pd.DataFrame(
        {
            "Dst Port": [80],
            "Flow Duration": [1],
            "Fwd Header Len": [40],
        }
    )
    out = normalize_flow_frame(df)
    assert "Fwd Header Length" in out.columns
    assert "Fwd Header Length.1" in out.columns
    assert float(out["Fwd Header Length.1"].iloc[0]) == 40.0


def test_adapt_flows_csv_accepts_abbreviated_headers():
    names = expected_feature_names()
    # Build a row using abbreviated names for a subset + canonical for the rest
    abbrev = {
        "Dst Port": 443.0,
        "Tot Fwd Pkts": 10.0,
        "Tot Bwd Pkts": 8.0,
        "Flow Byts/s": 1000.0,
        "Flow Pkts/s": 12.0,
        "Init Fwd Win Byts": 8192.0,
        "Init Bwd Win Byts": 8192.0,
        "Fwd Act Data Pkts": 3.0,
        "Fwd Seg Size Min": 20.0,
    }
    row = {n: 0.0 for n in names}
    # Apply after normalize would map — construct CSV with aliases only for mapped ones
    csv_cols = []
    csv_vals = []
    for n in names:
        if n == "Destination Port":
            csv_cols.append("Dst Port")
            csv_vals.append(443.0)
        elif n == "Total Fwd Packets":
            csv_cols.append("Tot Fwd Pkts")
            csv_vals.append(10.0)
        elif n == "Total Backward Packets":
            csv_cols.append("Tot Bwd Pkts")
            csv_vals.append(8.0)
        elif n == "Flow Bytes/s":
            csv_cols.append("Flow Byts/s")
            csv_vals.append(1000.0)
        elif n == "Flow Packets/s":
            csv_cols.append("Flow Pkts/s")
            csv_vals.append(12.0)
        elif n == "Init_Win_bytes_forward":
            csv_cols.append("Init Fwd Win Byts")
            csv_vals.append(8192.0)
        elif n == "Init_Win_bytes_backward":
            csv_cols.append("Init Bwd Win Byts")
            csv_vals.append(8192.0)
        elif n == "act_data_pkt_fwd":
            csv_cols.append("Fwd Act Data Pkts")
            csv_vals.append(3.0)
        elif n == "min_seg_size_forward":
            csv_cols.append("Fwd Seg Size Min")
            csv_vals.append(20.0)
        else:
            csv_cols.append(n)
            csv_vals.append(0.0)
    # ensure abbrev used
    assert abbrev
    line = ",".join(csv_cols) + "\n" + ",".join(str(v) for v in csv_vals) + "\n"
    aligned, validation = adapt_flows_csv(line)
    assert validation["ok"] is True
    assert list(aligned.columns) == names
    assert float(aligned.iloc[0]["Destination Port"]) == 443.0
    assert float(aligned.iloc[0]["Total Fwd Packets"]) == 10.0


def test_cli_module_importable():
    import ingestion.__main__ as cli

    assert callable(cli.main)
