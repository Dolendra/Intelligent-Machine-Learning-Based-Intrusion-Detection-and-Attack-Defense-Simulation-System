"""Shared workload helpers for P8 benchmarks (demo/processed flows)."""
from __future__ import annotations

from typing import Any


def sample_feature_rows(n: int, *, attack_hint: str | None = None) -> list[dict[str, float]]:
    """Return n feature dicts (repeats demo/processed samples as needed)."""
    from backend.services.pipeline import get_predictor, load_demo_flow, load_demo_flows, sample_feature_template

    n = max(1, int(n))
    predictor = get_predictor()
    if predictor is None:
        raise RuntimeError("Models not loaded — train or ensure models/trained_models artifacts exist")

    # Prefer a larger unique sample when processed data exists
    try:
        bundle = load_demo_flows(attack_hint=attack_hint, n=min(n, 100))
        items = bundle.get("items") or []
        if items:
            rows = [dict(it["features"]) for it in items]
            while len(rows) < n:
                rows.append(dict(rows[len(rows) % len(items)]))
            return rows[:n]
    except Exception:  # noqa: BLE001
        pass

    one = load_demo_flow(attack_hint=attack_hint)
    feats = one.get("features") or sample_feature_template()
    return [dict(feats) for _ in range(n)]


def resource_snapshot() -> dict[str, Any]:
    """Best-effort CPU/RAM/disk snapshot (no secrets)."""
    import os
    import shutil

    from ids_config import ROOT

    out: dict[str, Any] = {"cpu_count": os.cpu_count()}
    try:
        import psutil

        out["cpu_percent"] = psutil.cpu_percent(interval=0.05)
        vm = psutil.virtual_memory()
        out["ram_percent"] = vm.percent
        out["ram_available_mb"] = round(vm.available / (1024 * 1024), 1)
    except Exception:  # noqa: BLE001
        out["cpu_percent"] = None
        out["ram_percent"] = None

    try:
        usage = shutil.disk_usage(str(ROOT))
        out["disk"] = {
            "total_gb": round(usage.total / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent_used": round(100.0 * (1 - usage.free / usage.total), 2),
        }
    except Exception:  # noqa: BLE001
        out["disk"] = None

    db_path = ROOT / "database" / "ids.db"
    if db_path.exists():
        out["db_size_mb"] = round(db_path.stat().st_size / (1024 * 1024), 3)
    else:
        out["db_size_mb"] = None
    return out
