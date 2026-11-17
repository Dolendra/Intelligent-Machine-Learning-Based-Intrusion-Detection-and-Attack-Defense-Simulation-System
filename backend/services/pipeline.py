"""Application services wrapping ML + security engines."""
from __future__ import annotations

import logging

import json
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from database.db import Incident, IncidentEvent
from explainability.shap_engine import ExplanationEngine
from explainability.lime_engine import LimeExplanationEngine
from ids_config import load_config, resolve_path
from ml.features.intensity import intensity_from_features, intensity_report
from ml.prediction.predictor import FeatureValidationError, IDSPredictor, PredictionResult
from security.assets import criticality_for
from security.correlation import (
    escalate_severity,
    find_related_campaign,
    new_campaign_id,
)
from security.recommendations.engine import recommend
from security.risk.engine import compute_risk

INCIDENT_TRANSITIONS: dict[str, set[str]] = {
    "Detected": {"Triaged", "Investigating", "MitigationRecommended", "Simulating", "FalsePositive", "Resolved"},
    "Triaged": {"Investigating", "MitigationRecommended", "Simulating", "FalsePositive", "Resolved"},
    "Investigating": {"MitigationRecommended", "DefenseApplied", "Simulating", "FalsePositive", "Resolved"},
    "MitigationRecommended": {"DefenseApplied", "Simulating", "Monitoring", "Resolved"},
    "DefenseApplied": {"Monitoring", "Resolved", "Simulating"},
    "Simulating": {"DefenseApplied", "Monitoring", "Resolved", "MitigationRecommended"},
    "Monitoring": {"Resolved", "Investigating"},
    "Resolved": set(),
    "FalsePositive": set(),
}


_predictor: IDSPredictor | None = None


def get_predictor() -> IDSPredictor | None:
    """Load the frozen v1.1 predictor once. A failed load (missing files) is NOT cached, so
    artifacts restored after startup are picked up without a restart (R-04 / ARCH-10)."""
    global _predictor
    if _predictor is not None:
        return _predictor
    cfg = load_config()
    model_dir = resolve_path(cfg["models"]["output_dir"])
    required = [
        model_dir / "feature_bundle.joblib",
        model_dir / "binary_best.joblib",
        model_dir / "multiclass_best.joblib",
    ]
    if not all(p.exists() for p in required):
        return None
    _predictor = IDSPredictor.from_artifacts(model_dir)
    return _predictor


def _clear_predictor_cache() -> None:
    global _predictor
    _predictor = None


get_predictor.cache_clear = _clear_predictor_cache  # type: ignore[attr-defined]  # lru_cache-compatible


@lru_cache(maxsize=1)
def get_explainer() -> ExplanationEngine | None:
    predictor = get_predictor()
    if predictor is None:
        return None
    cfg = load_config()
    bg_path = resolve_path(cfg["models"]["output_dir"]) / "shap_background.npy"
    background = np.load(bg_path) if bg_path.exists() else None
    return ExplanationEngine(predictor, background=background)


@lru_cache(maxsize=1)
def get_lime_explainer() -> LimeExplanationEngine | None:
    predictor = get_predictor()
    if predictor is None:
        return None
    cfg = load_config()
    bg_path = resolve_path(cfg["models"]["output_dir"]) / "shap_background.npy"
    background = np.load(bg_path) if bg_path.exists() else None
    return LimeExplanationEngine(predictor, background=background)


def models_ready() -> bool:
    return get_predictor() is not None


def model_info() -> dict[str, Any]:
    cfg = load_config()
    model_dir = resolve_path(cfg["models"]["output_dir"])
    meta_path = model_dir / "model_metadata.json"
    report_path = model_dir / "training_report.json"
    predictor = get_predictor()
    info: dict[str, Any] = {
        "models_loaded": predictor is not None,
        "application_version": cfg["project"]["version"],
        "model_version": cfg.get("models", {}).get("model_version", "unknown"),
        "binary_threshold": cfg.get("models", {}).get("binary_threshold", 0.5),
        "use_calibrated_binary_config": bool(cfg.get("models", {}).get("use_calibrated_binary", False)),
        "calibrated_binary_active": bool(getattr(predictor, "calibrated_binary", False)) if predictor else False,
        "metadata_available": meta_path.exists(),
        "training_report_available": report_path.exists(),
    }
    if meta_path.exists():
        try:
            info["metadata"] = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            info["metadata"] = None
    return info


def training_comparison() -> dict[str, Any]:
    cfg = load_config()
    path = resolve_path(cfg["models"]["output_dir"]) / "training_report.json"
    if not path.exists():
        raise FileNotFoundError("training_report.json not found — train models first")
    report = json.loads(path.read_text(encoding="utf-8"))
    binary_val = report.get("binary", {}).get("validation", {})
    multi_val = report.get("multiclass", {}).get("validation", {})
    binary_rows = []
    for name, m in binary_val.items():
        binary_rows.append(
            {
                "model": name,
                "precision": m.get("precision"),
                "recall": m.get("recall"),
                "f1": m.get("f1"),
                "pr_auc": m.get("pr_auc"),
                "fpr": m.get("fpr"),
                "selection_score": m.get("selection_score"),
                "infer_seconds_val": m.get("infer_seconds_val"),
            }
        )
    multi_rows = []
    for name, m in multi_val.items():
        multi_rows.append(
            {
                "model": name,
                "f1_macro": m.get("f1_macro"),
                "f1_weighted": m.get("f1_weighted"),
                "selection_score": m.get("selection_score"),
            }
        )
    per_class = {}
    test_report = report.get("multiclass", {}).get("test", {})
    # per-class lives in validation report blobs if present
    for name, m in multi_val.items():
        if isinstance(m.get("report"), dict):
            per_class[name] = {
                k: v
                for k, v in m["report"].items()
                if isinstance(v, dict) and k not in {"accuracy", "macro avg", "weighted avg"}
            }
    return {
        "selection_criteria": report.get("selection_criteria"),
        "binary_best": report.get("binary", {}).get("best"),
        "multiclass_best": report.get("multiclass", {}).get("best"),
        "binary_validation": binary_rows,
        "multiclass_validation": multi_rows,
        "binary_test": report.get("binary", {}).get("test"),
        "multiclass_test": {k: v for k, v in test_report.items() if k != "confusion_matrix"},
        "per_class_validation": per_class,
        "classes": report.get("multiclass", {}).get("classes"),
    }


