"""Pydantic schemas for the IDS API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    features: dict[str, float] = Field(..., description="Flow feature map")
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
    threshold: float | None = None
    risk_factors: dict[str, Any] | None = None
    deduplicated: bool | None = None
    source_ref: str | None = None
    campaign_id: str | None = None
    escalated: bool | None = None


class BatchPredictRequest(BaseModel):
    flows: list[dict[str, float]] = Field(..., min_length=1, max_length=500)
    persist: bool = False
    allow_missing_features: bool = False
    asset_criticality: float | None = Field(None, ge=0.0, le=5.0)


class ExplainRequest(BaseModel):
    features: dict[str, float]
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
