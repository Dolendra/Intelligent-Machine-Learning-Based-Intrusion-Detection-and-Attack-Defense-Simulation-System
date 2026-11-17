"""Cyber-range API: create, step, respond to and inspect trace-driven attack/defense runs."""
from __future__ import annotations

from dataclasses import fields
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cyberrange.engine import DEFENSES, DETECTORS, RangeConfig, range_manager
from cyberrange.scenarios import catalog

router = APIRouter(prefix="/range", tags=["cyber-range"])

MAX_SWEEP_RUNS = 60


class RangeRunRequest(BaseModel):
    scenario: str = "dos"
    seed: int = Field(1, ge=0, le=1_000_000)
    intensity: float = Field(1.0, ge=0.1, le=5.0)
    attackers: int | None = Field(None, ge=1, le=8)
    detector: str = "union"
    alert_threshold: int = Field(3, ge=1, le=20)
    alert_window_s: int = Field(5, ge=1, le=30)
    response_mode: str = "manual"
    defense: str = "recommended"
    approval_delay_s: int = Field(3, ge=0, le=60)
    benign_rate: float = Field(30.0, ge=1.0, le=200.0)
    capacity: float = Field(60.0, ge=5.0, le=1000.0)
    duration_s: int | None = Field(None, ge=20, le=600)
    explain: bool = True

    def to_config(self) -> RangeConfig:
        names = {f.name for f in fields(RangeConfig)}
        return RangeConfig(**{k: v for k, v in self.model_dump().items() if k in names})


class StepRequest(BaseModel):
    seconds: int = Field(1, ge=1, le=600)


class RespondRequest(BaseModel):
    action: str


class SweepRequest(BaseModel):
    """A small, bounded experiment the UI can run on demand (heavy suites use scripts/56)."""

    scenarios: list[str] = Field(default_factory=lambda: ["dos"], min_length=1, max_length=9)
    defenses: list[str] = Field(default_factory=lambda: ["block_source", "rate_limit", "isolate_host", "monitor_only"],
                                min_length=1, max_length=7)
    seeds: list[int] = Field(default_factory=lambda: [1, 2, 3], min_length=1, max_length=10)
    detector: str = "union"
    intensity: float = Field(1.0, ge=0.1, le=5.0)
    approval_delay_s: int = Field(3, ge=0, le=60)


def _bad(exc: Exception, code: str = "BAD_REQUEST", status: int = 422) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": str(exc)})


@router.get("/scenarios")
def range_scenarios() -> dict[str, Any]:
    return {"items": catalog(), "defenses": DEFENSES, "detectors": list(DETECTORS)}


@router.get("/runs")
def range_runs() -> dict[str, Any]:
    return {"items": range_manager.recent()}


@router.post("/runs")
def range_create(body: RangeRunRequest) -> dict[str, Any]:
    try:
        run = range_manager.create(body.to_config())
    except (KeyError, ValueError) as exc:
        raise _bad(exc) from exc
    except FileNotFoundError as exc:
        raise _bad(exc, "RANGE_UNAVAILABLE", 503) from exc
    return run.view()


@router.get("/runs/{run_id}")
def range_get(run_id: str) -> dict[str, Any]:
    try:
        return range_manager.get(run_id).view()
    except KeyError as exc:
        raise _bad(exc, "NOT_FOUND", 404) from exc


@router.post("/runs/{run_id}/step")
def range_step(run_id: str, body: StepRequest) -> dict[str, Any]:
    try:
        return range_manager.get(run_id).step(body.seconds)
    except KeyError as exc:
        raise _bad(exc, "NOT_FOUND", 404) from exc


@router.post("/runs/{run_id}/respond")
def range_respond(run_id: str, body: RespondRequest) -> dict[str, Any]:
    try:
        return range_manager.get(run_id).respond(body.action)
    except KeyError as exc:
        raise _bad(exc, "NOT_FOUND", 404) from exc
    except ValueError as exc:
        raise _bad(exc, "INVALID_RESPONSE", 409) from exc


@router.post("/runs/{run_id}/complete")
def range_complete(run_id: str) -> dict[str, Any]:
    try:
        return range_manager.get(run_id).complete()
    except KeyError as exc:
        raise _bad(exc, "NOT_FOUND", 404) from exc


@router.get("/experiments/latest")
def range_experiments_latest() -> dict[str, Any]:
    from cyberrange.experiments import load_latest

    data = load_latest()
    if data is None:
        raise HTTPException(status_code=404, detail={
            "code": "NOT_GENERATED", "message": "No experiment results yet. Run: python scripts/56_cyber_range_experiments.py"})
    for suite in data.get("suites", {}).values():  # keep the payload small: drop raw runs
        for cell in suite.get("cells", []):
            cell.pop("runs", None)
    return data


@router.post("/experiments/sweep")
def range_sweep(body: SweepRequest) -> dict[str, Any]:
    from cyberrange.experiments import run_cells

    n = len(body.scenarios) * len(body.defenses) * len(body.seeds)
    if n > MAX_SWEEP_RUNS:
        raise _bad(ValueError(f"Sweep too large ({n} runs > {MAX_SWEEP_RUNS}). Use scripts/56 for big suites."))
    for d in body.defenses:
        if d not in DEFENSES:
            raise _bad(ValueError(f"Unknown defense {d!r}"))
    try:
        cells = [{"scenario": s, "defense": d} for s in body.scenarios for d in body.defenses]
        base = RangeConfig(detector=body.detector, intensity=body.intensity, approval_delay_s=body.approval_delay_s)
        res = run_cells(cells, body.seeds, base.validate(), keep_runs=False)
    except (KeyError, ValueError) as exc:
        raise _bad(exc) from exc
    return res
