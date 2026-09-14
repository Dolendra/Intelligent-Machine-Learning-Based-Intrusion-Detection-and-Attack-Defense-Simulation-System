# P11 — Empirical Mitigation

**Experiments:** EXP-018 (DDoS / `BLOCK_SOURCE`), EXP-019 (DoS / `RATE_LIMIT`)  
**Artifact:** `models/trained_models/empirical_mitigation_report.json`  
**Script:** `scripts/42_empirical_mitigation_experiment.py`  
**Package:** `empirical/` (controlled test plane — **not** `simulation/`)

> Purpose: replace *simulation-only* defense-effectiveness **claims** with **measurements** from an isolated CONTROLLED lab — without removing the simulation, and without connecting real firewall/EDR.

---

## 1. Objective

Answer:

> When Aegis detects a controlled attack scenario and an approved defense is applied, what measurable change occurs compared with the same scenario without defense?

---

## 2. Two tracks (do not conflate)

### Simulation (unchanged)

```text
Attack scenario → Aegis detection → Risk → Recommended defense → Simulation → Assumed effectiveness
```

Assumptions remain in `config.yaml` → `simulation.defense_effectiveness` (e.g. DDoS **0.82**, DoS **0.78**).  
See `docs/05-simulation.md`.

### P11 experiment (new)

```text
Controlled test traffic → Aegis detection → Controlled response (approve) → Measured outcome
```

```text
Defense effectiveness (P11) = measured observation on the CONTROLLED test plane
```

If measured ≠ assumed, **keep both** and report the delta. Do not retune the experiment to make the simulation look correct.

---

## 3. Controlled environment

Isolated **in-process** lab (no public/production network, no NIC packets):

```text
┌─────────────┐
│ Test Client │  (attacker IP + benign probes)
└──────┬──────┘
       ↓
┌─────────────┐
│ Test Target │  (capacity proxy)
└──────┬──────┘
       ↓
    Aegis detect → propose → approve → TestNetworkAdapter → traffic_decision gate
```

Enforcement plane: existing **CONTROLLED** `TestNetworkAdapter` only (`live_network_change=false`).

---

## 4. Measurable outcomes

| Quantity | Definition in this lab |
|----------|------------------------|
| Attack traffic rate | Attack attempts / window duration |
| Accepted connection rate | Accepted / attempts |
| Blocked connection rate | Denied / attempts |
| Attack accepted / blocked rates | Same, attack-only |
| Service availability | Benign probes accepted / benign attempts |
| Resource utilization proxy | `cpu_proxy_load` = accepted attacks / target capacity |
| Detection / decision / response / mitigation / recovery latency | From timeline T0–T8 (only when measured) |

**Measured mitigation effectiveness:**

```text
(pre_attack_accepted_rate − post_attack_accepted_rate) / pre_attack_accepted_rate
```

---

## 5. Baseline vs defense

Every trial records a **pre** window (WITHOUT active defense state) and a **post** window after the condition-specific response path.

Conditions compared (same traffic parameters):

| Condition | What happens |
|-----------|----------------|
| `no_defense` | Detect only; no propose/approve |
| `recommendation_only` | Propose + dry-run; **no** approve → adapter state unchanged |
| `controlled_response` | Propose → dry-run → **approve** → verify → gate traffic → rollback |

This separates **detection capability** from **response capability**.

---

## 6. Safety architecture preserved

```text
Approval required → CONTROLLED adapter → Verification → Rollback
```

LIVE / firewall / EDR remain forbidden. P2/P3 gates are not bypassed for the experiment.

---

## 7. Timeline (measured slots)

| Mark | Meaning |
|------|---------|
| T0 | Traffic starts (pre window) |
| T1 | Attack window complete (detectable) |
| T2 | Aegis detection completes |
| T3 | Recommendation timestamp |
| T4 | Action proposed |
| T5 | Approval |
| T6 | Response executed (approve path executes immediately) |
| T7 | Verified |
| T8 | Post-rollback recovery window done |

Derived: detection / decision / response / mitigation / recovery latencies — only when both endpoints exist.

---

## 8. Freeze snapshot results (10 repetitions, frozen_ml detection)