def _intensity_from_features(features: dict[str, float]) -> float | None:
    return intensity_from_features(features)


def _enrich_prediction(
    pred: PredictionResult,
    features: dict[str, float],
    *,
    asset_criticality: float | None = None,
) -> dict[str, Any]:
    confidence = pred.multiclass_confidence if pred.is_attack else pred.binary_confidence
    intensity_meta = intensity_report(features)
    intensity = intensity_meta["value"]
    risk = compute_risk(
        pred.attack_type,
        confidence,
        pred.is_attack,
        intensity,
        asset_criticality=asset_criticality,
    )
    rec = recommend(
        pred.attack_type,
        risk["severity"],
        confidence=confidence,
        traffic_intensity=intensity,
        certainty=pred.certainty,
        is_attack=pred.is_attack,
    )
    factors = dict(risk.get("factors") or {})
    factors["intensity_method"] = intensity_meta["method"]
    return {
        "is_attack": pred.is_attack,
        "attack_type": pred.attack_type,
        "confidence": confidence,
        "binary_proba_attack": pred.binary_proba_attack,
        "class_probabilities": pred.class_probabilities,
        "risk_score": risk["risk_score"],
        "severity": risk["severity"],
        "risk_factors": factors,
        "risk_contributions": risk.get("contributions"),
        "risk_why": risk.get("why"),
        "recommendation": rec,
        "certainty": pred.certainty,
        "confidence_band": pred.certainty,
        "confidence_band_label": {
            "likely_benign": "Likely benign",
            "uncertain": "Ambiguous / review",
            "likely_attack": "High-confidence attack",
        }.get(pred.certainty, pred.certainty),
        "threshold": pred.threshold,
        "uncertainty_lower": pred.uncertainty_lower,
        "uncertainty_upper": pred.uncertainty_upper,
        "intensity_method": intensity_meta["method"],
        "threshold_note": (
            "Attack decision uses operating threshold; "
            "confidence_band is a separate review band and may mark ATTACK rows as Ambiguous/review "
            "when probability is between the band edges."
        ),
    }


def _flow_source_ref(features: dict[str, float], explicit: str | None = None) -> str | None:
    """Return explicit source fingerprint only — never invent from Destination Port."""
    if explicit:
        return explicit[:128]
    return None


def _find_duplicate_incident(
    db: Session,
    attack_type: str,
    source_ref: str | None,
) -> Incident | None:
    """Dedup only when an explicit source_ref is present (never Destination Port)."""
    if not source_ref:
        return None
    cfg = load_config()
    window = int(cfg.get("incident", {}).get("dedup_window_minutes", 5))
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window)
    closed = ("Resolved", "FalsePositive")
    return (
        db.query(Incident)
        .filter(
            Incident.attack_type == attack_type,
            Incident.source_ref == source_ref,
            Incident.created_at >= cutoff,
            ~Incident.status.in_(closed),
        )
        .order_by(Incident.created_at.desc())
        .first()
    )


_gate_log = logging.getLogger("aegis.zero_day")


def _gate_metric(name: str, n: int = 1) -> None:
    try:
        from backend.observability.registry import domain_metrics

        domain_metrics.incr(name, n)
    except Exception:  # noqa: BLE001
        pass


def zero_day_assessment_with_status(
    rows: list[dict[str, float]], *, explain_top: int = 5,
) -> tuple[list[dict[str, Any] | None], list[str]]:
    """Advisory Aegis-OSR Zero-Day Gate verdicts plus a per-row status.

    Status is ``ok``, ``unavailable`` (gate not loaded) or ``error`` (this row could not be
    scored). The frozen v1.1 decision is never altered and detection never fails because of
    the gate. R-04 (ARCH-10, ML-22): failures are no longer silent. They are logged
    (exception class only, no flow data) and counted, and one bad row no longer nullifies the
    whole batch.
    """
    n = len(rows)
    if not rows:
        return [], []
    try:
        from research.serving import gate_error, get_gate

        gate = get_gate()
    except Exception as exc:  # noqa: BLE001
        gate, reason = None, type(exc).__name__
    else:
        reason = gate_error() if gate is None else None
    if gate is None:
        _gate_metric("detection.zero_day_gate_unavailable", n)
        _gate_log.warning("zero_day_gate_unavailable rows=%d reason=%s", n, reason)
        return [None] * n, ["unavailable"] * n
    try:
        return gate.assess(rows, explain_top=explain_top), ["ok"] * n
    except Exception as exc:  # noqa: BLE001 — fall back to per-row scoring
        _gate_log.warning("zero_day_gate_batch_error rows=%d error=%s; scoring rows individually",
                          n, type(exc).__name__)
    results: list[dict[str, Any] | None] = []
    statuses: list[str] = []
    for row in rows:
        try:
            results.append(gate.assess([row], explain_top=explain_top)[0])
            statuses.append("ok")
        except Exception as exc:  # noqa: BLE001
            results.append(None)
            statuses.append("error")
            _gate_log.warning("zero_day_gate_row_error error=%s", type(exc).__name__)
    errors = statuses.count("error")
    if errors:
        _gate_metric("detection.zero_day_gate_errors", errors)
    return results, statuses


