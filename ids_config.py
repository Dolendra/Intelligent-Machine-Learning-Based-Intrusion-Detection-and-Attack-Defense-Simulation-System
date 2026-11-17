"""Shared configuration loader for the IDS platform."""
from __future__ import annotations

import copy
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


_YAML_CACHE: dict[tuple[str, int, int], dict[str, Any]] = {}


def _read_yaml(cfg_path: Path) -> dict[str, Any]:
    """Parse the YAML once per (path, mtime, size); return a private deep copy each call.

    Hot paths (risk scoring, recommendations) call ``load_config`` per flow; re-parsing the
    YAML every time cost ~10–60 ms per call. Editing config.yaml still takes effect
    immediately because the mtime/size key changes.
    """
    st = cfg_path.stat()
    key = (str(cfg_path.resolve()), st.st_mtime_ns, st.st_size)
    cached = _YAML_CACHE.get(key)
    if cached is None:
        with open(cfg_path, encoding="utf-8") as f:
            cached = yaml.safe_load(f)
        if len(_YAML_CACHE) > 16:
            _YAML_CACHE.clear()
        _YAML_CACHE[key] = cached
    return copy.deepcopy(cached)


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    cfg_path = Path(path) if path else ROOT / "config.yaml"
    cfg = _read_yaml(cfg_path)

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
    if os.getenv("IDS_USE_CALIBRATED_BINARY"):
        cfg.setdefault("models", {})["use_calibrated_binary"] = os.environ["IDS_USE_CALIBRATED_BINARY"].lower() in {
            "1",
            "true",
            "yes",
        }
    return cfg


def resolve_path(relative: str) -> Path:
    p = Path(relative)
    return p if p.is_absolute() else ROOT / p
