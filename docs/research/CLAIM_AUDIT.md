# Aegis IDS — Research Claim Audit (R1)

**Date:** 2026-11-17 · **Scope:** `docs/AEGIS_GUIDE_PLAIN_LANGUAGE.md`, `docs/research/paper.tex`,
`docs/research/PAPER_AEGIS_OSR.md`, `docs/research/*.md` vs. raw artifacts
(`research_artifacts/*_records.json`, `results/cyber_range/`, `research_artifacts/*.json`, code).
**Method:** every headline number was recomputed from *raw records*, not from summaries or docs.
No code or result was changed by this audit.

Legend: ✅ verified · ⚠️ true but needs a caveat or rewording · ❌ wrong / not supported

---

## 0. Two things to fix before anything else

| # | Finding | Impact | Fix |
|---|---|---|---|
| 0.1 | **None of the v3 work is committed.** Branch `v3-openset-research` == `main` (`775e9a9`); research code, Cyber Range, paper, guide, results and the UI redesign exist only in the working tree. GitHub `main` contains none of it. | One bad checkout or disk failure loses ~2 weeks of work; a reviewer given `main` sees nothing. | Commit on the branch now (no push needed until reviewed). |
| 0.2 | **Replay-pool leakage for the frozen model (bug in `scripts/52_build_replay_pool.py`).** The pool was drawn from the *gate's* test split, but the frozen v1.1 model used an independent 70/10/20 split. Exact-row check (float32 hashes): **69.6 % of replay flows are in v1.1's training split**, 10.2 % in validation, 20.4 % in test. The 47 Infiltration/Heartbleed flows are clean. | Every **frozen-model** number measured on replay flows is optimistic: Live Monitor, Cyber Range detector tables, the `frozen_v11` block of `zero_day_gate_report.json`, XAI-stability flows. **Gate and zero-day comparisons are unaffected** (pool is the gate's own test split; unseen families never trained on). | Rebuild the pool from rows in **both** test splits (frozen ∩ gate), re-run gate report, range experiments and XAI study. Fix the docstring claim. |

## 1. Claims that hold

| Claim (guide / paper) | Evidence | Status |
|---|---|---|
| LOAFO: Aegis-OSR 70.6 % vs closed-set XGB 49.0 % vs DT 24.1 % zero-day recall at α = 1 % | `openset_loafo_records.json`: 30 records = 6 folds × seeds 1–5; 0.706 [0.689, 0.723], 0.490, 0.241 | ✅ |
| Realized FPR 1.00 % on matching (IID) traffic | 0.0100 for every method | ✅ |
| Beats closed-set XGB in 30/30 fold × seed pairs | positive in every seed (+0.18…+0.25) and every family | ✅ (statistics need rewording, §2) |
| Per family: Web 99 %, DoS 98 %, DDoS 97 %, BruteForce 92 % vs 31 %, PortScan 36 %, Bot 2 % | LOAFO summary | ✅ |
| Unknowns rarely mislabelled as a known family (≤ 0.9 %) | attribution block | ✅ |
| Never-seen Infiltration/Heartbleed: frozen 0/47, gate 29/47 (11/11 Heartbleed) | `zero_day_gate_report.json` | ✅ (tiny n — illustrative only) |
| Frozen v1.1 on CSE-CIC-IDS2018: F1 0.185, recall ≈ 10 % | `frozen_v11_on_cic2018.json` (0.1846 / 0.1018) | ✅ |
| Cyber Range: 1,190 runs (119 cells × 10 seeds); zero-day scenario frozen 0/10, gate 10/10, 4.3 s | `CYBER_RANGE_RESULTS.md`, experiment JSON | ✅ (caveat §3) |
| k = 3 alerts / 5 s → 0 false incidents vs ≈ 18 at k = 1 | experiment JSON | ✅ (k = 2 already ≈ 0.7) |
| 30 s approval delay: DDoS availability 99.5 % → 62 % | experiment JSON | ✅ (99.5 % is the 0 s-delay baseline) |
| Ten detector families; most IID F1 > 0.98; best held-out 48 %; NNs 5–35 % | `model_family_comparison.json` | ✅ (single seed) |
| SHAP robust (≥ 0.90) except Bot 0.51 / WebAttack 0.66; SHAP–LIME agreement 0.26 | `xai_stability_report.json` | ✅ (flows affected by 0.2) |
| The three "inconsistencies" raised by the reviewer | see §4 | resolved |

## 2. Statistical wording to correct

* **"p = 1.86 × 10⁻⁹ across 30 pairs"** treats 6 folds × 5 seeds as independent. Folds within a seed share a
  split. Seed-level test (fold-averaged, n = 5): paired *t* **p = 7.6 × 10⁻⁵** vs closed-set XGB (3.3 × 10⁻⁵ vs DT);
  Wilcoxon with n = 5 cannot go below p = 0.0625. → Report the seed-level paired test + "positive in 30/30
  fold-seed pairs", or move to 10 seeds.
* **Design selection bias (mild).** Fusion rule and novelty detector were chosen on seed 0 *on the same six
  held-out families*. Seeds are disjoint, families are not. State it; ideally confirm on a third dataset.
* **"Extreme Value Theory"** (`paper.tex:213`) — the tail is a simple exponential extrapolation inspired by
  peaks-over-threshold; no EVT distribution is fitted. Say "exponential tail extrapolation".

## 3. Claims that are wrong or overstated

| Where | Says | Artifact says | Status |
|---|---|---|---|
| `paper.tex:210`, `PAPER_AEGIS_OSR.md:316,324` | Friday FPR 7.68 % | **7.09 %** | ❌ stale |
| `paper.tex:210` | recal+ref@5000 → FPR 1.66 %, recall 0.457 | **2.84 %**, 0.444 | ❌ stale |
| `PAPER_AEGIS_OSR.md:316` | kNN Friday FPR 10.08 % | **8.82 %** | ❌ |
| `PAPER_AEGIS_OSR.md:324-331` (Table 4) | e.g. recal@2000 0.25 %, recal@5000 1.48 %, oracle 1.31 % | **0.82 %, 2.57 %, 0.97 %** (`RESULTS.md` is correct) | ❌ whole table |
| `paper.tex:205` | PortScan 58.7 % at α = 5 % | **52.8 %** | ❌ |
| `paper.tex:35`, `PAPER_AEGIS_OSR.md:16` | "30 experimental runs" covering LOAFO + temporal + cross | 30 = LOAFO only; temporal 10, cross 5 | ⚠️ |
| `paper.tex:35,213`, `PAPER_AEGIS_OSR.md:93` | Recalibration "restores" the FPR constraint | Only for some windows: Friday W=500/2000 → 0.36–0.82 %, but **W=5000 → 2.57–2.84 %**. Cross-dataset: W=500 → 0.83 % but recall collapses to 4 %; **recal+ref@2000 → 51 % FPR** (not reported) | ❌ overclaim |
| `paper.tex:213`, `PAPER_AEGIS_OSR.md:350,83` | "provable / exact / a-priori guaranteed 1 % budget" | Holds only under exchangeability; measured 7.09 % (Friday) and 35.2 % (2018) | ⚠️ add the condition every time |
| Both papers | Cross-dataset listed as a contribution | No cross-dataset results reported (Aegis-OSR FPR 35.2 %, recall 0.44) | ❌ omission |
| Guide §7.1 | "None of the ten caught a single hidden botnet flow" | DT caught 3 / 1,948 | ⚠️ "almost none (≤ 0.2 %)" |
| Guide §7.1 | "Hidden DoS caught 90 %+ by tree models" | RF 0.90, XGB 0.94, HGB 0.81, DT 0.31 | ⚠️ "by RF and XGBoost" |
| Guide §7.3 / range | Isolate "locked out 27 % of normal users" | 27.4 % of benign **flows** blocked (`cyberrange/engine.py:585`) | ⚠️ |
| Guide §7.3 / range | Isolate "took ≈ 52 s to recover" | Mechanical: isolation lifts 5 s after the attack ends (`engine.py:489`) | ⚠️ not a measurement of recovery |
| Guide §5.3 | Compare defenses "runs every defense five times" | 4 defenses × 5 seeds; increase-inspection omitted (`CyberRangePage.tsx:610`) | ⚠️ |
| Guide §2, §7.4 | ATT&CK tag on "every detection" | Static per-family map (`security/threat_intel.py:27-44`); BENIGN/UNKNOWN/ZERO-DAY untagged; gate-only range incidents show the **scenario's ground-truth** tag (`engine.py:476-478`) | ⚠️ the last one leaks ground truth into the demo |
| `XAI_STABILITY.md:3`, `scripts/57_xai_stability.py:3` | "held-out replay flows" | ~70 % in v1.1 training split (0.2) | ❌ |
| `scripts/52_build_replay_pool.py:3-6` | "never replays training data" | True for the gate only (0.2) | ❌ |
| Gate report `frozen_v11` (FPR 0.064 %, recall 0.993, WebAttack 42 %) | — | Computed on the gate test split → partly frozen-train rows | ❌ recompute |
| `scripts/54_frozen_v11_on_cic2018.py` | `iid_cicids2017_f1_reference` | `null` (wrong JSON path; should be `binary.test`) | bug |

### Cyber Range: what is measured vs modelled

* **Computed:** detector verdicts on real flows, alert/incident timing (1-s ticks), firewall decisions, counts.
* **Modelled:** availability = `min(1, capacity / load)` with capacity 60 units/s and per-family `FLOW_COST`
  constants (`cyberrange/scenarios.py:21-24`) and Poisson arrival rates. The delay → availability curve is
  therefore arithmetic on modelled constants (the results doc already says "modelled").
* **Resampling:** the zero-day scenario redraws the same 47 unseen flows with fixed verdicts, so 10 runs are
  not 10 independent zero-days (flow-level gate recall 0.645 ≈ 29/47).
* **Fragility:** if a model fails to load, the engine silently scores every flow benign
  (`engine.py:105-106,115-116`) — should fail loudly.
* **P11** (controlled mitigation, Sept 2026) is a *separate* experiment; no document mixes their numbers.

## 4. The reviewer's three inconsistencies — resolved

1. **Feature count.** Raw CSV = 79 columns (78 features + `Label`); processed parquet = 80 (+ `is_attack`);
   frozen v1.1 takes all **78** and selects **40** per stage (separate binary / multiclass selectors);
   Aegis-OSR uses **77** (drops `Fwd Header Length.1`, an exact duplicate column in CICIDS2017).
2. **Gate integration.** Operational API (`backend/services/pipeline.py:388,461`): the gate runs *after* the
   frozen decision and is attached as `zero_day` to the response only. **Gate alerts are not persisted** — no
   incident, no decision-trace step, no metric, no audit event. Cyber Range: incident detector defaults to
   `union` (frozen OR gate), so the gate *can* raise incidents there. → The two contexts combine decisions
   differently; production gate alerts are currently unauditable.
3. **Cyber Range vs P11.** Different suites, different dates, different planes; never merged. Keep separate
   experiment IDs (P11 = EXP-018/019; range needs its own EXP-ID, not yet in the index).

## 5. Why CICIDS2017 → CSE-CIC-IDS2018 collapses (new evidence)

* **No broken mapping.** All 77 features map; none are all-NaN or sign-flipped; benign KS ≤ 0.34 for every
  feature. Two flags are constant in 2018 only (`Fwd URG Flags`, `CWE Flag Count`).
* **Real environment shift in benign traffic:** 2018 benign is dominated by port **445 (SMB)** vs 80; median
  flow duration **34× longer**; 75 % vs 42 % of flows with zero minimum packet length.
* **Same attack tools stop being detected:** DoS-Hulk 99 % → **0.8 %**, SSH-Patator → SSH-Bruteforce **0 %**,
  LOIC-HTTP **0 %**, while Slowloris still transfers (95.6 %). Identical tools vanishing points to
  **feature-extraction shift** (different CICFlowMeter versions; the 2017 one has documented bugs) confounded
  with network shift. Domain adaptation alone cannot separate the two.
* **2018 duplication:** after exact de-duplication FTP-BruteForce has **51** unique flows and SlowHTTPTest
  **55** (from ~190 k / ~140 k raw rows) — report per-label *unique* counts.
* **Protocol flaw in our cross-dataset adaptation:** the warm-up window is the earliest benign traffic of the
  *first* 2018 day while the test spans 10 days, so recalibration cannot be exchangeable with the test set.

## 6. Recommended plan (maps to the reviewer's R1–R7)

| Phase | Work | Acceptance test |
|---|---|---|
| **R1a — integrity fixes** | Commit branch; rebuild replay pool from frozen∩gate test rows; re-run gate report, range experiments, XAI study; fix script 54; range fails loudly when a model is missing; gate-only incidents get no ground-truth ATT&CK tag | overlap test: 0 replay rows in either training split (new pytest); all reruns regenerate docs |
| **R1b — claim corrections** | Regenerate paper numbers *from artifacts* (script, not by hand); seed-level statistics; condition every guarantee on exchangeability; report cross-dataset results and the W-sensitivity honestly; guide wording fixes above | a test that every number in `paper.tex` tables exists in a summary JSON |
| **R1c — gate auditability** | Persist gate verdicts (incident field + decision-trace step + metric); explicit combination policy (advisory vs union) shared by API and range | API test: gate-only alert produces an auditable record |
| **R2 — cross-dataset** | Separate tool shift from network shift: evaluate on datasets produced by **one** feature extractor (e.g. the NetFlow-standardised NF-* versions of CSE-CIC-IDS2018 / UNSW-NB15 / ToN-IoT, or corrected CICIDS2017 re-extractions); per-day warm-up windows; feature-alignment baselines | cross-dataset table with ≥ 2 target datasets, 5 seeds |
| **R3 — host/temporal layer** | Per-host windows (fan-out, distinct ports, beacon periodicity) fused as a third evidence source; evaluate Bot/PortScan LOAFO | Bot / PortScan zero-day recall vs flow-only, same α |
| **R4 — adaptive gate** | Online FPR monitor on confirmed-benign traffic (binomial test vs α), recalibration trigger, poisoning guard (cap per-source share in calibration) | simulated drift: violation detected within N flows; poisoning ablation |
| **R5 — packet-level testbed** | Mininet/netns + real traffic + CICFlowMeter/NFStream → existing pipeline | same scenarios measured on packets vs replay |
| **R6 — XAI evaluation** | Seeded LIME, more flows, faithfulness (deletion) test; small analyst study (with vs without explanations) | stability with CIs; study protocol + results |
| **R7 — system validation** | P8 harness extended to the gate + live stream; soak test (memory/CPU over hours) | operating envelope v3 |

**Not recommended now:** more classifiers, an LLM chatbot, more dashboard features, federated learning.