def zero_day_assessment(rows: list[dict[str, float]], *, explain_top: int = 5) -> list[dict[str, Any] | None]:
    """Backwards-compatible wrapper: verdicts only (``None`` where the gate could not score)."""
    return zero_day_assessment_with_status(rows, explain_top=explain_top)[0]


def _gate_version() -> str | None:
    try:
        from research.serving import get_gate

        gate = get_gate()
        return getattr(gate, "version", None) if gate is not None else None
    except Exception:  # noqa: BLE001
        return None


def _record_zero_day_alert(
    db: Session,
    zero_day: dict[str, Any],
    *,
    pred: PredictionResult,
    policy: str,
    raised_incident: bool,
    incident_code: str | None,
    source_ref: str | None,
    origin: str,
) -> None:
    """Audit row for every gate alert on a persisted detection (whether or not it raised an incident)."""
    import json as _json

    from database.db import ZeroDayAlert

    ev = zero_day.get("evidence") or {}
    fam = zero_day.get("family") or {}
    db.add(ZeroDayAlert(
        origin=origin,
        source_ref=source_ref,
        incident_code=incident_code,
        policy=policy,
        raised_incident=int(bool(incident_code) and raised_incident),
        gate_label=str(zero_day.get("label")),
        p_value=float(zero_day.get("p_value", 1.0)),
        alpha=float(zero_day.get("alpha", 0.0)),
        fused_surprisal=zero_day.get("fused_surprisal"),
        p_attack=(ev.get("supervised") or {}).get("p_attack"),
        knn_distance=(ev.get("novelty") or {}).get("knn_distance"),
        family_predicted=fam.get("predicted"),
        family_conformity_p=fam.get("conformity_p"),
        frozen_is_attack=int(bool(pred.is_attack)),
        frozen_attack_type=pred.attack_type,
        gate_model_version=_gate_version() or "unknown",
        evidence=_json.dumps(zero_day.get("top_deviations") or []),
    ))
    try:
        from backend.observability.registry import domain_metrics

        domain_metrics.incr("detection.zero_day_alerts_total")
        if not pred.is_attack:
            domain_metrics.incr("detection.zero_day_gate_only_alerts_total")
    except Exception:  # noqa: BLE001
        pass


