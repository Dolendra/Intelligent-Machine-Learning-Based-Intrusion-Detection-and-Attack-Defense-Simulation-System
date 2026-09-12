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


class RecommendationRequest(BaseModel):
    attack_type: str
    severity: str | None = None


class SimulationStartRequest(BaseModel):
    attack_type: str = "DDoS"
    confidence: float = Field(0.96, ge=0.0, le=1.0)
    incident_id: str | None = None


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
