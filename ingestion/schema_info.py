"""Feature schema helpers for Stage-2 ingestion."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from ids_config import ROOT, load_config, resolve_path

SCHEMA_PATH = ROOT / "ingestion" / "schema" / "cicids2017_v1_1.json"


@lru_cache(maxsize=1)
def load_feature_schema() -> dict[str, Any]:
    data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    # Prefer live bundle names when models are present (authoritative at runtime)
    try:
        from ml.features.pipeline import FeatureBundle

        cfg = load_config()
        bundle_path = resolve_path(cfg["models"]["output_dir"]) / "feature_bundle.joblib"
        if bundle_path.exists():
            bundle = FeatureBundle.load(bundle_path)
            data = {
                **data,
                "feature_names": list(bundle.feature_names),
                "feature_count": len(bundle.feature_names),
                "runtime_source": str(bundle_path.relative_to(ROOT)).replace("\\", "/"),
            }
    except Exception:
        data = {**data, "runtime_source": None}
    return data


def schema_summary() -> dict[str, Any]:
    schema = load_feature_schema()
    return {
        "schema_id": schema.get("schema_id"),
        "schema_version": schema.get("schema_version"),
        "feature_count": schema.get("feature_count"),
        "feature_names": schema.get("feature_names"),
        "runtime_source": schema.get("runtime_source"),
        "description": schema.get("description"),
        "notes": schema.get("notes", []),
    }


def expected_feature_names() -> list[str]:
    return list(load_feature_schema()["feature_names"])