def run_prediction(
    features: dict[str, float],
    db: Session | None = None,
    persist: bool = True,
    allow_missing_features: bool = False,
    asset_criticality: float | None = None,
    source_ref: str | None = None,
    asset_id: str | None = None,
    origin: str = "api",
) -> dict[str, Any]:
    import time

    from security.detection_policy import GATE_ONLY_LABEL, configured_policy, decide

    _t0 = time.perf_counter()
    predictor = get_predictor()
    if predictor is None:
        raise RuntimeError("Models not trained. Run scripts/01_prepare_data.py and scripts/02_train_models.py")

    if asset_criticality is None and asset_id:
        asset_criticality = criticality_for(asset_id)

    pred: PredictionResult = predictor.predict_row(features, allow_missing=allow_missing_features)
    payload = _enrich_prediction(pred, features, asset_criticality=asset_criticality)
    flow_ref = _flow_source_ref(features, source_ref)
    payload["source_ref"] = flow_ref
    payload["deduplicated"] = False
    payload["campaign_id"] = None
    payload["escalated"] = False

    # Advisory Zero-Day Gate runs BEFORE the incident decision; the shared policy (also used by
    # the Cyber Range) decides whether an incident is raised and what it is called.
    zd_results, zd_status = zero_day_assessment_with_status([features])
    zero_day = zd_results[0]
    payload["zero_day"] = zero_day
    payload["zero_day_status"] = zd_status[0]
    policy = configured_policy()
    decision = decide(pred.is_attack, pred.attack_type, bool(zero_day and zero_day.get("alert")),
                      (zero_day or {}).get("label"), policy)
    payload["detection_decision"] = {
        "policy": policy,
        "source": decision.source,
        "raises_incident": decision.raises_incident,
        "incident_label": decision.incident_label,
        "known_family": decision.known_family,
        "gate_hint": decision.gate_hint,
    }
    incident_type = decision.incident_label or pred.attack_type
    gate_only = decision.raises_incident and not pred.is_attack
    inc_risk = {"score": payload["risk_score"], "severity": payload["severity"],
                "recommendation": payload["recommendation"]["primary"], "confidence": payload["confidence"]}
    if gate_only:
        # Gate-only incident: risk/playbook for an unnamed attack; frozen-verdict fields stay untouched.
        p_val = float(zero_day.get("p_value", 1.0))
        g_conf = max(0.0, min(1.0, 1.0 - p_val))
        # R-01 (ML-5/ARCH-19): use the flow's measured intensity. The frozen verdict is BENIGN
        # here, and the benign risk branch hard-codes intensity 0.0.
        g_risk = compute_risk(GATE_ONLY_LABEL, g_conf, True,
                              traffic_intensity=intensity_report(features)["value"],
                              asset_criticality=asset_criticality)
        g_rec = recommend(GATE_ONLY_LABEL, g_risk.get("severity"), confidence=g_conf, is_attack=True)
        # R-01 (ARCH-2): compute_risk returns "risk_score"; the old "score" lookup always gave 0.
        inc_risk = {"score": g_risk["risk_score"], "severity": g_risk["severity"],
                    "recommendation": g_rec.get("primary", ""), "confidence": g_conf}
        payload["incident_risk"] = {"risk_score": inc_risk["score"], "severity": inc_risk["severity"],
                                    "recommendation": inc_risk["recommendation"]}

    incident_id = None
    if persist and db is not None and decision.raises_incident:
        existing = _find_duplicate_incident(db, incident_type, flow_ref)
        if existing is not None:
            incident_id = existing.incident_code
            hits = int(getattr(existing, "hit_count", 1) or 1) + 1
            existing.hit_count = hits
            existing.confidence = max(float(existing.confidence or 0), float(inc_risk["confidence"]))
            if float(inc_risk["score"]) >= float(existing.risk_score or 0):
                existing.risk_score = inc_risk["score"]
                existing.recommendation = inc_risk["recommendation"]
            old_sev = existing.severity
            new_sev = escalate_severity(existing.severity, inc_risk["severity"], hit_count=hits)
            existing.severity = new_sev
            if gate_only:
                payload["incident_risk"]["severity"] = new_sev
            else:
                payload["severity"] = new_sev
            payload["escalated"] = severity_changed(old_sev, new_sev)
            if asset_criticality is not None:
                existing.asset_criticality = asset_criticality
            if flow_ref and not existing.source_ref:
                existing.source_ref = flow_ref
            payload["campaign_id"] = getattr(existing, "campaign_id", None)
            notes = f"Deduplicated prediction (hit_count={hits})"
            if payload["escalated"]:
                notes += f"; severity {old_sev} → {new_sev}"
            _record_incident_event(
                db,
                incident_id,
                existing.status,
                existing.status,
                actor="system",
                notes=notes,
                action="escalate" if payload["escalated"] else "dedup",
            )
            db.commit()
            payload["deduplicated"] = True
        else:
            related = find_related_campaign(db, attack_type=incident_type, source_ref=flow_ref)
            if not flow_ref:
                # Without a source reference there is nothing to correlate on: do not invent a
                # one-incident "campaign" for every detection.
                campaign_id = None
            else:
                campaign_id = (
                    related.campaign_id
                    if related is not None and getattr(related, "campaign_id", None)
                    else (related.incident_code.replace("INC-", "CMP-") if related is not None else new_campaign_id())
                )
            if related is not None and not getattr(related, "campaign_id", None):
                related.campaign_id = campaign_id

            incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
            row = Incident(
                incident_code=incident_id,
                attack_type=incident_type,
                is_attack=1,
                confidence=inc_risk["confidence"],
                risk_score=inc_risk["score"],
                severity=inc_risk["severity"],
                recommendation=inc_risk["recommendation"],
                detector_source=decision.source,
                zero_day_label=(zero_day or {}).get("label") if zero_day and zero_day.get("alert") else None,
                zero_day_p_value=(zero_day or {}).get("p_value") if zero_day else None,
                explanation="",
                status="Detected",
                asset_criticality=asset_criticality,
                source_ref=flow_ref,
                campaign_id=campaign_id,
                hit_count=1,
            )
            db.add(row)
            db.flush()
            note = ("Created from Zero-Day Gate alert (frozen model: benign)" if gate_only
                    else "Created from prediction")
            if related is not None:
                note = f"Created; linked campaign {campaign_id} (related {related.incident_code})"
            _record_incident_event(db, incident_id, None, "Detected", actor="system", notes=note, action="create")
            db.commit()
            payload["campaign_id"] = campaign_id
            try:
                from backend.services.events import notify_sync

                notify_sync(
                    {
                        "type": "incident_created",
                        "incident_id": incident_id,
                        "attack_type": incident_type,
                        "detector_source": decision.source,
                        "severity": inc_risk["severity"],
                        "risk_score": inc_risk["score"],
                        "campaign_id": campaign_id,
                    }
                )
            except Exception:
                pass

    payload["incident_id"] = incident_id
    if persist and db is not None and zero_day and zero_day.get("alert"):
        try:
            _record_zero_day_alert(db, zero_day, pred=pred, policy=policy,
                                   raised_incident=decision.raises_incident, incident_code=incident_id,
                                   source_ref=flow_ref, origin=origin)
            db.commit()
        except Exception:  # noqa: BLE001 — auditing must not break detection
            db.rollback()
    from backend.services.decision_trace import build_trace_from_prediction

    payload["decision_trace"] = build_trace_from_prediction(payload)
    _observe_prediction(payload, duration_ms=(time.perf_counter() - _t0) * 1000, source="single")
    return payload


def _observe_prediction(payload: dict[str, Any], *, duration_ms: float, source: str) -> None:
    """Operational metrics + JSON log for a prediction (no raw feature dump)."""
    try:
        from backend.observability.context import bind_correlation
        from backend.observability.events import log_event
        from backend.observability.registry import domain_metrics

        is_attack = bool(payload.get("is_attack"))
        domain_metrics.incr("detection.flows_processed_total")
        domain_metrics.incr("detection.detections_total")
        if is_attack:
            domain_metrics.incr("detection.attacks_detected_total")
        else:
            domain_metrics.incr("detection.normal_flows_total")
        domain_metrics.observe_ms("detection.prediction_latency_ms", duration_ms)
        with bind_correlation(incident_id=payload.get("incident_id")):
            log_event(
                "prediction",
                duration_ms=duration_ms,
                status="ok",
                prediction=payload.get("attack_type"),
                attack_family=payload.get("attack_type"),
                confidence=payload.get("confidence"),
                risk_score=payload.get("risk_score"),
                incident_id=payload.get("incident_id"),
                campaign_id=payload.get("campaign_id"),
                model_version="v1.1-research",
                feature_schema_version="1.1.0",
                preprocessing_version="cicids2017_v1_1",
                source=source,
                is_attack=is_attack,
            )
    except Exception:  # noqa: BLE001
        pass