| Scenario | Condition | Post attack blocked rate (mean) | Measured effectiveness (mean±stdev) | Simulation assumption | Δ (meas − sim) |
|----------|-----------|--------------------------------:|------------------------------------:|----------------------:|---------------:|
| DDoS `BLOCK_SOURCE` | no_defense | 0.00 | 0.00 | 0.82 | — |
| DDoS `BLOCK_SOURCE` | recommendation_only | 0.00 | 0.00 | 0.82 | — |
| DDoS `BLOCK_SOURCE` | controlled_response | **1.00** | **1.00 ± 0** | 0.82 | **+0.18** |
| DoS `RATE_LIMIT` | no_defense | 0.00 | 0.00 | 0.78 | — |
| DoS `RATE_LIMIT` | recommendation_only | 0.00 | 0.00 | 0.78 | — |
| DoS `RATE_LIMIT` | controlled_response | **0.80** | **0.80 ± 0** | 0.78 | **+0.02** |

### Reading the delta

- **DDoS:** CONTROLLED block denies 100% of subsequent attacker attempts in this plane. The simulation assumption (0.82) is a **visualization prior**, not a lab measurement — measured effectiveness is higher here because the test adapter’s `BLOCK_SOURCE` is a hard deny.
- **DoS:** `RATE_LIMIT` allows a deterministic 20% through (`allow_fraction=0.2`) → measured block rate 0.80, close to the 0.78 assumption.
- **Recommendation-only** never changes traffic — as required for scientific separation.

Raw trials + mean/median/stdev/min/max/p95 are in `empirical_mitigation_report.json`.

---

## 9. Reproducibility

| Field | Recorded in report |
|-------|-------------------|
| Experiment IDs | EXP-018, EXP-019 |
| Git commit / model version / timestamp | yes |
| Scenario + traffic parameters | pre/post attack & benign counts |
| Defense configuration | CONTROLLED / test_network / approval+verify+rollback |
| Detection mode | `frozen_ml` (preferred) or `label_oracle` (CI) |
| Repetitions | 10 (default) |
| Environment | platform / python / in-process isolation note |

```bash
python scripts/42_empirical_mitigation_experiment.py --repetitions 10
python scripts/42_empirical_mitigation_experiment.py --quick   # oracle, 3 reps (CI-friendly)
python scripts/22_write_experiment_index.py
```

---

## 10. Limitations

1. **Not** a real firewall/EDR measurement — CONTROLLED adapter only.
2. Traffic is synthetic connection attempts inside the process, not wire packets.
3. Service availability is a benign-probe proxy, not an application SLA.
4. `cpu_proxy_load` is not OS CPU.
5. Frozen-ML detection scores CICIDS flow samples, not PCAP from the lab topology.
6. Hard `BLOCK_SOURCE` in the test plane yields effectiveness 1.0 by construction of the gate — valuable for validating the measurement framework, not for claiming production block rates.
7. Simulation assumptions were **not** edited to match measurements.

---

## 11. What about real firewall/EDR?

Only after this CONTROLLED measurement framework is proven:

```text
CONTROLLED adapter → measurement validated → sandbox enforcement → verify → rollback
                 → only then consider a real adapter (explicitly opt-in, never automatic)
```

Live response remains **opt-in and tightly controlled**. This phase does **not** enable it.

---

## 12. Conclusions

Under the tested controlled environment and scenarios:

1. **Without defense** and **recommendation-only**, attack traffic continues to be accepted (blocked rate 0).
2. **With approved CONTROLLED response**, measurable mitigation appears immediately in the post window (DDoS block → 100% attacker deny; DoS rate-limit → 80% deny).
3. Simulation assumptions remain documented priors; measured lab outcomes are reported beside them with deltas.
4. The production claim upgrade is:

> Under the tested controlled environment and scenario, the measured outcome was X, with the limitations above — not “the simulation assumes X% mitigation” as a substitute for measurement.

### Completion criterion

P11 is complete when the question in §1 is answered with **actual experimental data** from this harness.

### After P11

```text
P11 Empirical mitigation       ✅
          ↓
P12 Final security validation
```
