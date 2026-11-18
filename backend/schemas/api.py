"""Pydantic schemas for the IDS API."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field

# R-11 (ML-8): flow features must be finite. JSON NaN/Infinity used to reach the model and
# surface as a 500; they are now a 422 validation error, consistent with training (which
# dropped non-finite rows) and with the per-row policy for CSV/PCAP ingestion.
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]


class PredictRequest(BaseModel):
    features: dict[str, FiniteFloat] = Field(..., description="Flow feature map")
    persist: bool = True
    allow_missing_features: bool = Field(
        False,
        description="Demo-only: fill missing features with 0. Production should keep false.",
    )
    asset_criticality: float | None = Field(
        None,
        ge=0.0,
        le=5.0,
        description="Affected asset criticality 0–1 or 1–5",
    )
    source_ref: str | None = Field(
        None,
        max_length=128,
        description="Optional source/target fingerprint for incident deduplication",
    )
    asset_id: str | None = Field(None, max_length=64, description="Asset inventory id")


class PredictResponse(BaseModel):
    is_attack: bool
    attack_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    binary_proba_attack: float = Field(..., ge=0.0, le=1.0)
    class_probabilities: dict[str, float]
    risk_score: float = Field(..., ge=0.0, le=100.0)
    severity: str
    recommendation: dict[str, Any]
    incident_id: str | None = None
    certainty: str | None = None
    confidence_band: str | None = None
    confidence_band_label: str | None = None
    threshold: float | None = None
    uncertainty_lower: float | None = None
    uncertainty_upper: float | None = None
    threshold_note: str | None = None
    risk_factors: dict[str, Any] | None = None
    risk_contributions: dict[str, Any] | None = None
    risk_why: str | None = None
    deduplicated: bool | None = None
    source_ref: str | None = None
    campaign_id: str | None = None
    escalated: bool | None = None
    decision_trace: dict[str, Any] | None = None
    intensity_method: str | None = None
    # v3 advisory Aegis-OSR Zero-Day Gate (None when artifacts are unavailable)
    zero_day: dict[str, Any] | None = None
    zero_day_status: str | None = None
    # R-11 (ML-14): which required features were absent (zero-filled, development demo only)
    missing_features: list[str] = Field(default_factory=list)
    prediction_quality: str | None = None
    # R1a: shared incident policy outcome (security.detection_policy.decide)
    detection_decision: dict[str, Any] | None = None
    # risk/playbook of a gate-only incident (frozen-verdict fields above stay untouched)
    incident_risk: dict[str, Any] | None = None


class BatchPredictRequest(BaseModel):
    flows: list[dict[str, FiniteFloat]] = Field(..., min_length=1, max_length=500)
    persist: bool = False
    allow_missing_features: bool = False
    asset_criticality: float | None = Field(None, ge=0.0, le=5.0)


class ExplainRequest(BaseModel):
    features: dict[str, FiniteFloat]
    top_k: int = Field(10, ge=1, le=50)
    method: str = Field("shap", description="Explainability method: shap (primary) or lime")
    allow_missing_features: bool = False


class RiskRequest(BaseModel):
    attack_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_attack: bool = True
    traffic_intensity: float | None = Field(None, ge=0.0, le=1.0)
    asset_criticality: float | None = Field(None, ge=0.0, le=5.0)


class RecommendationRequest(BaseModel):
    attack_type: str
    severity: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    traffic_intensity: float | None = Field(None, ge=0.0, le=1.0)
    certainty: str | None = None
    is_attack: bool | None = None


class ControlledResponsePlanRequest(BaseModel):
    """Stage-2 Phase D controlled-response plan (advisory / simulation only)."""

    attack_type: str
    severity: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    traffic_intensity: float | None = Field(None, ge=0.0, le=1.0)
    certainty: str | None = None
    is_attack: bool | None = None
    asset_criticality: float | None = Field(None, ge=0.0, le=5.0)
    risk_score: float | None = Field(None, ge=0.0, le=100.0)
    start_simulation: bool = False
    incident_id: str | None = None


class ResponseActionProposeRequest(BaseModel):
    """Propose an abstract response action (DRY_RUN or CONTROLLED test adapter)."""

    attack_type: str
    incident_id: str | None = None
    severity: str | None = None
    risk_score: float | None = Field(None, ge=0.0, le=100.0)
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    source_ip: str | None = Field(None, max_length=128)
    host: str | None = Field(None, max_length=256)
    target: str | None = Field(None, max_length=256)
    action_type: str | None = None
    reason: str | None = Field(None, max_length=2000)
    duration_minutes: int | None = Field(None, ge=0, le=1440)
    mode: str = "DRY_RUN"
    adapter: str | None = None


class ResponseActionDecisionRequest(BaseModel):
    reason: str | None = Field(None, max_length=2000)
    actor: str | None = Field(None, max_length=128)


class IncidentUpdateRequest(BaseModel):
    status: str
    analyst_notes: str | None = None
    defense_action: str | None = None


class SimulationStartRequest(BaseModel):
    attack_type: str = "DDoS"
    confidence: float = Field(0.96, ge=0.0, le=1.0)
    incident_id: str | None = None
    traffic_intensity: float | None = Field(
        None, ge=0.0, le=1.0, description="Configured attack intensity 0–1 (simulation)"
    )
    asset_criticality: float | None = Field(None, ge=0.0, le=5.0)
    risk_score: float | None = Field(None, ge=0.0, le=100.0)
    severity: str | None = None
    source_ref: str | None = Field(None, max_length=128)


class SimulationFromPredictionRequest(BaseModel):
    incident_id: str | None = None
    attack_type: str | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    risk_score: float | None = Field(None, ge=0.0, le=100.0)
    severity: str | None = None


class SimulationAdvanceRequest(BaseModel):
    session_id: str
    action: str | None = None


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    version: str


class ZeroDayAssessRequest(BaseModel):
    flows: list[dict[str, FiniteFloat]] = Field(..., min_length=1, max_length=500)
    alpha: float | None = Field(None, gt=0.0, le=0.2, description="Benign false-alarm budget (conformal)")
    explain_top: int = Field(5, ge=0, le=20)