def severity_changed(old: str | None, new: str | None) -> bool:
    from security.correlation import severity_rank

    return severity_rank(new) > severity_rank(old)


def run_prediction_batch(
    rows: list[dict[str, float]],
    db: Session | None = None,
    persist: bool = False,
    allow_missing_features: bool = False,
    asset_criticality: float | None = None,
) -> dict[str, Any]:
    import time

    _t0 = time.perf_counter()
    if not rows:
        raise ValueError("Batch must contain at least one feature vector")
    if len(rows) > 500:
        raise ValueError("Batch size limited to 500 flows per request")

    predictor = get_predictor()
    if predictor is None:
        raise RuntimeError("Models not trained. Run scripts/01_prepare_data.py and scripts/02_train_models.py")

    import pandas as pd

    df = pd.DataFrame(rows)
    preds = predictor.predict_many_vectorized(df, allow_missing=allow_missing_features)
    zero_day, zd_status = zero_day_assessment_with_status(rows, explain_top=3)
    results: list[dict[str, Any]] = []
    for i, (pred, features) in enumerate(zip(preds, rows)):
        item = _enrich_prediction(pred, features, asset_criticality=asset_criticality)
        item["flow_index"] = i
        item["incident_id"] = None
        item["zero_day"] = zero_day[i]
        item["zero_day_status"] = zd_status[i]
        if persist and db is not None and (pred.is_attack or (zero_day[i] or {}).get("alert")):
            single = run_prediction(
                features,
                db=db,
                persist=True,
                allow_missing_features=True,
                asset_criticality=asset_criticality,
                origin="batch",
            )
            item["incident_id"] = single.get("incident_id")
        results.append(item)

    attacks = [r for r in results if r["is_attack"]]
    by_type: dict[str, int] = {}
    for r in attacks:
        by_type[r["attack_type"]] = by_type.get(r["attack_type"], 0) + 1
    highest = max(results, key=lambda r: r["risk_score"]) if results else None

    duration_ms = (time.perf_counter() - _t0) * 1000
    try:
        from backend.observability.events import log_event
        from backend.observability.registry import domain_metrics

        for r in results:
            # Avoid double-count when persist path already observed via run_prediction
            if r.get("incident_id"):
                continue
            domain_metrics.incr("detection.flows_processed_total")
            domain_metrics.incr("detection.detections_total")
            if r.get("is_attack"):
                domain_metrics.incr("detection.attacks_detected_total")
            else:
                domain_metrics.incr("detection.normal_flows_total")
        domain_metrics.observe_ms("detection.prediction_latency_ms", duration_ms)
        log_event(
            "prediction_batch",
            duration_ms=duration_ms,
            status="ok",
            total_flows=len(results),
            attack_flows=len(attacks),
            model_version="v1.1-research",
            feature_schema_version="1.1.0",
            source="batch",
        )
    except Exception:  # noqa: BLE001
        pass

    novel = [r for r in results if (r.get("zero_day") or {}).get("novel")]
    return {
        "total_flows": len(results),
        "attack_flows": len(attacks),
        "zero_day_alerts": sum(1 for r in results if (r.get("zero_day") or {}).get("alert")),
        "zero_day_novel": len(novel),
        "zero_day_missed_by_frozen": sum(1 for r in novel if not r["is_attack"]),
        "benign_flows": len(results) - len(attacks),
        "attack_percentage": round(100.0 * len(attacks) / len(results), 2),
        "by_attack_type": by_type,
        "highest_risk": {
            "flow_index": highest["flow_index"],
            "attack_type": highest["attack_type"],
            "risk_score": highest["risk_score"],
            "severity": highest["severity"],
        }
        if highest
        else None,
        "results": results,
    }


def run_explain(
    features: dict[str, float],
    top_k: int = 10,
    method: str = "shap",
    allow_missing_features: bool = False,
) -> dict[str, Any]:
    cfg = load_config()
    xai_cfg = cfg.get("xai", {})
    method = (method or xai_cfg.get("default_method", "shap")).lower().strip()
    top_k = int(top_k or xai_cfg.get("top_k", 10))
    if method == "lime":
        explainer = get_lime_explainer()
        if explainer is None:
            raise RuntimeError("Explainability engine unavailable — train models first.")
        return explainer.explain(features, top_k=top_k)
    explainer = get_explainer()
    if explainer is None:
        raise RuntimeError("Explainability engine unavailable — train models first.")
    return explainer.explain(features, top_k=top_k, allow_missing=allow_missing_features)


def _record_incident_event(
    db: Session,
    incident_code: str,
    old_status: str | None,
    new_status: str,
    *,
    actor: str = "system",
    notes: str | None = None,
    action: str | None = None,
) -> None:
    db.add(
        IncidentEvent(
            incident_code=incident_code,
            old_status=old_status,
            new_status=new_status,
            actor=actor,
            notes=notes,
            action=action,
        )
    )


