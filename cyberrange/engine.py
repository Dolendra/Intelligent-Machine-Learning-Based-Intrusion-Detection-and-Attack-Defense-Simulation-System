"""Trace-driven cyber range: a reproducible attack → detect → explain → respond → measure loop.

Why trace-driven
----------------
The locked design asks for a simulator that is a *laboratory*, not an animation: every state the UI
shows must come from simulated traffic, real detector output and measured outcomes. Mininet needs a
Linux host; this range runs anywhere. Instead of synthesising packets, it **replays recorded
CICIDS2017 flows** (benign background plus the scenario's attack families) on a seeded,
discrete simulation clock (1 s ticks) and pushes every flow through:

1. a firewall that applies whichever controls are active (block / rate-limit / isolate),
2. the real detectors — the frozen v1.1 model and the Aegis-OSR Zero-Day Gate — whose verdicts
   are *computed*, not scripted,
3. an alert aggregator: a source becomes an incident after ``k`` alerts within ``W`` seconds,
4. a capacity model of the target service, which turns surviving traffic into service availability.

Detection latency, mitigation latency, attack success, collateral damage, false incidents and
recovery time are therefore *measured inside the range*. What is modelled (and documented as such):
flow arrival rates, the per-family service cost of a flow, and the 20% pass-through of a rate limit.

Every random choice comes from ``numpy.random.default_rng(seed)``: the same configuration and
seed reproduce the same run exactly.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cyberrange.scenarios import FLOW_COST, UNSEEN_FAMILIES, Scenario, get_scenario
from ids_config import ROOT

POOL_PATH = ROOT / "research_artifacts" / "replay" / "replay_pool.parquet"
# Overridable so the test suite never writes into the committed results directory.
RUNS_DIR = Path(os.environ.get("AEGIS_RANGE_RUNS_DIR") or ROOT / "results" / "cyber_range" / "runs")
EVENT_SCHEMA_VERSION = 1
RATE_LIMIT_PASS = 0.2  # a rate-limited source keeps 20% of its flows (model parameter)
TAIL_SECONDS = 25      # observation time after the attacker stops
RECENT_FLOWS = 80

DEFENSES: dict[str, dict[str, str]] = {
    "recommended": {"title": "Recommended", "effect": "Apply the response the playbook recommends for the detected family."},
    "block_source": {"title": "Block source", "effect": "Firewall drops every flow from each detected source."},
    "rate_limit": {"title": "Rate limit", "effect": "Each detected source keeps only 20% of its flows."},
    "isolate_host": {"title": "Isolate target", "effect": "Cut the target server off the network until the attack stops (5 s quiet)."},
    "monitor_only": {"title": "Monitor only", "effect": "No control change; the attack continues and is only watched."},
    "increase_inspection": {"title": "Increase inspection", "effect": "Use both detectors and alert on a single hit; no blocking."},
    "none": {"title": "No action", "effect": "Ignore the alert."},
}
RECOMMENDED: dict[str, str] = {
    "DoS": "rate_limit", "BruteForce": "rate_limit", "DDoS": "block_source", "PortScan": "block_source",
    "WebAttack": "block_source", "Bot": "block_source", "Infiltration": "block_source", "Heartbleed": "block_source",
    # Gate-only incidents cannot be named; containing the alerting source is the conservative default.
    "Zero-Day Candidate": "block_source",
}
DETECTORS = ("frozen", "gate", "union")  # == security.detection_policy.POLICIES


def _default_policy() -> str:
    from security.detection_policy import configured_policy

    return configured_policy()

CLIENTS = [f"10.20.{3 + i // 20}.{20 + i % 20 * 7}" for i in range(40)]
EXTERNAL_ATTACKERS = ["203.0.113.24", "198.51.100.17", "198.51.100.44", "198.51.100.71",
                      "198.51.100.98", "198.51.100.125", "198.51.100.152", "198.51.100.179"]
INTERNAL_ATTACKER = "10.20.7.13"
SERVERS = {"web": "10.20.1.10", "auth": "10.20.1.20", "db": "10.20.2.5", "files": "10.20.2.9"}


# ----------------------------------------------------------------------------- scored pool
@dataclass
class ScoredPool:
    """Every replay flow scored once by both detectors (deterministic, so caching is exact)."""

    frame: pd.DataFrame
    family: np.ndarray
    frozen_alert: np.ndarray
    frozen_type: np.ndarray
    frozen_conf: np.ndarray
    gate_alert: np.ndarray
    gate_label: np.ndarray
    gate_p: np.ndarray
    by_family: dict[str, np.ndarray]
    models: dict[str, bool]


class ModelsUnavailable(FileNotFoundError):
    """Raised instead of silently scoring every flow as benign when a detector cannot load."""


@lru_cache(maxsize=1)
def scored_pool() -> ScoredPool:
    from backend.services.pipeline import get_predictor
    from research.serving import get_gate

    if not POOL_PATH.exists():
        raise FileNotFoundError(f"Replay pool missing: {POOL_PATH}. Run scripts/52_build_replay_pool.py")
    pool = pd.read_parquet(POOL_PATH).reset_index(drop=True)
    n = len(pool)
    fam = pool["family"].astype(str).to_numpy()
    predictor = get_predictor()
    gate = get_gate()
    missing = [name for name, obj in (("frozen v1.1", predictor), ("Zero-Day Gate", gate)) if obj is None]
    if missing:
        # Measured results are meaningless with a silent all-benign detector, so refuse to run.
        raise ModelsUnavailable(f"Cyber Range needs both detectors; unavailable: {', '.join(missing)}")
    if predictor is not None:
        preds = predictor.predict_many_vectorized(pool)
        f_alert = np.array([bool(p.is_attack) for p in preds])
        f_type = np.array([str(p.attack_type) for p in preds], dtype=object)
        f_conf = np.array([float(p.multiclass_confidence if p.is_attack else p.binary_confidence) for p in preds])
    else:
        f_alert, f_type, f_conf = np.zeros(n, bool), np.full(n, "BENIGN", dtype=object), np.ones(n)
    if gate is not None:
        res = []
        for s in range(0, n, 4000):
            res += gate.assess(pool.iloc[s:s + 4000], explain_top=0)
        g_alert = np.array([r["alert"] for r in res])
        g_label = np.array([r["label"] for r in res], dtype=object)
        g_p = np.array([r["p_value"] for r in res])
    else:
        g_alert, g_label, g_p = np.zeros(n, bool), np.full(n, "BENIGN", dtype=object), np.ones(n)
    by_family = {str(f): np.flatnonzero(fam == f) for f in np.unique(fam)}
    return ScoredPool(pool, fam, f_alert, f_type, f_conf, g_alert, g_label, g_p, by_family,
                      {"frozen": predictor is not None, "gate": gate is not None})


# ----------------------------------------------------------------------------- configuration
@dataclass
class RangeConfig:
    scenario: str = "dos"
    seed: int = 1
    intensity: float = 1.0          # multiplier on the scenario's attack rate
    attackers: int | None = None    # override the scenario's number of attacking sources
    detector: str = field(default_factory=lambda: _default_policy())  # frozen | gate | union (shared policy)
    alert_threshold: int = 3        # k alerts ...
    alert_window_s: int = 5         # ... within W seconds make a source an incident
    response_mode: str = "auto"     # auto: apply `defense` after the approval delay; manual: wait for respond()
    defense: str = "recommended"
    approval_delay_s: int = 3       # analyst decision time in auto mode
    benign_rate: float = 30.0       # background flows per second (whole network)
    target_share: float = 0.5       # fraction of benign flows addressed to the target service
    capacity: float = 60.0          # service units per second the target can serve
    duration_s: int | None = None   # default: scenario length + 25 s tail
    explain: bool = True

    def validate(self) -> "RangeConfig":
        get_scenario(self.scenario)
        if self.detector not in DETECTORS:
            raise ValueError(f"detector must be one of {DETECTORS}")
        if self.defense not in DEFENSES:
            raise ValueError(f"defense must be one of {sorted(DEFENSES)}")
        if self.response_mode not in ("auto", "manual"):
            raise ValueError("response_mode must be 'auto' or 'manual'")
        self.intensity = float(min(max(self.intensity, 0.1), 5.0))
        if self.attackers is not None:
            self.attackers = int(min(max(self.attackers, 1), len(EXTERNAL_ATTACKERS)))
        self.alert_threshold = int(min(max(self.alert_threshold, 1), 20))
        self.alert_window_s = int(min(max(self.alert_window_s, 1), 30))
        self.approval_delay_s = int(min(max(self.approval_delay_s, 0), 60))
        self.benign_rate = float(min(max(self.benign_rate, 1.0), 200.0))
        self.target_share = float(min(max(self.target_share, 0.05), 1.0))
        self.capacity = float(min(max(self.capacity, 5.0), 1000.0))
        if self.duration_s is not None:
            self.duration_s = int(min(max(self.duration_s, 20), 600))
        return self


# ----------------------------------------------------------------------------- run
@dataclass
class Source:
    ip: str
    is_attacker: bool
    alerts: deque = field(default_factory=deque)
    detected_at: int | None = None
    first_alert_at: int | None = None


class RangeRun:
    def __init__(self, config: RangeConfig) -> None:
        self.config = config.validate()
        self.scenario: Scenario = get_scenario(config.scenario)
        self.id = str(uuid.uuid4())
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.rng = np.random.default_rng(config.seed)
        self.pool = scored_pool()
        sc = self.scenario
        n_att = config.attackers or sc.attackers
        if sc.internal_attacker:
            self.attacker_ips = [INTERNAL_ATTACKER] + EXTERNAL_ATTACKERS[: n_att - 1]
        else:
            self.attacker_ips = EXTERNAL_ATTACKERS[:n_att]
        self.target = sc.target
        self.schedule: list[tuple[int, int, Any]] = []
        t = 0
        for st in sc.stages:
            self.schedule.append((t, t + st.seconds, st))
            t += st.seconds
        self.attack_end = t
        self.attack_start = next((a for a, _, st in self.schedule if st.rate > 0), t)
        self.duration = config.duration_s or (t + TAIL_SECONDS)

        self.t = 0
        self.seq = 0
        self.state = "NORMAL"
        self.stage = "NORMAL"
        self.events: list[dict[str, Any]] = []
        self.telemetry: list[dict[str, Any]] = []
        self.recent: deque = deque(maxlen=RECENT_FLOWS)
        self.sources: dict[str, Source] = {ip: Source(ip, True) for ip in self.attacker_ips}
        self.controls: dict[str, Any] = {"policy": None, "blocked": set(), "rate_limited": set(),
                                         "isolated": False, "inspection": False}
        self.marks: dict[str, int | None] = {k: None for k in (
            "attack_start", "suspicious", "detected", "explained", "response_options", "defense",
            "contained", "recovered", "isolation_lifted", "completed")}
        self.awaiting_decision = False
        self.recommended = RECOMMENDED.get(sc.family, "block_source")
        self.chosen: str | None = None
        self.detected_family: str | None = None
        self.explanation: dict[str, Any] | None = None
        self.acc = {k: 0 for k in (
            "benign_sent", "benign_scored", "benign_blocked", "fp_alerts_frozen", "fp_alerts_gate", "fp_alerts",
            "attack_sent", "attack_passed", "attack_blocked", "attack_scored", "attack_alerts", "attack_alerts_frozen",
            "attack_alerts_gate", "unseen_sent", "unseen_alert_frozen", "unseen_alert_gate",
            "attack_sent_pre", "attack_passed_pre", "attack_sent_post", "attack_passed_post")}
        self.last_attack_attempt: int | None = None
        self._pending_explain: int | None = None
        self._lock = threading.Lock()
        self._emit("simulation.started", {"config": asdict(self.config), "scenario": sc.to_dict(),
                                          "attackers": self.attacker_ips, "duration_s": self.duration})
        self._emit("topology.ready", {"nodes": len(self.topology()["nodes"])})

    # ------------------------------------------------------------------ helpers
    @property
    def done(self) -> bool:
        return self.t >= self.duration

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        self.seq += 1
        self.events.append({
            "event_id": str(uuid.uuid4()), "run_id": self.id, "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(), "sim_time_s": self.t,
            "source": "cyber_range", "sequence": self.seq, "schema_version": EVENT_SCHEMA_VERSION,
            "payload": payload,
        })

    def _set_state(self, state: str, detail: str = "") -> None:
        if state != self.state:
            prev, self.state = self.state, state
            self._emit("run.state_changed", {"from": prev, "to": state, "detail": detail})

    def _stage_at(self, t: int):
        for a, b, st in self.schedule:
            if a <= t < b:
                return st
        return None

    def _draw(self, families: dict[str, float], n: int) -> np.ndarray:
        fams = [f for f in families if f in self.pool.by_family]
        if not fams or n <= 0:
            return np.zeros(0, dtype=int)
        w = np.array([families[f] for f in fams], dtype=float)
        picks = self.rng.choice(len(fams), size=n, p=w / w.sum())
        out = np.empty(n, dtype=int)
        for j, f in enumerate(fams):
            m = picks == j
            if m.any():
                idx = self.pool.by_family[f]
                out[m] = idx[self.rng.integers(0, len(idx), size=int(m.sum()))]
        return out

    def _decision(self, i: int):
        """Same incident semantics as the operational API (security.detection_policy.decide)."""
        from security.detection_policy import decide

        mode = "union" if self.controls["inspection"] else self.config.detector
        return decide(bool(self.pool.frozen_alert[i]), str(self.pool.frozen_type[i]),
                      bool(self.pool.gate_alert[i]), str(self.pool.gate_label[i]), mode)

    def _alert(self, i: int) -> tuple[bool, bool, bool]:
        f, g = bool(self.pool.frozen_alert[i]), bool(self.pool.gate_alert[i])
        return self._decision(i).raises_incident, f, g

    # ------------------------------------------------------------------ one simulated second
    def _tick(self) -> None:
        cfg, t, pool = self.config, self.t, self.pool
        st = self._stage_at(t)
        stage = st.name if st is not None else ("ATTACK_ENDED" if t >= self.attack_end else "NORMAL")
        if stage != self.stage:
            self.stage = stage
            self._emit("attack.stage_changed", {"stage": stage, "ground_truth": True})

        flows: list[tuple[str, str, int, bool]] = []  # (src, dst_role, pool_idx, is_attack)
        n_b = int(self.rng.poisson(cfg.benign_rate))
        for i in self._draw({"BENIGN": 1.0}, n_b):
            dst = self.target if self.rng.random() < cfg.target_share else str(self.rng.choice(["db", "files", "auth" if self.target != "auth" else "web"]))
            flows.append((CLIENTS[int(self.rng.integers(0, len(CLIENTS)))], dst, int(i), False))
        if st is not None and st.rate > 0:
            if self.marks["attack_start"] is None:
                self.marks["attack_start"] = t
            for ip in self.attacker_ips:
                n_a = int(self.rng.poisson(self.scenario.base_rate * cfg.intensity * st.rate))
                for i in self._draw(st.families, n_a):
                    flows.append((ip, self.target, int(i), True))
            self.last_attack_attempt = t
        order = self.rng.permutation(len(flows))

        c = self.controls
        tel = {"t": t, "stage": stage, "state": self.state, "benign_target": 0, "benign_served": 0.0,
               "benign_blocked": 0, "attack_sent": 0, "attack_passed": 0, "attack_blocked": 0,
               "alerts_true": 0, "alerts_false": 0, "load_units": 0.0}
        new_detections: list[Source] = []
        units = 0.0
        benign_target_passed = 0
        defended = self.marks["defense"] is not None
        for j in order:
            src, dst, i, is_att = flows[j]
            fam = str(pool.family[i])
            blocked = False
            if c["isolated"] and dst == self.target:
                blocked = True
            elif src in c["blocked"]:
                blocked = True
            elif src in c["rate_limited"] and self.rng.random() >= RATE_LIMIT_PASS:
                blocked = True
            a = self.acc
            if is_att:
                a["attack_sent"] += 1
                tel["attack_sent"] += 1
                a["attack_sent_post" if defended else "attack_sent_pre"] += 1
                if fam in UNSEEN_FAMILIES:
                    a["unseen_sent"] += 1
            else:
                a["benign_sent"] += 1
                if dst == self.target:
                    tel["benign_target"] += 1
            if blocked:
                if is_att:
                    a["attack_blocked"] += 1
                    tel["attack_blocked"] += 1
                else:
                    a["benign_blocked"] += 1
                    tel["benign_blocked"] += 1
                self.recent.append(self._flow_row(t, src, dst, i, is_att, "blocked", None))
                continue
            alert, f_al, g_al = self._alert(i)
            if is_att:
                a["attack_passed"] += 1
                tel["attack_passed"] += 1
                a["attack_passed_post" if defended else "attack_passed_pre"] += 1
                a["attack_scored"] += 1
                a["attack_alerts"] += alert
                a["attack_alerts_frozen"] += f_al
                a["attack_alerts_gate"] += g_al
                if fam in UNSEEN_FAMILIES:
                    a["unseen_alert_frozen"] += f_al
                    a["unseen_alert_gate"] += g_al
                tel["alerts_true"] += alert
            else:
                a["benign_scored"] += 1
                a["fp_alerts"] += alert
                a["fp_alerts_frozen"] += f_al
                a["fp_alerts_gate"] += g_al
                tel["alerts_false"] += alert
            if dst == self.target:
                units += FLOW_COST.get(fam, 1.0)
                if not is_att:
                    benign_target_passed += 1
            if alert:
                s = self.sources.setdefault(src, Source(src, is_att))
                s.alerts.append(t)
                if s.first_alert_at is None:
                    s.first_alert_at = t
                while s.alerts and s.alerts[0] <= t - cfg.alert_window_s:
                    s.alerts.popleft()
                k = 1 if c["inspection"] else cfg.alert_threshold
                if s.detected_at is None and len(s.alerts) >= k:
                    s.detected_at = t
                    new_detections.append(s)
                    if s.is_attacker and self.explanation is None:
                        self._pending_explain = i
                    if s.is_attacker and self.detected_family is None:
                        # frozen family if the frozen model alerted, else "Zero-Day Candidate" (never the truth)
                        self.detected_family = str(self._decision(i).incident_label)
            self.recent.append(self._flow_row(t, src, dst, i, is_att, "alert" if alert else "passed", (f_al, g_al)))

        # service model: the target serves min(1, capacity / load) of what reaches it
        served_frac = 1.0 if units <= cfg.capacity else cfg.capacity / units
        tel["load_units"] = round(units, 2)
        tel["benign_served"] = round(benign_target_passed * served_frac, 2)
        tel["availability"] = round(tel["benign_served"] / tel["benign_target"], 4) if tel["benign_target"] else 1.0
        self.telemetry.append(tel)

        # ---------------------------------------------------- detection-side state machine
        for s in new_detections:
            self._emit("detection.created", {"source": s.ip, "true_attacker": s.is_attacker,
                                              "alerts_in_window": len(s.alerts), "threshold": cfg.alert_threshold})
            if self.controls["policy"] in ("block_source", "rate_limit"):
                self._enforce_on(s.ip)
        if self.marks["suspicious"] is None and any(
                s.first_alert_at is not None for s in self.sources.values() if s.is_attacker):
            self.marks["suspicious"] = t
            self._set_state("SUSPICIOUS", "First alert on an attacking source")
        if self.marks["detected"] is None and any(s.detected_at is not None for s in self.sources.values() if s.is_attacker):
            self.marks["detected"] = t
            # the playbook follows what was actually detected (e.g. a scanner caught during recon)
            # Only what the detector named may drive the recommendation (no ground-truth fallback).
            self.recommended = RECOMMENDED.get(str(self.detected_family), "block_source")
            self._set_state("DETECTED", f"Incident raised for {self.detected_family}")
            self._explain()
            self.marks["response_options"] = t
            self._set_state("RESPONSE_OPTIONS", f"Recommended: {DEFENSES[self.recommended]['title']}")
            self._emit("response.recommended", {"recommended": self.recommended, "options": list(DEFENSES)})
            if cfg.response_mode == "manual":
                self.awaiting_decision = True
                self._emit("response.awaiting_decision", {})
        if (cfg.response_mode == "auto" and self.marks["detected"] is not None and self.chosen is None
                and t >= self.marks["detected"] + cfg.approval_delay_s):
            self._apply(cfg.defense)

        self._update_outcome(t)

    def _flow_row(self, t, src, dst, i, is_att, status, verdicts) -> dict[str, Any]:
        p = self.pool
        return {"t": t, "src": src, "dst": SERVERS.get(dst, dst), "dst_role": dst, "truth": str(p.family[i]),
                "is_attack": is_att, "status": status,
                "frozen": None if verdicts is None else {"alert": verdicts[0], "type": str(p.frozen_type[i]),
                                                         "confidence": round(float(p.frozen_conf[i]), 3)},
                "gate": None if verdicts is None else {"alert": verdicts[1], "label": str(p.gate_label[i]),
                                                       "p_value": float(p.gate_p[i])}}

    def _explain(self) -> None:
        i = getattr(self, "_pending_explain", None)
        if i is None or not self.config.explain:
            return
        try:
            from backend.services.pipeline import get_explainer

            eng = get_explainer()
            if eng is None:
                return
            row = self.pool.frame.iloc[i]
            names = list(eng.bundle.feature_names)
            feats = {n: float(row[n]) if n in row.index else float(row.get("Fwd Header Length", 0.0)) for n in names}
            exp = eng.explain(feats, top_k=8)
            exp["flow_family_truth"] = str(self.pool.family[i])
            exp["feature_values"] = {f["feature"]: feats.get(f["feature"]) for f in exp.get("top_features", [])}
            self.explanation = exp
            self.marks["explained"] = self.t
            self._set_state("EXPLAINED", "SHAP explanation of the triggering flow")
            self._emit("explanation.ready", {"method": exp.get("actual_method"),
                                             "top": exp.get("top_features", [])[:3]})
        except Exception as exc:  # explanation is decision support; never break the run
            self._emit("explanation.failed", {"error": str(exc)[:200]})

    def _enforce_on(self, ip: str) -> None:
        if self.controls["policy"] == "block_source":
            self.controls["blocked"].add(ip)
        elif self.controls["policy"] == "rate_limit":
            self.controls["rate_limited"].add(ip)

    def _apply(self, action: str) -> None:
        action = self.recommended if action == "recommended" else action
        self.chosen = action
        self.awaiting_decision = False
        if action in ("none", "monitor_only"):
            self._emit("response.applied", {"action": action, "changes_traffic": False})
            self._set_state("NO_ACTION" if action == "none" else "MONITORING", DEFENSES[action]["effect"])
            return
        self.marks["defense"] = self.t
        if action in ("block_source", "rate_limit"):
            self.controls["policy"] = action
            for s in self.sources.values():
                if s.detected_at is not None:
                    self._enforce_on(s.ip)
        elif action == "isolate_host":
            self.controls["isolated"] = True
        elif action == "increase_inspection":
            self.controls["inspection"] = True
        self._emit("response.applied", {"action": action, "changes_traffic": action != "increase_inspection",
                                        "controls": self._controls_view()})
        self._set_state("MITIGATING", DEFENSES[action]["effect"])

    def _mitre(self) -> dict[str, Any] | None:
        """ATT&CK context of what the *detector* named. A gate-only "Zero-Day Candidate" has no family,
        so no technique is shown — the range never leaks the scenario's ground truth into a detection."""
        from security.threat_intel import attack_context

        if self.detected_family is None:
            return None
        return attack_context(self.detected_family)

    def _controls_view(self) -> dict[str, Any]:
        c = self.controls
        return {"policy": c["policy"], "blocked": sorted(c["blocked"]), "rate_limited": sorted(c["rate_limited"]),
                "isolated": c["isolated"], "inspection": c["inspection"]}

    def _update_outcome(self, t: int) -> None:
        tel = self.telemetry
        # isolation is lifted after 5 quiet seconds (no attack attempts)
        if self.controls["isolated"] and self.last_attack_attempt is not None and t - self.last_attack_attempt >= 5:
            self.controls["isolated"] = False
            self.marks["isolation_lifted"] = t
            self._emit("response.isolation_lifted", {"after_quiet_s": 5})
        if self.marks["defense"] is not None and self.marks["contained"] is None and t >= self.marks["defense"] + 2:
            recent = tel[-3:]
            # contained = at least a 75% reduction of attack traffic reaching the target (or none at all)
            if all(r["attack_passed"] == 0 for r in recent) or (
                    sum(r["attack_passed"] for r in recent) <= 0.25 * max(1, sum(r["attack_sent"] for r in recent))):
                self.marks["contained"] = t
                self._emit("attack.mitigated", {"seconds_after_defense": t - self.marks["defense"]})
                self._set_state("CONTAINED", "Malicious traffic no longer reaches the target")
        if self.marks["contained"] is not None and self.marks["recovered"] is None:
            last = tel[-3:]
            if len(last) == 3 and all(r["availability"] >= 0.98 for r in last):
                self.marks["recovered"] = t
                self._emit("service.recovered", {"seconds_after_defense": t - self.marks["defense"]})
                self._set_state("RECOVERY", "Service availability restored")

    # ------------------------------------------------------------------ public API
    def step(self, seconds: int = 1) -> dict[str, Any]:
        with self._lock:
            start_seq = self.seq
            for _ in range(max(1, int(seconds))):
                if self.done:
                    break
                self._tick()
                self.t += 1
            if self.done and self.marks["completed"] is None:
                self.marks["completed"] = self.t
                if self.awaiting_decision:
                    self._emit("response.no_decision", {})
                    self.awaiting_decision = False
                self._set_state("COMPLETED", self.outcome())
                self._emit("simulation.completed", {"metrics": self.metrics()})
                self.save()
            return self.view(since_seq=start_seq)

    def respond(self, action: str) -> dict[str, Any]:
        with self._lock:
            if action not in DEFENSES:
                raise ValueError(f"Unknown action {action!r}")
            if self.marks["detected"] is None:
                raise ValueError("Nothing has been detected yet — there is no incident to respond to.")
            if self.chosen is not None:
                raise ValueError(f"A response was already applied ({self.chosen}).")
            self._apply(action)
            return self.view(since_seq=self.seq - 3)

    def complete(self) -> dict[str, Any]:
        if self.config.response_mode == "manual" and not self.done:
            # headless completion of a manual run applies nothing on the analyst's behalf
            pass
        return self.step(self.duration - self.t + 1)

    def outcome(self) -> str:
        m = self.marks
        if m["detected"] is None:
            return "Attack was never detected"
        if self.chosen is None:
            return "Detected, but no response was applied"
        if self.chosen in ("none", "monitor_only"):
            return f"Detected; response '{self.chosen}' left the attack running"
        if m["contained"] is None:
            return f"Response '{self.chosen}' applied but the attack was not contained"
        if m["recovered"] is None:
            return f"Contained by '{self.chosen}', service not yet fully recovered"
        return f"Contained by '{self.chosen}' and service recovered"

    def metrics(self) -> dict[str, Any]:
        a, m, tel = self.acc, self.marks, self.telemetry
        def rate(x, y):
            return round(x / y, 4) if y else None
        att = [r for r in tel if self.attack_start <= r["t"] < max(self.attack_end, self.attack_start + 1)]
        post = [r for r in tel if m["defense"] is not None and r["t"] >= m["defense"]]
        avail_attack = [r["availability"] for r in att]
        attackers = [s for s in self.sources.values() if s.is_attacker]
        false_incidents = [s for s in self.sources.values() if not s.is_attacker and s.detected_at is not None]
        dur_post = max(1, len([r for r in post if r["t"] < self.attack_end]))
        return {
            "detection_latency_s": None if m["detected"] is None or m["attack_start"] is None else m["detected"] - m["attack_start"],
            "first_alert_latency_s": None if m["suspicious"] is None or m["attack_start"] is None else m["suspicious"] - m["attack_start"],
            "time_to_mitigate_s": None if m["defense"] is None or m["detected"] is None else m["defense"] - m["detected"],
            "containment_time_s": None if m["contained"] is None or m["attack_start"] is None else m["contained"] - m["attack_start"],
            "recovery_time_s": None if m["recovered"] is None or m["defense"] is None else m["recovered"] - m["defense"],
            "attack_success_rate": rate(a["attack_passed"], a["attack_sent"]),
            "attack_success_before_defense": rate(a["attack_passed_pre"], a["attack_sent_pre"]),
            "attack_success_after_defense": rate(a["attack_passed_post"], a["attack_sent_post"]),
            "residual_attack_flows_per_s": round(a["attack_passed_post"] / dur_post, 3) if m["defense"] is not None else None,
            "mitigation_effectiveness": (None if m["defense"] is None or not a["attack_sent_pre"] or not a["attack_sent_post"]
                                         else round(1 - (a["attack_passed_post"] / a["attack_sent_post"]) /
                                                    max(a["attack_passed_pre"] / a["attack_sent_pre"], 1e-9), 4)),
            "availability_mean_during_attack": round(float(np.mean(avail_attack)), 4) if avail_attack else None,
            "availability_min_during_attack": round(float(np.min(avail_attack)), 4) if avail_attack else None,
            "availability_mean_overall": round(float(np.mean([r["availability"] for r in tel])), 4) if tel else None,
            "collateral_benign_blocked": a["benign_blocked"],
            "collateral_rate": rate(a["benign_blocked"], a["benign_sent"]),
            "false_positive_alerts": a["fp_alerts"],
            "fpr_flows": rate(a["fp_alerts"], a["benign_scored"]),
            "fpr_flows_frozen": rate(a["fp_alerts_frozen"], a["benign_scored"]),
            "fpr_flows_gate": rate(a["fp_alerts_gate"], a["benign_scored"]),
            "false_incidents": len(false_incidents),
            "attack_flow_recall": rate(a["attack_alerts"], a["attack_scored"]),
            "attack_flow_recall_frozen": rate(a["attack_alerts_frozen"], a["attack_scored"]),
            "attack_flow_recall_gate": rate(a["attack_alerts_gate"], a["attack_scored"]),
            "unseen_flows": a["unseen_sent"],
            "attackers_detected": sum(s.detected_at is not None for s in attackers),
            "attackers_total": len(attackers),
            "flows_total": a["benign_sent"] + a["attack_sent"],
            "attack_flows_sent": a["attack_sent"],
            "defense_applied": self.chosen,
            "detected_family": self.detected_family,
            "outcome": self.outcome(),
        }

    def topology(self) -> dict[str, list[dict[str, Any]]]:
        last = self.telemetry[-1] if self.telemetry else None
        c = self.controls
        attacking = self.stage not in ("NORMAL", "PREPARATION", "ATTACK_ENDED")
        target_id = "auth" if self.target == "auth" else "server"
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        att_ids = ["attacker", "attacker2", "attacker3", "attacker4"]
        internal = self.scenario.internal_attacker
        for k, ip in enumerate(self.attacker_ips[:4]):
            s = self.sources[ip]
            status = ("blocked" if ip in c["blocked"] else "stressed" if ip in c["rate_limited"]
                      else "alert" if s.detected_at is not None else "ok")
            nid = "pc02" if (internal and k == 0) else att_ids[k]
            label = f"Infected PC\n{ip}" if (internal and k == 0) else f"Attacker\n{ip}"
            nodes.append({"id": nid, "label": label, "kind": "attacker", "status": status})
            traffic = "blocked" if status == "blocked" else ("malicious" if attacking else "normal")
            if internal and k == 0:
                edges.append({"id": f"e_{nid}", "source": nid, "target": "router", "traffic": traffic,
                              "intensity": 0.6 if attacking else 0.1})
            else:
                edges.append({"id": f"e_{nid}", "source": nid, "target": "internet", "traffic": traffic,
                              "intensity": 0.7 if attacking else 0.1})
        avail = last["availability"] if last else 1.0
        alerts_now = (last["alerts_true"] + last["alerts_false"]) if last else 0
        tgt_status = ("isolated" if c["isolated"] else "stressed" if avail < 0.9 else "ok")
        nodes += [
            {"id": "internet", "label": "Internet", "kind": "router", "status": "ok"},
            {"id": "firewall", "label": "Firewall", "kind": "firewall",
             "status": "blocked" if (c["blocked"] or c["rate_limited"] or c["isolated"]) else "ok"},
            {"id": "ids", "label": "IDS sensor\nv1.1 + Zero-Day Gate", "kind": "ids", "status": "alert" if alerts_now else "ok"},
            {"id": "router", "label": "Core switch", "kind": "router", "status": "ok"},
            {"id": target_id, "label": f"{'Auth server' if target_id == 'auth' else 'Web server'}\n{SERVERS[self.target]}\n"
                                       f"availability {avail:.0%}", "kind": "server", "status": tgt_status},
            {"id": "pc01", "label": "40 clients", "kind": "host", "status": "ok"},
        ]
        mal_in = attacking and not c["isolated"] and (last is None or last["attack_passed"] > 0)
        edges += [
            {"id": "e_inet_fw", "source": "internet", "target": "firewall",
             "traffic": "malicious" if attacking and not internal else "normal", "intensity": 0.6 if attacking else 0.2},
            {"id": "e_fw_router", "source": "firewall", "target": "router",
             "traffic": ("filtered" if (c["blocked"] or c["rate_limited"]) and attacking else "malicious" if mal_in and not internal else "normal"),
             "intensity": 0.5},
            {"id": "e_router_ids", "source": "router", "target": "ids", "traffic": "normal", "intensity": 0.3},
            {"id": "e_router_tgt", "source": "router", "target": target_id,
             "traffic": "blocked" if c["isolated"] else ("malicious" if mal_in else "normal"),
             "intensity": min(1.0, (last["load_units"] / max(self.config.capacity, 1)) if last else 0.2)},
            {"id": "e_clients", "source": "pc01", "target": "router", "traffic": "normal", "intensity": 0.3},
        ]
        return {"nodes": nodes, "edges": edges}

    def view(self, since_seq: int = 0) -> dict[str, Any]:
        return {
            "run_id": self.id,
            "created_at": self.created_at,
            "config": asdict(self.config),
            "scenario": self.scenario.to_dict(),
            "t": self.t,
            "duration_s": self.duration,
            "done": self.done,
            "state": self.state,
            "stage": self.stage,
            "awaiting_decision": self.awaiting_decision,
            "recommended": self.recommended,
            "chosen": self.chosen,
            "detected_family": self.detected_family,
            "mitre_attack": self._mitre(),
            "controls": self._controls_view(),
            "marks": self.marks,
            "attackers": [{"ip": ip, "detected_at": self.sources[ip].detected_at,
                           "first_alert_at": self.sources[ip].first_alert_at} for ip in self.attacker_ips],
            "telemetry": self.telemetry,
            "events": [e for e in self.events if e["sequence"] > since_seq],
            "event_count": self.seq,
            "recent_flows": list(self.recent)[-30:],
            "explanation": self.explanation,
            "metrics": self.metrics(),
            "topology": self.topology(),
            "models": self.pool.models,
            "defenses": DEFENSES,
        }

    def record(self) -> dict[str, Any]:
        """Full persistent record (everything needed to audit or re-run the experiment)."""
        return {
            "run_id": self.id, "created_at": self.created_at, "config": asdict(self.config),
            "scenario": self.scenario.to_dict(), "attackers": self.attacker_ips, "duration_s": self.duration,
            "marks": self.marks, "metrics": self.metrics(), "telemetry": self.telemetry, "events": self.events,
            "explanation": self.explanation, "models": self.pool.models,
            "reproducibility": {"seed": self.config.seed, "scenario_version": self.scenario.version,
                                "event_schema_version": EVENT_SCHEMA_VERSION, "pool": str(POOL_PATH.relative_to(ROOT)),
                                "pool_rows": int(len(self.pool.frame))},
        }

    def save(self) -> Path | None:
        try:
            RUNS_DIR.mkdir(parents=True, exist_ok=True)
            path = RUNS_DIR / f"{self.id}.json"
            path.write_text(json.dumps(self.record(), default=_json_default), encoding="utf-8")
            return path
        except OSError:
            return None


