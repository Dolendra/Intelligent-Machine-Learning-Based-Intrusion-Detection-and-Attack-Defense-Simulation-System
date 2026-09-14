# P10 — Generalization

**Experiment:** EXP-017 (`generalization_report.json`)  
**Scripts:** `scripts/25_temporal_holdout_eval.py`, `scripts/41_generalization_report.py`  
**Related:** `docs/experiments/TEMPORAL_HOLDOUT.md`, `docs/experiments/DATA_DRIFT.md`  
**Frozen baseline:** tag `v1.1-research` — Decision Tree (binary @ 0.85) + Random Forest (six attack families)

> Purpose: measure how well the **frozen** IDS generalizes beyond the IID test split — **not** to improve 0.99048 / 0.99813.

---

## 1. Objective

Answer:

> How well does Aegis perform when evaluated on traffic that is temporally separated from its training data, and what are the limitations of that result?

Protocol constraints:

- Score frozen joblibs only (**no retrain**, **no threshold retune** on the holdout)
- Preserve published IID metrics exactly
- Report degradation (or improvement) honestly
- Do not claim zero-day detection or live-network guarantees

---

## 2. Dataset / time split

| Slice | Definition | n (this freeze) | Attack rate |
|-------|------------|----------------:|------------:|
| **IID test** | Stratified processed CICIDS2017 test | 504,151 | ~16.9% |
| **Friday temporal** | Day-named MachineLearningCVE CSVs starting with Friday (capped sample) | 36,000 | 33.8% |
| **Mon–Thu early** | Mon–Thu day samples (reference, not the primary holdout) | 60,000 | 6.9% |

- **Dataset:** CICIDS2017 / `MachineLearningCVE`
- **Random seed:** 42
- **Per-file sample cap:** 12,000
- Day slices are **capped samples**, not exhaustive day populations

---

## 3. Frozen model configuration

| Item | Value |
|------|-------|
| Binary | Decision Tree, operating threshold **0.85** |
| Multiclass | Random Forest (Bot, BruteForce, DDoS, DoS, PortScan, WebAttack) |
| Artifacts | `binary_best.joblib`, `multiclass_best.joblib`, `feature_bundle.joblib` |
| Model version | 1.1.0 |
| Training git commit | `c99d2d3` (see `model_metadata.json`) |
| Dual SelectKBest | 40 features binary / 40 multiclass |
| Tuned on temporal holdout? | **No** |

---

## 4. IID results (preserved)

From `training_report.json` / `v1.1-research`:

| Metric | Value |
|--------|------:|
| Binary F1 | **0.99048** |
| Binary Recall | 0.99700 |
| Binary PR-AUC | 0.99744 |
| Multiclass Accuracy | 0.99979 |
| Macro-F1 | **0.99813** |
| Macro-Recall | 0.99864 |

These remain the official stratified-test scores. Temporal numbers below do **not** replace them.

---

## 5. Temporal results

### Binary (Decision Tree @ 0.85)

| Metric | IID | Friday temporal | Mon–Thu early |
|--------|----:|----------------:|--------------:|
| F1 | 0.99048 | **0.99770** | 0.97997 |
| Recall | 0.99700 | 0.99638 | 0.97370 |
| Precision | 0.98404 | 0.99901 | 0.98631 |
| PR-AUC | 0.99744 | 0.99956 | 0.99670 |

### Multiclass (Random Forest)

| Metric | IID (6-class) | Friday subset (3-class) |
|--------|--------------:|------------------------:|
| Accuracy | 0.99979 | 1.0 |
| Macro-F1 | 0.99813 | 1.0 |
| Macro-Recall | 0.99864 | 1.0 |

Friday multiclass covers **only** Bot / DDoS / PortScan (n_attacks = 12,165). Absent: BruteForce, DoS, WebAttack. Subset perfect scores ≠ six-class temporal proof.

---

## 6. Degradation

Δ = IID − slice (**positive ⇒ temporal/early worse than IID**).

| Comparison | Δ F1 | Δ Recall | Δ PR-AUC |
|------------|-----:|---------:|---------:|
| IID − Friday | **−0.00722** | +0.00062 | −0.00212 |
| IID − Mon–Thu | **+0.01051** | +0.02330 | — |

**Reading:**

- On the **Friday** sample, binary F1/PR-AUC are **higher** than IID (negative Δ). Do not hide this, but also do not claim “better in production” — attack rate is much higher (33.8% vs ~16.9%), which can inflate F1.
- On **Mon–Thu**, binary F1 and recall **degrade** vs IID (positive Δ), with a lower attack rate (6.9%). This is the clearer within-corpus stress signal for prevalence/composition shift.
- Multiclass aggregate Δ is **not comparable** (6-class IID vs 3-class Friday).

---

## 7. Class-wise analysis (Friday temporal)

| Family | Present? | Precision | Recall | F1 | Support |
|--------|----------|----------:|-------:|---:|--------:|
| Bot | yes | 1.0 | 1.0 | 1.0 | 108 |
| BruteForce | **no** | — | — | — | 0 |
| DDoS | yes | 1.0 | 1.0 | 1.0 | 6915 |
| DoS | **no** | — | — | — | 0 |
| PortScan | yes | 1.0 | 1.0 | 1.0 | 5142 |
| WebAttack | **no** | — | — | — | 0 |