def _incident_dict(row: Incident, events: list[IncidentEvent] | None = None) -> dict[str, Any]:
    payload = {
        "incident_id": row.incident_code,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "attack_type": row.attack_type,
        "confidence": row.confidence,
        "risk_score": row.risk_score,
        "severity": row.severity,
        "recommendation": row.recommendation,
        "status": row.status,
        "analyst_notes": getattr(row, "analyst_notes", None),
        "defense_action": getattr(row, "defense_action", None),
        "resolved_at": row.resolved_at.isoformat() if getattr(row, "resolved_at", None) else None,
        "asset_criticality": getattr(row, "asset_criticality", None),
        "source_ref": getattr(row, "source_ref", None),
        "campaign_id": getattr(row, "campaign_id", None),
        "hit_count": getattr(row, "hit_count", 1),
        "detector_source": getattr(row, "detector_source", None) or "frozen",
        "zero_day_label": getattr(row, "zero_day_label", None),
        "zero_day_p_value": getattr(row, "zero_day_p_value", None),
        "allowed_next_statuses": sorted(INCIDENT_TRANSITIONS.get(row.status or "Detected", set())),
    }
    if events is not None:
        payload["events"] = [
            {
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "old_status": e.old_status,
                "new_status": e.new_status,
                "actor": e.actor,
                "notes": e.notes,
                "action": e.action,
            }
            for e in events
        ]
    return payload


def get_incident(db: Session, incident_id: str) -> dict[str, Any] | None:
    row = db.query(Incident).filter(Incident.incident_code == incident_id).first()
    if not row:
        return None
    events = (
        db.query(IncidentEvent)
        .filter(IncidentEvent.incident_code == incident_id)
        .order_by(IncidentEvent.timestamp.asc())
        .all()
    )
    return _incident_dict(row, events)


def update_incident_status(
    db: Session,
    incident_id: str,
    status: str,
    *,
    analyst_notes: str | None = None,
    defense_action: str | None = None,
) -> dict[str, Any]:
    row = db.query(Incident).filter(Incident.incident_code == incident_id).first()
    if not row:
        raise KeyError(f"Unknown incident: {incident_id}")
    current = row.status or "Detected"
    target = status.strip()
    allowed = INCIDENT_TRANSITIONS.get(current, set())
    if target == current:
        # Notes / defense-action update without a status change (allowed in every state,
        # including closed incidents) — recorded in the audit trail as a note event.
        if analyst_notes is not None:
            row.analyst_notes = analyst_notes
        if defense_action is not None:
            row.defense_action = defense_action
        _record_incident_event(db, incident_id, current, current, actor="analyst",
                               notes=analyst_notes, action=defense_action)
        db.commit()
        return get_incident(db, incident_id) or _incident_dict(row)
    if target not in allowed:
        raise ValueError(f"Invalid transition {current} → {target}. Allowed: {sorted(allowed)}")
    row.status = target
    if analyst_notes is not None:
        row.analyst_notes = analyst_notes
    if defense_action is not None:
        row.defense_action = defense_action
    if target in {"Resolved", "FalsePositive"}:
        row.resolved_at = datetime.now(timezone.utc)
    _record_incident_event(
        db,
        incident_id,
        current,
        target,
        actor="analyst",
        notes=analyst_notes,
        action=defense_action,
    )
    db.commit()
    return get_incident(db, incident_id) or _incident_dict(row)


def start_simulation_from_incident(db: Session, incident_id: str) -> dict[str, Any]:
    from simulation.engine.core import simulation_engine

    incident = get_incident(db, incident_id)
    if incident is None:
        raise KeyError(f"Unknown incident: {incident_id}")
    session = simulation_engine.start(
        attack_type=incident["attack_type"],
        confidence=float(incident["confidence"] or 0.9),
        incident_id=incident_id,
        risk_score=float(incident["risk_score"] or 0),
        severity=incident["severity"],
        recommendation={
            "primary": incident["recommendation"],
            "actions": [incident["recommendation"]],
            "advisory_only": True,
        },
    )
    row = db.query(Incident).filter(Incident.incident_code == incident_id).first()
    if row and row.status != "Simulating":
        try:
            update_incident_status(db, incident_id, "Simulating")
        except ValueError:
            current = row.status
            row.status = "Simulating"
            _record_incident_event(db, incident_id, current, "Simulating", actor="system", notes="Simulation started")
            db.commit()
    return session


def list_incidents(db: Session, limit: int = 50) -> list[dict[str, Any]]:
    rows = db.query(Incident).order_by(Incident.created_at.desc()).limit(limit).all()
    return [_incident_dict(r) for r in rows]


def analytics_summary(db: Session) -> dict[str, Any]:
    rows = db.query(Incident).all()
    by_sev: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for r in rows:
        by_sev[r.severity or "UNKNOWN"] = by_sev.get(r.severity or "UNKNOWN", 0) + 1
        by_type[r.attack_type or "UNKNOWN"] = by_type.get(r.attack_type or "UNKNOWN", 0) + 1
        by_status[r.status or "UNKNOWN"] = by_status.get(r.status or "UNKNOWN", 0) + 1
    return {
        "total_incidents": len(rows),
        "by_severity": by_sev,
        "by_attack_type": by_type,
        "by_status": by_status,
    }


def sample_feature_template() -> dict[str, float]:
    predictor = get_predictor()
    if predictor is None:
        return {}
    return {name: 0.0 for name in predictor.bundle.feature_names}


