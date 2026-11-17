"""Live Traffic Monitor: replay held-out CICIDS2017 flows through the detectors in real time.

Each WebSocket connection gets its own ``LiveSession``. Every tick (0.5 s) it draws flows
according to the active scenario's phase mixture, scores them with

* the **frozen v1.1** detector (Decision Tree @0.85 → attack-only Random Forest), and
* the advisory **Aegis-OSR Zero-Day Gate**,

and pushes a compact message. Because replayed flows carry their ground-truth label, the
stream also reports *outcomes* (caught by both / only by the gate / missed / false alarm),
which makes the value of open-set detection visible during a demo.

This is a replay of recorded dataset flows — not live packet capture.
"""
from __future__ import annotations

import ipaddress
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd

from ids_config import ROOT

POOL_PATH = ROOT / "research_artifacts" / "replay" / "replay_pool.parquet"
TICK_SECONDS = 0.5
MAX_RATE = 200
UNSEEN = {"Infiltration", "Heartbleed"}

# Each phase: (name, seconds, {family: weight}). Weights are normalized per phase.
SCENARIOS: dict[str, dict[str, Any]] = {
    "enterprise_day": {
        "title": "Enterprise workday",
        "description": "Mostly normal traffic with short reconnaissance, brute-force and web-attack bursts.",
        "phases": [
            ("Quiet morning", 14, {"BENIGN": 1.0}),
            ("Reconnaissance", 12, {"BENIGN": 0.82, "PortScan": 0.18}),
            ("Business as usual", 10, {"BENIGN": 1.0}),
            ("Credential stuffing", 12, {"BENIGN": 0.75, "BruteForce": 0.25}),
            ("Web probing", 12, {"BENIGN": 0.88, "WebAttack": 0.12}),
        ],
    },
    "ddos_wave": {
        "title": "DDoS wave",
        "description": "A volumetric attack ramps up, peaks and subsides.",
        "phases": [
            ("Baseline", 10, {"BENIGN": 1.0}),
            ("Ramp-up", 10, {"BENIGN": 0.7, "DDoS": 0.3}),
            ("Peak", 14, {"BENIGN": 0.3, "DDoS": 0.6, "DoS": 0.1}),
            ("Mitigation", 10, {"BENIGN": 0.8, "DDoS": 0.2}),
            ("Recovery", 10, {"BENIGN": 1.0}),
        ],
    },
    "zero_day": {
        "title": "Zero-day intrusion",
        "description": "Never-seen attack families (Infiltration, Heartbleed) hidden in normal traffic. "
                       "The frozen model was never trained on them — watch the Zero-Day Gate.",
        "phases": [
            ("Normal operations", 10, {"BENIGN": 1.0}),
            ("Silent foothold", 14, {"BENIGN": 0.9, "Infiltration": 0.1}),
            ("Memory disclosure", 10, {"BENIGN": 0.92, "Heartbleed": 0.08}),
            ("Mixed activity", 14, {"BENIGN": 0.8, "Infiltration": 0.08, "Bot": 0.12}),
        ],
    },
    "apt_campaign": {
        "title": "Multi-stage campaign",
        "description": "Kill chain: scan → brute force → web exploitation → botnet C2 → lateral infiltration.",
        "phases": [
            ("Recon", 10, {"BENIGN": 0.75, "PortScan": 0.25}),
            ("Initial access", 10, {"BENIGN": 0.75, "BruteForce": 0.25}),
            ("Exploitation", 10, {"BENIGN": 0.85, "WebAttack": 0.15}),
            ("Command & control", 10, {"BENIGN": 0.8, "Bot": 0.2}),
            ("Lateral movement", 12, {"BENIGN": 0.88, "Infiltration": 0.12}),
        ],
    },
}

# Synthetic addressing for visualization only (dataset IPs are dropped as leakage-prone).
_ATTACKERS = {
    "PortScan": "203.0.113.24", "DDoS": "198.51.100.0/27", "DoS": "198.51.100.77",
    "BruteForce": "203.0.113.91", "WebAttack": "192.0.2.150", "Bot": "10.20.4.66",
    "Infiltration": "10.20.7.13", "Heartbleed": "192.0.2.201",
}
_SERVERS = ["10.20.1.10", "10.20.1.11", "10.20.1.20", "10.20.2.5", "10.20.3.8"]


