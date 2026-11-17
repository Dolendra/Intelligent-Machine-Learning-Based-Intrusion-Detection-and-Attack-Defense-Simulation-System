"""Batch experiment engine for the cyber range (pre-report experiments E6, E7, E8, E10 and a
detector comparison). Each cell of a suite is run for several seeds; results are aggregated as
mean and 95% Student-t interval, and every raw run is kept so the numbers can be audited.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
from itertools import product
from typing import Any, Iterable

import numpy as np
from scipy import stats

from cyberrange.engine import DEFENSES, RangeConfig, run_headless
from cyberrange.scenarios import SCENARIOS
from ids_config import ROOT

EXP_DIR = ROOT / "results" / "cyber_range" / "experiments"
METRICS = [
    "detection_latency_s", "time_to_mitigate_s", "containment_time_s", "recovery_time_s",
    "attack_success_before_defense", "attack_success_after_defense", "mitigation_effectiveness",
    "availability_mean_during_attack", "availability_min_during_attack", "collateral_rate",
    "fpr_flows", "false_incidents", "attack_flow_recall", "attack_flow_recall_frozen", "attack_flow_recall_gate",
    "attackers_detected", "attackers_total", "detected", "wall_seconds", "flows_total",
]
DEFENSE_SET = ["block_source", "rate_limit", "isolate_host", "monitor_only", "increase_inspection"]


_RATE_WORDS = ("rate", "availability", "recall", "effectiveness", "success", "detected", "fpr")


def _ci(values: Iterable[float | None], name: str = "") -> dict[str, Any]:
    """Mean and 95% Student-t interval, clipped to the metric's natural range
    (all range metrics are non-negative; rates and shares are also at most 1)."""
    v = np.array([x for x in values if x is not None and not (isinstance(x, float) and np.isnan(x))], dtype=float)
    if v.size == 0:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0}
    if v.size == 1 or np.allclose(v, v[0]):
        return {"mean": float(v.mean()), "ci_low": float(v.mean()), "ci_high": float(v.mean()), "n": int(v.size)}
    h = stats.sem(v) * stats.t.ppf(0.975, v.size - 1)
    hi_cap = 1.0 if (any(w in name for w in _RATE_WORDS) and name != "false_incidents") else float("inf")
    return {"mean": float(v.mean()), "ci_low": float(max(0.0, v.mean() - h)),
            "ci_high": float(min(hi_cap, v.mean() + h)), "n": int(v.size)}


def run_cells(cells: list[dict[str, Any]], seeds: Iterable[int], base: RangeConfig | None = None,
              *, keep_runs: bool = True) -> dict[str, Any]:
    base = base or RangeConfig()
    seeds = list(seeds)
    out_cells = []
    t0 = time.perf_counter()
    for cell in cells:
        runs = []
        for seed in seeds:
            cfg = replace(base, seed=int(seed), **cell)
            m = run_headless(cfg)
            m["detected"] = 1.0 if m["detection_latency_s"] is not None else 0.0
            runs.append({"seed": int(seed), **m})
        agg = {k: _ci([r.get(k) for r in runs], k) for k in METRICS}
        out_cells.append({"cell": cell, "summary": agg, "runs": runs if keep_runs else None})
    return {"cells": out_cells, "seeds": seeds, "base_config": asdict(base),
            "runtime_seconds": round(time.perf_counter() - t0, 2)}


# ----------------------------------------------------------------------------- suites
def suite_defense(seeds: Iterable[int]) -> dict[str, Any]:
    """E8: every scenario × every defense (auto mode, 3 s approval delay)."""
    cells = [{"scenario": s, "defense": d} for s, d in product(SCENARIOS, DEFENSE_SET)]
    return run_cells(cells, seeds)


def suite_intensity(seeds: Iterable[int]) -> dict[str, Any]:
    """E6: attack intensity low / medium / high with the recommended defense."""
    cells = [{"scenario": s, "intensity": i} for s, i in product(["port_scan", "brute_force", "dos", "ddos", "web_burst"],
                                                                 [0.5, 1.0, 2.0])]
    return run_cells(cells, seeds)


def suite_attackers(seeds: Iterable[int]) -> dict[str, Any]:
    """E7: number of simultaneous DDoS sources."""
    cells = [{"scenario": "ddos", "attackers": n} for n in (1, 2, 4, 8)]
    return run_cells(cells, seeds)


def suite_detector(seeds: Iterable[int]) -> dict[str, Any]:
    """Which detector drives incidents: frozen v1.1, Zero-Day Gate, or their union."""
    cells = [{"scenario": s, "detector": d} for s, d in product(list(SCENARIOS), ["frozen", "gate", "union"])]
    return run_cells(cells, seeds)


def suite_threshold(seeds: Iterable[int]) -> dict[str, Any]:
    """False-positive control: alert threshold k (alerts in 5 s) vs. latency and false incidents."""
    cells = [{"scenario": s, "alert_threshold": k} for s, k in product(["dos", "brute_force", "bot_beacon", "host_discovery"],
                                                                        [1, 2, 3, 5, 8])]
    return run_cells(cells, seeds)


def suite_delay(seeds: Iterable[int]) -> dict[str, Any]:
    """How much the analyst's approval delay costs (time-to-mitigate vs. service impact)."""
    cells = [{"scenario": s, "approval_delay_s": d} for s, d in product(["dos", "ddos"], [0, 3, 10, 30])]
    return run_cells(cells, seeds)


SUITES = {"defense": suite_defense, "intensity": suite_intensity, "attackers": suite_attackers,
          "detector": suite_detector, "threshold": suite_threshold, "delay": suite_delay}


def run_all(names: Iterable[str], seeds: Iterable[int], *, save: bool = True) -> dict[str, Any]:
    seeds = list(seeds)
    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seeds": seeds,
        "defenses": DEFENSES,
        "scenarios": {k: v.to_dict() for k, v in SCENARIOS.items()},
        "suites": {},
        "notes": [
            "Trace-driven range: recorded CICIDS2017 replay flows on a seeded 1 s clock; detector verdicts are computed.",
            "Modelled (not measured): arrival rates, per-family service cost, 20% rate-limit pass-through, target capacity.",
        ],
    }
    for name in names:
        result["suites"][name] = SUITES[name](seeds)
    if save:
        EXP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload = json.dumps(result, default=float)
        (EXP_DIR / f"range_experiments_{stamp}.json").write_text(payload, encoding="utf-8")
        (EXP_DIR / "latest.json").write_text(payload, encoding="utf-8")
    return result


def load_latest() -> dict[str, Any] | None:
    path = EXP_DIR / "latest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