def _bundled_demo_flows() -> dict[str, Any] | None:
    """Committed demo vectors for CI / fresh clones without data/processed."""
    path = resolve_path(load_config()["models"]["output_dir"]) / "demo_flows.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _demo_from_bundle(attack_hint: str | None = None) -> dict[str, Any] | None:
    blob = _bundled_demo_flows()
    if not blob:
        return None
    by_label: dict[str, dict[str, float]] = blob.get("by_label") or {}
    if not by_label:
        return None
    hint = (attack_hint or "").strip()
    if hint and hint in by_label:
        label = hint
    elif hint == "BENIGN" and "BENIGN" in by_label:
        label = "BENIGN"
    else:
        label = next((k for k in by_label if k != "BENIGN"), next(iter(by_label)))
    features = dict(by_label[label])
    predictor = get_predictor()
    if predictor is not None:
        # Align to trained schema; fill missing with 0 only for absent keys
        features = {name: float(features.get(name, 0.0)) for name in predictor.bundle.feature_names}
    return {"features": features, "label": label, "source": "bundled_demo_flows"}


def load_demo_flow(attack_hint: str | None = None) -> dict[str, Any]:
    """Load one demo flow: prefer processed test split, else committed demo_flows.json."""
    from ml.preprocessing.dataset import load_processed

    try:
        test = load_processed("test")
    except FileNotFoundError:
        bundled = _demo_from_bundle(attack_hint)
        if bundled:
            return bundled
        return {"features": sample_feature_template(), "label": None, "source": "zero_template"}
    if attack_hint and attack_hint != "BENIGN":
        subset = test[test["Label"] == attack_hint]
        if subset.empty:
            subset = test[test["is_attack"] == 1]
    elif attack_hint == "BENIGN":
        subset = test[test["is_attack"] == 0]
    else:
        subset = test[test["is_attack"] == 1]
    if subset.empty:
        subset = test
    # a fresh random flow each time (a fixed random_state returned the same flow on every click)
    row = subset.sample(1).iloc[0]
    features = {c: float(row[c]) for c in predictor.bundle.feature_names} if (predictor := get_predictor()) else {}
    substituted = bool(attack_hint and attack_hint != "BENIGN" and str(row["Label"]) != attack_hint)
    return {"features": features, "label": str(row["Label"]), "source": "processed_test", "substituted": substituted}


def load_demo_flows(attack_hint: str | None = None, n: int = 10) -> dict[str, Any]:
    """Load multiple demo flows for batch demos."""
    from ml.preprocessing.dataset import load_processed

    n = max(1, min(100, int(n)))
    try:
        test = load_processed("test")
    except FileNotFoundError:
        bundled = _demo_from_bundle(attack_hint)
        if not bundled:
            return {"items": [], "count": 0}
        items = [{"features": bundled["features"], "label": bundled["label"]} for _ in range(n)]
        return {"items": items, "count": len(items), "source": "bundled_demo_flows"}
    if attack_hint and attack_hint != "BENIGN":
        subset = test[test["Label"] == attack_hint]
        if subset.empty:
            subset = test[test["is_attack"] == 1]
    elif attack_hint == "BENIGN":
        subset = test[test["is_attack"] == 0]
    else:
        subset = test
    if subset.empty:
        return {"items": [], "count": 0}
    sample = subset.sample(min(n, len(subset)), random_state=42)
    predictor = get_predictor()
    if predictor is None:
        return {"items": [], "count": 0}
    items = []
    for _, row in sample.iterrows():
        features = {c: float(row[c]) for c in predictor.bundle.feature_names}
        items.append({"features": features, "label": str(row["Label"])})
    return {"items": items, "count": len(items), "source": "processed_test"}


def parse_flows_csv(content: str | bytes, *, max_rows: int = 500) -> list[dict[str, float]]:
    """Parse CSV with strict numeric validation and schema checks against trained features when available."""
    import io
    import math

    import pandas as pd

    text = content.decode("utf-8-sig") if isinstance(content, (bytes, bytearray)) else content
    df = pd.read_csv(io.StringIO(text))
    if df.empty:
        raise ValueError("CSV contains no rows")
    if len(df) > max_rows:
        raise ValueError(f"CSV limited to {max_rows} rows (got {len(df)})")
    if df.columns.duplicated().any():
        dups = df.columns[df.columns.duplicated()].tolist()
        raise ValueError(f"Duplicate columns in CSV: {dups}")

    drop = [c for c in ("Label", "is_attack", "Flow ID", "Timestamp") if c in df.columns]
    df = df.drop(columns=drop, errors="ignore")
    if df.shape[1] == 0:
        raise ValueError("CSV has no feature columns after dropping metadata")

    predictor = get_predictor()
    expected = list(predictor.bundle.feature_names) if predictor else None
    if expected:
        missing_cols = [c for c in expected if c not in df.columns]
        if missing_cols:
            raise ValueError(
                f"CSV missing {len(missing_cols)} required feature columns "
                f"(e.g. {', '.join(missing_cols[:8])}{'...' if len(missing_cols) > 8 else ''})"
            )
        # Keep expected order; allow extra columns but warn via details in message if many
        extras = [c for c in df.columns if c not in expected]
        df = df[expected]
    else:
        extras = []

    rows: list[dict[str, float]] = []
    for i, row in df.iterrows():
        features: dict[str, float] = {}
        for k, v in row.items():
            col = str(k).strip()
            if pd.isna(v):
                raise ValueError(f"Row {int(i) + 2}: column '{col}' is NaN/empty")
            try:
                num = float(v)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Row {int(i) + 2}: column '{col}' invalid numeric value: {v!r}") from exc
            if math.isinf(num):
                raise ValueError(f"Row {int(i) + 2}: column '{col}' is Inf")
            features[col] = num
        rows.append(features)
    if extras and len(extras) > 20:
        # Not fatal — extras already dropped when expected schema known
        pass
    return rows