def _json_default(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, set):
        return sorted(o)
    return str(o)


def run_headless(config: RangeConfig, *, save: bool = False) -> dict[str, Any]:
    """Run one configuration to completion and return its metrics (used by the experiment engine)."""
    run = RangeRun(config)
    t0 = time.perf_counter()
    while not run.done:
        run._tick()
        run.t += 1
    run.marks["completed"] = run.t
    out = run.metrics()
    out["wall_seconds"] = round(time.perf_counter() - t0, 3)
    if save:
        run.save()
    return out


class RangeManager:
    """In-memory registry of interactive runs (bounded)."""

    def __init__(self, max_runs: int = 30) -> None:
        self.runs: dict[str, RangeRun] = {}
        self.max_runs = max_runs
        self._lock = threading.Lock()

    def create(self, config: RangeConfig) -> RangeRun:
        run = RangeRun(config)
        with self._lock:
            self.runs[run.id] = run
            while len(self.runs) > self.max_runs:
                self.runs.pop(next(iter(self.runs)))
        return run

    def get(self, run_id: str) -> RangeRun:
        if run_id not in self.runs:
            raise KeyError(f"Unknown or expired cyber-range run: {run_id}")
        return self.runs[run_id]

    def recent(self) -> list[dict[str, Any]]:
        return [{"run_id": r.id, "scenario": r.scenario.id, "state": r.state, "t": r.t, "done": r.done,
                 "created_at": r.created_at} for r in reversed(list(self.runs.values()))]


range_manager = RangeManager()