**Which families generalize (in this sample)?** Bot, DDoS, and PortScan scored perfectly on the Friday attack-only subset.

**Which lack temporal evidence?** BruteForce, DoS, WebAttack — absent from the Friday sample used here. IID class-wise (for context) remains strong for all six; WebAttack is the weakest IID family (F1 ≈ 0.990).

---

## 8. Confusion matrix (temporal multiclass)

Friday 3×3 (labels Bot, DDoS, PortScan) is **diagonal-only** in this freeze:

| true \ pred | Bot | DDoS | PortScan |
|-------------|----:|-----:|---------:|
| Bot | 108 | 0 | 0 |
| DDoS | 0 | 6915 | 0 |
| PortScan | 0 | 0 | 5142 |

**Relationships actually present:** none off-diagonal on Friday.

**Not claimed here** (would require off-diagonal evidence): DoS ↔ DDoS, BruteForce ↔ WebAttack, Bot ↔ DDoS.

IID residual confusions (separate artifact) concentrate among PortScan / DoS / WebAttack — see `docs/experiments/ERROR_ANALYSIS.md`.

Figures: `models/trained_models/figures/temporal_friday_multiclass_confusion.png`

---

## 9. Drift analysis

### IID train → test (EXP-008)

> **No feature exceeded the selected PSI threshold (0.2) in the tested IID train→test comparison.**

| Item | Value |
|------|------:|
| Features compared | 78 |
| Flagged PSI ≥ 0.2 | **0** |
| Max PSI (listed) | ~0.0 |

This is **expected** under a stratified same-corpus split. It is **not** a claim that “there is no drift.”

### Temporal train → Friday (P10)

Complementary check: processed **train** vs Friday day sample (same seed/cap as temporal eval).

| Item | Value |
|------|------:|
| Features compared | 78 |
| Flagged PSI ≥ 0.2 | **2** |
| Max PSI | **0.2354** (`Fwd Header Length` / `Fwd Header Length.1`) |
| Near-threshold | `Bwd Header Length` ≈ 0.20 |

Non-zero temporal PSI is expected under day/scenario composition shift. It contextualizes the IID PSI≈0 result; it does **not** by itself invalidate frozen model scores.

---

## 10. External dataset status

| Item | Status |
|------|--------|
| Configured path | `CSE-CIC-IDS2018` (not present on this host) |
| Artifact | `cross_dataset_status.json` → **skipped** |
| Conclusion | **External-dataset validation remains future work.** |

Rule: if a compatible external set appears later, score **frozen** preprocessing + DT/RF only — do **not** retrain on the external set and call that cross-dataset generalization. If feature semantics are incompatible, document why the experiment is invalid instead.

---

## 11. Limitations

1. Temporal day slices are capped samples, not full-day populations.
2. Attack-rate composition differs sharply across slices; headline F1 moves with prevalence.
3. Friday multiclass evidence covers only three of six families.
4. Mon–Thu multiclass may skip when labels outside the freeze set appear (e.g. Infiltration).
5. IID PSI≈0 ≠ absence of temporal/live/cross-dataset drift.
6. No external dataset scored under frozen preprocessing.
7. **No zero-day / unknown-attack claim** — that would be a separate held-out experiment and must not modify the frozen classifier.
8. The **production PCAP pipeline does not automatically inherit** these research metrics.
9. Models were **not** optimized against the temporal holdout (holdout stays evaluation-only).

---

## 12. Conclusions

1. **Temporal (Friday) binary detection remains strong** relative to the IID test under the documented sample; Δ F1 is slightly in Friday’s favor, with a much higher attack rate.
2. **Mon–Thu early-day binary F1/recall degrade vs IID**, showing sensitivity to day composition / prevalence — report this degradation rather than averaging it away.
3. **Class-wise temporal generalization is evidenced only for Bot, DDoS, and PortScan**; BruteForce, DoS, and WebAttack remain temporally unevaluated in this protocol.
4. **IID “no PSI ≥ 0.2” must stay narrowly worded**; temporal train→Friday shows measurable feature shift (2 features ≥ 0.2).
5. **External-dataset and unknown/zero-day validation remain future / separate work.**
6. Research metrics apply to: *dataset → frozen models → IID + temporal evaluation*. Production path is: *PCAP → flows → features → validation → frozen models* — scores are not automatically inherited.

### Completion criterion

P10 is complete when the question above can be answered from this document + `generalization_report.json` without relying only on the original IID test score.

### Reproducibility

| Field | Source |
|-------|--------|
| Experiment ID | EXP-017 |
| Git commit | recorded in `generalization_report.json` |
| Model / feature / dataset versions | `model_metadata.json` + report |
| Split definition / seed / metrics / env / timestamp | `generalization_report.json` |

```text
python scripts/25_temporal_holdout_eval.py   # regenerate temporal scores (needs MachineLearningCVE)
python scripts/41_generalization_report.py   # consolidate + temporal PSI
python scripts/22_write_experiment_index.py  # refresh INDEX
```

### After P10

```text
P10 Generalization       ✅
       ↓
P11 Empirical mitigation
       ↓
P12 Final security validation
```
