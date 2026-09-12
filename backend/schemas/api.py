"""Pydantic schemas for the IDS API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    features: dict[str, float] = Field(..., description="Flow feature map")
    persist: bool = True


class PredictResponse(BaseModel):
    is_attack: bool
    attack_type: str
    confidence: float
    binary_proba_attack: float
    class_probabilities: dict[str, float]
    risk_score: float
    severity: str
    recommendation: dict[str, Any]
    incident_id: str | None = None


class ExplainRequest(BaseModel):
    features: dict[str, float]
    top_k: int = 10
    method: str = Field("shap", description="Explainability method: shap (primary) or lime")


class RiskRequest(BaseModel):
    attack_type: str
    confidence: float
    is_attack: bool = True
    traffic_intensity: float | None = None


class RecommendationRequest(BaseModel):
    attack_type: str
    severity: str | None = None


class SimulationStartRequest(BaseModel):
    attack_type: str = "DDoS"
    confidence: float = 0.96


class SimulationAdvanceRequest(BaseModel):
    session_id: str
    action: str | None = None


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    version: str
