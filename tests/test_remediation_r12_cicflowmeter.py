"""R-12 (ML-9): Python-cicflowmeter snake_case headers map onto the frozen 78-feature schema.

The tool is not installed here, so its exact header list is UNVERIFIED (audit U-5). The snake_case
names below are derived from the CSE-CIC-IDS2018 abbreviations the tool is based on
("Flow Byts/s" -> "flow_byts_s"). Unit/semantic parity with the 2017 Java extractor is also unverified.
"""
from __future__ import annotations

import re

import pandas as pd

from ingestion.normalize import _ALIAS_TO_CANONICAL, normalize_flow_frame, rename_columns_to_schema
from ingestion.schema_info import expected_feature_names
from ingestion.validate import align_dataframe


def _snake(name: str) -> str:
    return re.sub(r"[ /]+", "_", name.strip().lower())


def _abbreviated_2018_names() -> list[str]:
    """One abbreviated (2018-style) alias per canonical feature where one exists."""
    by_target: dict[str, str] = {}
    for alias, target in _ALIAS_TO_CANONICAL.items():
        if target not in by_target or len(alias) < len(by_target[target]):
            by_target[target] = alias
    return list(by_target.values())


def test_snake_case_of_every_alias_maps_to_its_canonical_feature():
    snake = {_snake(a): t for a, t in _ALIAS_TO_CANONICAL.items()}
    renamed = rename_columns_to_schema(list(snake))
    wrong = {s: (renamed[s], t) for s, t in snake.items() if renamed[s] != t}
    assert not wrong, wrong


def test_known_python_cicflowmeter_headers():
    cases = {"dst_port": "Destination Port", "flow_byts_s": "Flow Bytes/s", "flow_pkts_s": "Flow Packets/s",
             "tot_fwd_pkts": "Total Fwd Packets", "fwd_byts_b_avg": "Fwd Avg Bytes/Bulk",
             "down_up_ratio": "Down/Up Ratio", "init_fwd_win_byts": "Init_Win_bytes_forward",
             "cwr_flag_count": "CWE Flag Count", "fwd_header_len": "Fwd Header Length"}
    renamed = rename_columns_to_schema(list(cases))
    assert renamed == cases


def test_snake_case_frame_aligns_to_full_schema():
    expected = expected_feature_names()
    cols = [_snake(a) for a in _abbreviated_2018_names()]
    df = pd.DataFrame([[1.0] * len(cols)], columns=cols)
    aligned, result = align_dataframe(normalize_flow_frame(df))
    assert result.ok, result.as_dict()
    assert list(aligned.columns) == expected


def test_original_names_still_map():
    renamed = rename_columns_to_schema([" Destination Port", "Flow Bytes/s", "Init_Win_bytes_forward"])
    assert list(renamed.values()) == ["Destination Port", "Flow Bytes/s", "Init_Win_bytes_forward"]