def export_incidents_csv(db: Session, limit: int = 1000) -> str:
    import csv
    import io

    items = list_incidents(db, limit=limit)
    buf = io.StringIO()
    fields = [
        "incident_id",
        "created_at",
        "attack_type",
        "confidence",
        "risk_score",
        "severity",
        "recommendation",
        "status",
        "defense_action",
        "resolved_at",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for item in items:
        writer.writerow({k: item.get(k) for k in fields})
    return buf.getvalue()


def export_analytics_payload(db: Session) -> dict[str, Any]:
    return {
        "analytics": analytics_summary(db),
        "incidents": list_incidents(db, limit=1000),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "note": "Decision-support export from Aegis IDS prototype — not live packet capture.",
    }


def _artifact_json(name: str) -> dict[str, Any] | None:
    cfg = load_config()
    path = resolve_path(cfg["models"]["output_dir"]) / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def model_health() -> dict[str, Any]:
    """Research-facing model health / readiness summary."""
    info = model_info()
    cfg = load_config()
    model_dir = resolve_path(cfg["models"]["output_dir"])
    required = ["feature_bundle.joblib", "binary_best.joblib", "multiclass_best.joblib"]
    missing = [f for f in required if not (model_dir / f).exists()]
    operating = _artifact_json("threshold_operating_point.json")
    drift = _artifact_json("drift_report.json")
    xai = _artifact_json("xai_agreement_report.json")
    status = "healthy" if info["models_loaded"] and not missing else "degraded"
    return {
        "status": status,
        "models_loaded": info["models_loaded"],
        "missing_artifacts": missing,
        "application_version": info.get("application_version"),
        "model_version": info.get("model_version"),
        "binary_threshold": info.get("binary_threshold"),
        "calibrated_binary_active": info.get("calibrated_binary_active"),
        "metadata": info.get("metadata"),
        "operating_point_available": operating is not None,
        "operating_point": operating,
        "drift_available": drift is not None,
        "drift_summary": {
            "flagged": (drift or {}).get("feature_drift", {}).get("flagged_psi_ge_0.2")
            if drift
            else None,
            "status": (drift or {}).get("status"),
        }
        if drift
        else None,
        "xai_agreement_available": xai is not None,
        "note": "Prototype health view — does not claim production SOC monitoring.",
    }


def global_shap_summary(top_k: int = 15, refresh: bool = False) -> dict[str, Any]:
    from explainability.global_importance import (
        attack_specific_from_explanations,
        global_model_importance,
    )

    cached = _artifact_json("global_shap_summary.json")
    if cached and not refresh:
        return cached

    predictor = get_predictor()
    if predictor is None:
        raise RuntimeError("Models not loaded")
    global_imp = global_model_importance(predictor, top_k=top_k)
    explanations: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    if refresh:
        try:
            items = load_demo_flows(n=18).get("items") or []
        except Exception:
            items = []
        for item in items:
            try:
                explanations.append(
                    run_explain(item["features"], method="shap", top_k=10, allow_missing_features=True)
                )
            except Exception:
                continue
    attack_imp = (
        attack_specific_from_explanations(explanations, top_k=8)
        if explanations
        else {
            "method": "mean_abs_local_explanation",
            "note": "Run scripts/24_global_shap_summary.py or call with refresh=true for attack-specific ranks.",
            "by_attack": {},
            "attacks": [],
        }
    )
    report = {
        "experiment": "global_and_attack_shap",
        "status": "ok",
        "global": global_imp,
        "attack_specific": attack_imp,
        "samples_explained": len(explanations),
        "cached": False,
    }
    # R-03 (ARCH-18): global_shap_summary.json is a frozen v1.1 artifact. A refresh is computed
    # and returned but never written back (previously any viewer's GET overwrote it).
    report["persisted"] = False
    return report


def experiment_index() -> dict[str, Any]:
    cached = _artifact_json("experiment_index.json")
    if cached:
        return cached
    # Lightweight inline index if script not run yet
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    known = [
        ("EXP-001", "baseline_training", "training_report.json"),
        ("EXP-004", "threshold", "threshold_sweep.json"),
        ("EXP-006", "xai_agreement", "xai_agreement_report.json"),
        ("EXP-008", "drift", "drift_report.json"),
        ("EXP-011", "error_analysis", "error_analysis_report.json"),
        ("EXP-012", "global_shap", "global_shap_summary.json"),
    ]
    items = []
    for eid, name, filename in known:
        path = out_dir / filename
        items.append(
            {
                "experiment_id": eid,
                "name": name,
                "artifact": filename,
                "present": path.exists(),
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "experiments": items,
        "note": "Run scripts/22_write_experiment_index.py for the full index.",
    }


def drift_status() -> dict[str, Any]:
    drift = _artifact_json("drift_report.json")
    if drift is None:
        return {
            "available": False,
            "status": "missing",
            "message": "drift_report.json not found — run scripts/20_data_drift_report.py",
        }
    return {"available": True, **drift}


def run_counterfactual(
    features: dict[str, float],
    *,
    allow_missing_features: bool = False,
    max_edits: int = 5,
) -> dict[str, Any]:
    from explainability.counterfactual import suggest_counterfactuals

    predictor = get_predictor()
    if predictor is None:
        raise RuntimeError("Models not loaded")
    top = None
    try:
        exp = run_explain(
            features, method="shap", top_k=max_edits, allow_missing_features=allow_missing_features
        )
        top = exp.get("top_features")
    except Exception:
        top = None
    return suggest_counterfactuals(
        predictor,
        features,
        top_features=top,
        max_edits=max_edits,
        allow_missing=allow_missing_features,
    )
