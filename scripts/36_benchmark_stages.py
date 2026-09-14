#!/usr/bin/env python
"""P8 end-to-end stage timing (validation → predict → risk → incident → optional SHAP).

PCAP extraction is timed only when cicflowmeter is available; otherwise reported as skipped.

Usage:
  python scripts/36_benchmark_stages.py
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from performance.harness import new_result, write_result
from performance.workloads import resource_snapshot, sample_feature_rows


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000.0, 4)


def main() -> int:
    p = argparse.ArgumentParser(description="P8 staged latency breakdown")
    p.add_argument("--scenario", default="normal")
    args = p.parse_args()

    from backend.services.pipeline import get_predictor, run_explain, run_prediction
    from database.db import SessionLocal, init_db
    from ingestion.adapters import pcap_extractor_status
    from ingestion.pcap_validation import validate_pcap_upload

    if get_predictor() is None:
        print(json.dumps({"error": "MODELS_NOT_READY"}))
        return 2

    stages: dict[str, float | None] = {}
    features = sample_feature_rows(1)[0]

    # PCAP validation (synthetic minimal pcap)
    minimal = b"\xd4\xc3\xb2\xa1" + b"\x02\x00\x04\x00" + b"\x00" * 16
    t0 = time.perf_counter()
    vr = validate_pcap_upload(filename="bench.pcap", content=minimal)
    stages["pcap_validation_ms"] = _ms(t0)
    stages["pcap_validation_ok"] = bool(vr.ok) if hasattr(vr, "ok") else None

    ext = pcap_extractor_status()
    stages["pcap_extractor_available"] = bool(ext.get("available"))
    if ext.get("available"):
        # Write temp pcap and attempt extract — may still fail on truncated content
        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as tmp:
            tmp.write(minimal * 50)
            tmp_path = Path(tmp.name)
        try:
            from ingestion.adapters import extract_flows_from_pcap

            t0 = time.perf_counter()
            _df, meta = extract_flows_from_pcap(tmp_path)
            stages["pcap_extraction_ms"] = _ms(t0)
            stages["pcap_extraction_ok"] = _df is not None
            stages["pcap_extraction_note"] = meta.get("message") or meta.get("error")
        except Exception as exc:  # noqa: BLE001
            stages["pcap_extraction_ms"] = None
            stages["pcap_extraction_ok"] = False
            stages["pcap_extraction_note"] = type(exc).__name__
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        stages["pcap_extraction_ms"] = None
        stages["pcap_extraction_note"] = "skipped_extractor_not_installed"

    # ML only
    t0 = time.perf_counter()
    pred = run_prediction(features, db=None, persist=False, allow_missing_features=True)
    stages["ml_predict_enrich_ms"] = _ms(t0)

    # Persist incident path
    init_db()
    t0 = time.perf_counter()
    with SessionLocal() as db:
        run_prediction(features, db=db, persist=True, allow_missing_features=True)
    stages["ml_predict_persist_ms"] = _ms(t0)

    # SHAP (high-risk path)
    t0 = time.perf_counter()
    try:
        run_explain(features, top_k=8, method="shap", allow_missing_features=True)
        stages["shap_ms"] = _ms(t0)
        stages["shap_ok"] = True
    except Exception as exc:  # noqa: BLE001
        stages["shap_ms"] = _ms(t0)
        stages["shap_ok"] = False
        stages["shap_error"] = type(exc).__name__

    result = new_result(
        workload="stage_breakdown",
        scenario=args.scenario,
        configuration={"attack_type": pred.get("attack_type"), "persist": True},
        stages=stages,
        metrics={"prediction_confidence": pred.get("confidence"), "risk_score": pred.get("risk_score")},
        notes=[
            "Component timings for diagnosis — sum is not a guaranteed e2e SLA.",
            "PCAP extraction skipped when cicflowmeter is not on PATH.",
        ],
    )
    result["resources"] = resource_snapshot()
    path = write_result(result)
    print(json.dumps({"wrote": str(path), "stages_ms": stages}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