@lru_cache(maxsize=1)
def load_pool() -> dict[str, pd.DataFrame]:
    if not POOL_PATH.exists():
        raise FileNotFoundError(f"Replay pool missing: {POOL_PATH}. Run scripts/52_build_replay_pool.py")
    pool = pd.read_parquet(POOL_PATH)
    return {str(f): g.reset_index(drop=True) for f, g in pool.groupby("family")}


def scenario_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": sid,
            "title": s["title"],
            "description": s["description"],
            "phases": [{"name": n, "seconds": d, "mix": mix} for n, d, mix in s["phases"]],
            "cycle_seconds": sum(d for _, d, _ in s["phases"]),
        }
        for sid, s in SCENARIOS.items()
    ]


def _src_ip(family: str, rng: np.random.Generator) -> str:
    if family == "BENIGN":
        return f"10.20.{rng.integers(1, 9)}.{rng.integers(20, 250)}"
    spec = _ATTACKERS.get(family, "192.0.2.1")
    if "/" in spec:
        net = ipaddress.ip_network(spec)
        return str(net[int(rng.integers(1, net.num_addresses - 1))])
    return spec


@dataclass
class Counters:
    total: int = 0
    attacks_truth: int = 0
    frozen_alerts: int = 0
    gate_alerts: int = 0
    caught_both: int = 0
    caught_frozen_only: int = 0
    caught_gate_only: int = 0
    missed: int = 0
    false_alarm_frozen: int = 0
    false_alarm_gate: int = 0
    novel_flags: int = 0
    unseen_total: int = 0
    unseen_caught_gate: int = 0
    unseen_caught_frozen: int = 0
    by_family: dict[str, dict[str, int]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        benign = max(self.total - self.attacks_truth, 1)
        attacks = max(self.attacks_truth, 1)
        d["rates"] = {
            "frozen_recall": (self.caught_both + self.caught_frozen_only) / attacks,
            "gate_recall": (self.caught_both + self.caught_gate_only) / attacks,
            "combined_recall": (self.caught_both + self.caught_frozen_only + self.caught_gate_only) / attacks,
            "frozen_fpr": self.false_alarm_frozen / benign,
            "gate_fpr": self.false_alarm_gate / benign,
            "unseen_gate_recall": self.unseen_caught_gate / self.unseen_total if self.unseen_total else None,
            "unseen_frozen_recall": self.unseen_caught_frozen / self.unseen_total if self.unseen_total else None,
        }
        return d


class LiveSession:
    def __init__(self, scenario: str = "enterprise_day", rate: int = 20, seed: int | None = None) -> None:
        self.rng = np.random.default_rng(seed)
        self.set(scenario=scenario, rate=rate)
        self.paused = False
        self.seq = 0
        self.flow_id = 0
        self.counters = Counters()
        self.started = time.time()
        self.elapsed = 0.0  # scenario clock (advances only while running)

    def set(self, *, scenario: str | None = None, rate: int | None = None) -> None:
        if scenario is not None:
            if scenario not in SCENARIOS:
                raise ValueError(f"Unknown scenario {scenario!r}")
            self.scenario = scenario
            self.elapsed = 0.0
        if rate is not None:
            self.rate = int(min(max(rate, 1), MAX_RATE))

    def reset(self) -> None:
        self.counters = Counters()
        self.elapsed = 0.0
        self.seq = 0

    def _phase(self) -> tuple[int, str, float, dict[str, float]]:
        phases = SCENARIOS[self.scenario]["phases"]
        cycle = sum(d for _, d, _ in phases)
        t = self.elapsed % cycle
        for i, (name, dur, mix) in enumerate(phases):
            if t < dur:
                return i, name, t / dur, mix
            t -= dur
        name, _, mix = phases[-1]
        return len(phases) - 1, name, 1.0, mix

    def _draw(self, n: int, mix: dict[str, float]) -> pd.DataFrame:
        pool = load_pool()
        fams = [f for f in mix if f in pool]
        w = np.array([mix[f] for f in fams], dtype=float)
        picks = self.rng.choice(len(fams), size=n, p=w / w.sum())
        rows = []
        for j in np.unique(picks):
            fam = fams[j]
            k = int((picks == j).sum())
            g = pool[fam]
            rows.append(g.iloc[self.rng.integers(0, len(g), size=k)])
        out = pd.concat(rows, ignore_index=True)
        return out.iloc[self.rng.permutation(len(out))].reset_index(drop=True)

    def tick(self) -> dict[str, Any]:
        from backend.services.pipeline import get_predictor
        from research.serving import get_gate
        from security.risk.engine import compute_risk

        idx, name, progress, mix = self._phase()
        if self.paused:
            return {"type": "tick", "paused": True, "seq": self.seq, "scenario": self.scenario,
                    "phase": {"index": idx, "name": name, "progress": progress},
                    "flows": [], "stats": self.counters.as_dict()}

        # Poisson arrivals around the configured rate (at least one flow keeps the UI alive)
        n = max(1, int(self.rng.poisson(self.rate * TICK_SECONDS)))
        batch = self._draw(n, mix)
        truth = batch["family"].astype(str).to_numpy()

        predictor = get_predictor()
        frozen = predictor.predict_many_vectorized(batch) if predictor is not None else []
        gate = get_gate()
        gate_res = gate.assess(batch, explain_top=3) if gate is not None else [None] * n

        flows: list[dict[str, Any]] = []
        c = self.counters
        now = time.time()
        for i in range(n):
            fam = truth[i]
            is_attack_truth = fam != "BENIGN"
            fp = frozen[i] if frozen else None
            f_alert = bool(fp.is_attack) if fp is not None else False
            g = gate_res[i]
            g_alert = bool(g["alert"]) if g else False
            confidence = (fp.multiclass_confidence if f_alert else fp.binary_confidence) if fp is not None else 0.0
            risk = compute_risk(fp.attack_type, confidence, f_alert) if fp is not None else {"score": 0, "severity": "LOW"}
            if is_attack_truth:
                outcome = ("caught_both" if f_alert and g_alert else "caught_frozen_only" if f_alert
                           else "caught_gate_only" if g_alert else "missed")
            else:
                outcome = "false_alarm" if (f_alert or g_alert) else "clean"

            c.total += 1
            c.frozen_alerts += f_alert
            c.gate_alerts += g_alert
            c.novel_flags += bool(g and g["novel"])
            fam_stats = c.by_family.setdefault(fam, {"n": 0, "frozen": 0, "gate": 0})
            fam_stats["n"] += 1
            fam_stats["frozen"] += f_alert
            fam_stats["gate"] += g_alert
            if is_attack_truth:
                c.attacks_truth += 1
                setattr(c, outcome, getattr(c, outcome) + 1)
                if fam in UNSEEN:
                    c.unseen_total += 1
                    c.unseen_caught_gate += g_alert
                    c.unseen_caught_frozen += f_alert
            else:
                c.false_alarm_frozen += f_alert
                c.false_alarm_gate += g_alert

            self.flow_id += 1
            flows.append({
                "id": self.flow_id,
                "ts": now + (i / max(n, 1)) * TICK_SECONDS,
                "src": _src_ip(fam, self.rng),
                "dst": _SERVERS[int(self.rng.integers(0, len(_SERVERS)))],
                "dst_port": int(batch.at[i, "Destination Port"]),
                "bytes": float(batch.at[i, "Total Length of Fwd Packets"] + batch.at[i, "Total Length of Bwd Packets"]),
                "duration_ms": float(batch.at[i, "Flow Duration"]) / 1000.0,
                "truth": fam,
                "unseen_family": fam in UNSEEN,
                "frozen": {
                    "is_attack": f_alert,
                    "attack_type": fp.attack_type if fp is not None else None,
                    "confidence": float(confidence),
                    "risk_score": float(risk.get("score", 0)),
                    "severity": risk.get("severity"),
                },
                "gate": None if g is None else {
                    "label": g["label"], "alert": g_alert, "novel": g["novel"], "p_value": g["p_value"],
                    "summary": g["summary"], "top_deviations": g["top_deviations"],
                },
                "outcome": outcome,
            })

        self.seq += 1
        self.elapsed += TICK_SECONDS
        return {
            "type": "tick",
            "paused": False,
            "seq": self.seq,
            "ts": now,
            "scenario": self.scenario,
            "rate": self.rate,
            "phase": {"index": idx, "name": name, "progress": progress, "mix": mix},
            "flows": flows,
            "stats": c.as_dict(),
            "models": {"frozen": predictor is not None, "gate": gate is not None},
        }
