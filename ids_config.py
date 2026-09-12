"""Shared configuration loader for the IDS platform."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:  # pragma: no cover
    pass


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    cfg_path = Path(path) if path else ROOT / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Optional .env overrides (keep yaml as source of truth for structure)
    if os.getenv("IDS_SAMPLE_FRAC"):
        cfg.setdefault("data", {})["sample_frac"] = float(os.environ["IDS_SAMPLE_FRAC"])
    if os.getenv("IDS_RANDOM_STATE"):
        cfg.setdefault("data", {})["random_state"] = int(os.environ["IDS_RANDOM_STATE"])
    if os.getenv("IDS_DATA_DIR"):
        cfg.setdefault("data", {})["raw_dir"] = os.environ["IDS_DATA_DIR"]
    if os.getenv("IDS_PROCESSED_DIR"):
        cfg.setdefault("data", {})["processed_dir"] = os.environ["IDS_PROCESSED_DIR"]
    if os.getenv("IDS_MODEL_DIR"):
        cfg.setdefault("models", {})["output_dir"] = os.environ["IDS_MODEL_DIR"]
    if os.getenv("IDS_API_HOST"):
        cfg.setdefault("api", {})["host"] = os.environ["IDS_API_HOST"]
    if os.getenv("IDS_API_PORT"):
        cfg.setdefault("api", {})["port"] = int(os.environ["IDS_API_PORT"])
    return cfg


def resolve_path(relative: str) -> Path:
    p = Path(relative)
    return p if p.is_absolute() else ROOT / p
