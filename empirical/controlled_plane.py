"""Isolated controlled test plane: Test Client → Test Target gated by CONTROLLED adapter.

No real packets leave the process. Connection attempts are synthetic events whose
accept/deny outcome is decided by `TestNetworkAdapter.traffic_decision`.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from security.response.adapters.test_network import TestNetworkAdapter, test_network_adapter

TrafficKind = Literal["attack", "benign"]


@dataclass
class AttemptResult:
    t_perf: float
    source: str
    kind: TrafficKind
    decision: str
    accepted: bool
    reason: str | None = None


@dataclass
class WindowStats:
    attempts: int = 0
    accepted: int = 0
    denied: int = 0
    throttled_denied: int = 0
    attack_attempts: int = 0
    attack_accepted: int = 0
    attack_denied: int = 0
    benign_attempts: int = 0
    benign_accepted: int = 0
    duration_s: float = 0.0
    cpu_proxy_load: float = 0.0  # accepted attacks / capacity

    def as_dict(self) -> dict[str, Any]:
        att = max(self.attempts, 1)
        atk = max(self.attack_attempts, 1)
        ben = max(self.benign_attempts, 1)
        return {
            "attempts": self.attempts,
            "accepted": self.accepted,
            "denied": self.denied,
            "throttled_denied": self.throttled_denied,
            "accepted_rate": round(self.accepted / att, 6),
            "blocked_rate": round(self.denied / att, 6),
            "attack_attempts": self.attack_attempts,
            "attack_accepted": self.attack_accepted,
            "attack_denied": self.attack_denied,
            "attack_accepted_rate": round(self.attack_accepted / atk, 6),
            "attack_blocked_rate": round(self.attack_denied / atk, 6),
            "benign_attempts": self.benign_attempts,
            "benign_accepted": self.benign_accepted,
            "service_availability": round(self.benign_accepted / ben, 6),
            "duration_s": round(self.duration_s, 6),
            "attack_traffic_rate_per_s": round(self.attack_attempts / max(self.duration_s, 1e-9), 4),
            "cpu_proxy_load": round(self.cpu_proxy_load, 6),
        }


@dataclass
class ControlledTestPlane:
    """Lab topology: attacker/client IPs → test target, enforced by CONTROLLED adapter state."""

    target_host: str = "10.0.0.10"
    attacker_ip: str = "203.0.113.50"
    benign_ip: str = "198.51.100.20"
    target_capacity: int = 100  # accepted attack attempts that saturate the proxy load
    adapter: TestNetworkAdapter = field(default_factory=lambda: test_network_adapter)
    _throttle_counter: int = 0

    def reset_counters(self) -> None:
        self._throttle_counter = 0

    def attempt(self, source: str, kind: TrafficKind) -> AttemptResult:
        gate = self.adapter.traffic_decision(source)
        decision = str(gate.get("decision") or "ALLOW")
        accepted = True
        if decision == "DENY":
            accepted = False
        elif decision == "THROTTLE":
            frac = float(gate.get("allow_fraction") or 0.2)
            # Deterministic throttle: allow floor(frac*10)/10 of attempts
            period = max(1, int(round(1.0 / max(frac, 0.01))))
            self._throttle_counter += 1
            accepted = (self._throttle_counter % period) == 1
            if not accepted:
                decision = "THROTTLE_DENY"
        return AttemptResult(
            t_perf=time.perf_counter(),
            source=source,
            kind=kind,
            decision=decision if accepted or decision != "ALLOW" else "ALLOW",
            accepted=accepted,
            reason=gate.get("reason"),
        )

    def run_window(
        self,
        *,
        n_attack: int,
        n_benign: int,
        inter_attempt_s: float = 0.0,
    ) -> tuple[WindowStats, list[AttemptResult]]:
        """Generate interleaved attack/benign connection attempts."""
        self.reset_counters()
        results: list[AttemptResult] = []
        t0 = time.perf_counter()
        sequence: list[tuple[str, TrafficKind]] = (
            [(self.attacker_ip, "attack")] * n_attack
            + [(self.benign_ip, "benign")] * n_benign
        )
        # Stable shuffle-like interleave: place benign evenly among attacks
        if n_benign > 0 and n_attack > 0:
            sequence = []
            a_left, b_left = n_attack, n_benign
            step = max(1, n_attack // n_benign)
            i = 0
            while a_left > 0 or b_left > 0:
                if a_left > 0:
                    sequence.append((self.attacker_ip, "attack"))
                    a_left -= 1
                    i += 1
                if b_left > 0 and (i % step == 0 or a_left == 0):
                    sequence.append((self.benign_ip, "benign"))
                    b_left -= 1
        for source, kind in sequence:
            results.append(self.attempt(source, kind))
            if inter_attempt_s > 0:
                time.sleep(inter_attempt_s)
        t1 = time.perf_counter()
        stats = WindowStats(duration_s=t1 - t0)
        for r in results:
            stats.attempts += 1
            if r.accepted:
                stats.accepted += 1
            else:
                stats.denied += 1
                if r.decision == "THROTTLE_DENY":
                    stats.throttled_denied += 1
            if r.kind == "attack":
                stats.attack_attempts += 1
                if r.accepted:
                    stats.attack_accepted += 1
                else:
                    stats.attack_denied += 1
            else:
                stats.benign_attempts += 1
                if r.accepted:
                    stats.benign_accepted += 1
        stats.cpu_proxy_load = min(1.0, stats.attack_accepted / max(self.target_capacity, 1))
        return stats, results

    def scenario_id(self, name: str) -> str:
        raw = f"{name}|{self.attacker_ip}|{self.target_host}"
        return hashlib.sha1(raw.encode()).hexdigest()[:10]
