# Aegis IDS — Research Claim Audit (R1)

**Date:** 2026-11-17 · **Scope:** `docs/AEGIS_GUIDE_PLAIN_LANGUAGE.md`, `docs/research/paper.tex`,
`docs/research/legacy/PAPER_AEGIS_OSR_v1_STALE.md` (archived), `docs/research/*.md` vs. raw artifacts
(`research_artifacts/*_records.json`, `results/cyber_range/`, `research_artifacts/*.json`, code).
**Method:** every headline number was recomputed from *raw records*, not from summaries or docs.
The audit itself changed nothing; fixes were made afterwards in R1a (see §7 for status).

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
  LOIC-HTTP **0 %**, while Slowloris still transfers (95.6 %). *(R1b update: on the corrected v2 sample — random per-day attack sampling — DoS-Hulk is 1.1%, SSH 0.0%, but **LOIC-HTTP 45.0%**: the v1 file-order sample saw only the start of that attack. LOIC-HTTP is no longer evidence for the extractor hypothesis; Hulk and SSH still are.)* Identical tools vanishing points to
  **feature-extraction shift** (different CICFlowMeter versions; the 2017 one has documented bugs) confounded
  with network shift. Domain adaptation alone cannot separate the two.
* **2018 duplication:** after exact de-duplication FTP-BruteForce has **51** unique flows and SlowHTTPTest
  **55** (from ~190 k / ~140 k raw rows) — report per-label *unique* counts.
* **Protocol flaw in our cross-dataset adaptation:** the warm-up window is the earliest benign traffic of the
  *first* 2018 day while the test spans 10 days, so recalibration cannot be exchangeable with the test set.
* **Sampling defect found in R1b:** the v1 2018 sample capped every label *globally* in file order, so benign flows came from only 4 of 10 days. All 2018 numbers above were computed on that sample. Fixed in R1b (sample v2); see §8.

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

---

## 7. R1a status (2026-11-17)

Branch `v3-openset-research` (local, not pushed). `main` = `775e9a9` and tag `v1.1-research` untouched.

| Commit | What |
|---|---|
| `e84ab79` | Checkpoint of all pre-fix work (as audited) |
| `abf1d76` | R1a-B: shared incident policy, persisted gate alerts, no ground-truth leakage in the range |
| `b0ecc55` | R1a-A: leakage-free replay pool; gate head-to-head, Cyber Range and XAI re-run |
| `a09a48c` | R1a-C: seed-level statistics; paper numbers generated from artifacts; paper/guide corrections |
| `c127347` | Restored the frozen model's training provenance (`model_metadata.json` had been rewritten) |
| *(this commit)* | LOAFO reproduction (exact) + this status |

| Acceptance criterion | Result | Evidence |
|---|---|---|
| Frozen-model leakage | **0** replay rows in either model's train/val (was 69.6 %) | `replay_pool_manifest.json`; `tests/test_replay_pool_integrity.py` |
| Replay reproducibility | pool rebuilt deterministically (seed 42) with SHA-256 in the manifest; range runs are seeded | manifest; `tests/test_cyber_range.py` |
| Gate integration | every gate alert on a persisted detection → `zero_day_alerts` row (p, α, evidence, model version, frozen verdict, incident link); trace step; metrics | `tests/test_r1a_gate_integration.py` |
| Gate / range consistency | both call `security.detection_policy.decide()`; gate-only = `Zero-Day Candidate`, never a known family; no ground-truth ATT&CK/recommendation | same tests |
| Zero-day result reproduced | **exact**: independent re-run of all 30 LOAFO runs matches the original records bit-for-bit (1,320/1,320 metric values; Aegis-OSR 0.706 vs closed-set XGB 0.490) | `reproduction_loafo_repro.json`; `scripts/60_compare_reproduction.py` |
| Seed-level statistics | paired t over 5 independent seeds with CI of the difference; vs XGB +0.216 [0.180, 0.252], p = 7.6×10⁻⁵, 5/5 seeds | `significance_seed_level` in summaries |
| Paper traceability | 165 numbers + both LOAFO tables generated from artifacts with source paths; test fails on any drift | `paper_numbers.json`; `tests/test_paper_claims.py` |
| Frozen baseline unchanged | `binary_best`, `multiclass_best`, `feature_bundle`, `training_report`, `threshold_operating_point`, `model_metadata` identical to `v1.1-research` | `git diff v1.1-research` |

**What changed in the numbers after the fixes**

* Frozen v1.1 on flows it never trained on: benign FPR 0.064 % → **0.079 %**; known recall 0.993 → **0.993**;
  WebAttack 42.0 % → **41.6 %** (n = 77); Bot 61.7 % → **58.5 %** (n = 82). The weakness on minority families is real.
* Cyber Range headline numbers: **unchanged** (1,190 runs; zero-day 0 % vs 100 % at 4.3 s; 18 → 0 false incidents;
  isolate 27.4 % collateral; DDoS availability 99.5 % → 62 % with a 30 s delay).
* XAI stability: SHAP robustness below 0.90 for Bot (0.57), WebAttack (0.73) **and DoS (0.83)**; SHAP–LIME 0.27.
* Statistics: "p = 1.9×10⁻⁹" withdrawn; seed-level paired t used throughout.

**Also found and fixed during R1a:** tests wrote Cyber Range runs into the committed `results/` directory (now a
temp dir); the range silently scored all flows benign when a model failed to load (now a 503); the range picked
its recommended defense from the scenario's ground truth for unnamed detections (now a fixed conservative default).

**Still open (R1b and later):** the docx paper's remaining hand-typed tables (temporal, cross-dataset, range,
model families) should be generated like the LOAFO ones; the cross-dataset warm-up protocol (first-day window)
should be per-day; the 2017→2018 extractor-vs-network confound (R2); host-level detection for Bot/PortScan (R3).

---

## 8. R1b status — publication evidence consistency (2026-11-17)

Branch `v3-openset-research` (local, not pushed). `main` = `775e9a9` and tag `v1.1-research` untouched.

### What was built

* **One canonical pipeline** — `research/publication.py`: 18 table builders and 256 prose facts, each computed
  from a committed artifact and recorded with its source file and JSON path. Rendered three ways from the same
  objects: LaTeX (`docs/research/publication/tables/*.tex`, `\input` by `paper.tex`), Markdown
  (`docs/research/publication/TABLES.md`) and DOCX (`paper_build/paper.py` calls `PT(key)` for every table and
  interpolates `F[...]` in prose). `scripts/59_paper_numbers.py` emits the same facts as LaTeX macros.
* **No hand-typed numbers.** All 17 previously hand-typed DOCX tables were replaced (plus the new per-day table);
  43 prose paragraphs and 5 fragments now read their numbers from facts; table cross-references are computed.
  `research/literal_scan.py` finds result-like literals; the only allowed literals are design/configuration
  constants listed with a reason.
* **Duplicates removed:** the second LOAFO/significance table generator in script 59 and its two `.tex` files;
  stale builder backups moved to `paper_build/legacy/`; the stale markdown paper was archived in R1a.
* **Figures:** paper figures 3, 4 and 7 are now copied from their generators on every build. Figure 7 had been a
  pre-rerun Cyber Range image with no matching source.

### Corrected 2018 evidence

* **Sample v2** (`research/data.py`, `load_cic2018(version=2)`): 5 % of every day's benign flows, attacks capped per
  (day, label) by seeded random sampling — 1,098,993 flows, benign on all 10 days. v1 kept
  benign from 4 days. v1 records and summaries are retained unchanged; v2 results are written to new
  files (`*_v2.json`, `frozen_v11_on_cic2018_v2.json`).
* **Per-day recalibration protocol** (`research/protocols.py: cross_dataset_perday`): trained once per seed on
  CICIDS2017; for each 2018 day independently, warm-up = that day's earliest benign flows, evaluation = the rest of
  that day; `warmup_eval_overlap` is recorded per record and is 0 in all 50 records (10 days × 5 seeds).
* **Results (v2):** frozen v1.1 F1 0.278 (was 0.185 on v1; F1 depends on the sample's benign-to-attack mix),
  recall 0.162; Aegis-OSR unadapted FPR 36.7%; per-day recalibration at W = 2,000 → mean FPR
  1.62% (8 of 10 days ≤ 1.5 %; range 0.00%–8.84%), but
  known-family recall 0.088 and unseen-family recall 0.027. **Recalibration restores
  false-alarm control on most days but not detection — a negative transfer result.**
* **Data anomaly reported, not removed:** flows labelled benign on 2018-02-21 have median
  842,917 bytes/s vs 1,129 on other days and all alert before recalibration
  (100.0%); excluding the day gives a W = 2,000 mean FPR of 1.80%.

### Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| All 30 LOAFO reproduction pairs verified, none missing | 30/30, 1,320/1,320 values identical | `research_artifacts/reproduction_loafo_repro.json` |
| RESULTS.md: only the seed-level table | Wilcoxon table removed | `docs/research/RESULTS.md` |
| Range tests write only to temp dirs | enforced | `tests/test_range_output_isolation.py` |
| Every DOCX table generated from artifacts | 18/18 via `PT()`; DOCX cells equal canonical tables | `tests/test_publication_tables.py` |
| Equivalent LaTeX + Markdown tables from the same data | 18 `.tex` + `TABLES.md` from one build | same test (fresh rebuild equality) |
| No manually duplicated numerical results | 0 result-like literals in the DOCX builder; paper.tex uses only macros/generated tables | `research/literal_scan.py`; `tests/test_paper_claims.py` |
| 2018 recalibration per day, non-overlapping | 50 records, overlap 0 | `research_artifacts/openset_cross_perday_records.json` |
| Tables/figures regenerated; DOCX + PDF rebuilt | 18 tables, 7 figures; PDF 26 pages (Word export) | `docs/research/Aegis_Research_Paper.docx/.pdf` |
| Cited sources committed | test checks git-ignore status | `tests/test_publication_tables.py::test_cited_sources_are_committed` |
| Frozen baseline unchanged | model files, training report, thresholds, metadata identical to `v1.1-research` | `git diff v1.1-research` |
| **paper.tex compiled** | **PASS** — Tectonic 0.17.0 (XeTeX), 5 pages, 0 overfull boxes, 0 undefined references/citations | `docs/research/Aegis_OSR_paper_ieee.pdf` (SHA-256 `f6a49aed695ea194…`) |
| Compiled PDF matches canonical data | PASS — every numeric token of the 7 included tables and all 58 number macros found in the PDF text; no `??`/TODO/TBD/placeholder text; 10 headline facts present in both the LaTeX PDF and the DOCX-exported PDF | `scripts/63_validate_latex_pdf.py` → `docs/research/publication/latex_validation.json` |
| Validation not stale | PASS — the report records SHA-256 of `paper.tex`, `paper_numbers.tex` and each included table; the test fails if any source changes after validation | `tests/test_publication_tables.py::test_compiled_latex_paper_is_validated_and_current` |

### LaTeX build record

* Engine: Tectonic 0.17.0, official GitHub release `tectonic-0.17.0-x86_64-pc-windows-msvc.zip`; SHA-256
  `f61ce51f0b0ade1015b7de7ef368541c5424e9756ecbd0d7af97d6d48030845f` checked against the release-asset digest
  before first execution. Installed in a session scratch directory, not in the repository.
* Command: `cd docs/research && tectonic --keep-logs --outdir <out> paper.tex`, then
  `python scripts/63_validate_latex_pdf.py --pdf <out>/paper.pdf --log <out>/paper.log`.
* Formatting-only changes made to compile cleanly (no result changed): generated tables with > 4 columns use
  `table*` and shrink-to-width `adjustbox` (`research/publication.py: to_latex`); TeX Gyre Termes loaded by file name
  under XeTeX; the conformal alert rule moved from the display equation into the text; unused `algorithmic`
  package removed.
* All 5 pages were rendered and inspected: no clipped tables, no overlapping floats, no missing glyphs.
* Tests after the change: backend 281 passed; frontend 49 passed.
* Frozen v1.1 model, threshold, metadata and training-report files are byte-identical to `v1.1-research`
  (`git diff --quiet`). The v1.1 figure PNGs under `models/trained_models/figures/` were re-rendered in the
  pre-R1a checkpoint (`e84ab79`); they are images only, not model or metric files.

**R1b status: complete** — compilation and validation pass; the open items below are scope/positioning, not
consistency defects.

### Remaining limitations

1. `paper.tex` is the **condensed IEEE paper** (5 pages: method, LOAFO, temporal, 2018 transfer). It omits the system,
   cyber range, explanation, model-family and gate sections of the 26-page DOCX manuscript, has no figures and cites
   11 works. Its related work does **not yet position against the closest prior work** found in R2 (CLOSR, FIRCE);
   that must be added once the comparison in `RESEARCH_GAP_ANALYSIS.md` is reviewed. Remaining log items are
   cosmetic: 4 underfull boxes and IEEEtran's Times (`ptm`) shape warnings emitted before `fontspec` replaces it;
   the embedded text fonts are TeX Gyre Termes only (checked in the PDF font dictionary).
2. The plain-language guide is hand-written prose; its 2018 statements were regenerated from the facts, but it is not
   covered by the literal scan.
3. 2018 conclusions rest on one public export whose labels are known to contain errors (e.g. 2018-02-21).
4. Bot/WebAttack replay counts are small (82/77 flows); the model-family comparison is
   single-seed.
5. Novelty: the R2 review found close prior work (conformal false-alarm control for an IDS; one-class-held-out
   zero-day evaluation on corrected CICIDS2017 with code). See `RESEARCH_GAP_ANALYSIS.md`.

---

## 9. R2 follow-up — prior-work comparison and a new exploratory finding (2026-11-17)

**Documents.** `PRIOR_WORK_COMPARISON.md` (CLOSR, FIRCE, novelty re-check), `STATE_OF_THE_ART_REVIEW.md` addendum (F1–F9),
`RESEARCH_GAP_ANALYSIS.md` Revision 1, `R3_PROTOCOL.md` (proposed, not executed).

### 9.1 Claims affected by prior work

| Claim (paper / docs) | Status | Action |
|---|---|---|
| Conformal false-alarm control for NIDS | Done before (B17, F5, F7) | Never claim as new; cite |
| "The guarantee breaks under 2017→2018" | Replication of F2 (coverage collapse, Frontiers in AI 2026) | Cite F2; claim only the FPR-level and per-day measurements |
| Fisher-style fusion of evidence | Combination with Type-I control exists (MaSF, F3); naive Fisher of dependent conformal p-values is invalid (B11) | State that the *sum* is re-calibrated on a disjoint split (valid), and that this is engineering, not a new test |
| Mondrian attribution, hybrid fusion at a fixed FPR | Possibly done (F4, F6 — not readable) | **No novelty statement until F4 and F6 are read** |
| Better zero-day detection than prior methods | Not established: CLOSR has never been compared at a calibrated α | Forbidden until R3-H3 |

### 9.2 New exploratory finding (post hoc, hypothesis-generating)

`scripts/64_recalibration_diagnosis.py` reads only committed records (`openset_cross_perday_records.json`) and
writes `research_artifacts/recalibration_diagnosis.json`. Seed-level, n = 5.

* At recal@2000, every method sits at a comparable realized FPR (1.4–1.6 %). Even so, closed-set XGB alone has higher
  known recall than Aegis-OSR: +0.237 [+0.153, +0.322], 5/5 seeds. XGB + Energy has +0.345, and max fusion +0.215.
* The kNN novelty stream ranks 2018 attacks at or below chance (AUROC 0.51 mean; 0.05 on 2018-02-16).
* Refreshing the kNN reference with target benign raises Aegis-OSR known recall to 0.435–0.532, but the FPR rises to
  2.4–2.6 %, over the 1 % budget.
* A recalibrated XGB detects 2018-02-14 brute force (0.984) and 2018-02-16 DoS (0.920) at ≤ 1 % FPR.

**Status.**
* The measurements are read directly from records.
* The "dilution" mechanism is *inferred*: per-flow scores were not stored.
* The finding was made on data already inspected, so it motivates Contribution 1 and **cannot confirm it**.

### 9.3 Paper statement that needs correction (pending approval)

`paper.tex` §IV-E and the DOCX say:

> "Two attack tools present in both datasets lose detection almost entirely … Identical tools becoming undetectable
> suggests that flow-extractor differences between the two releases are confounded with network shift" (paper.tex line 137).

This holds for the **frozen v1.1 detector at its fixed thresholds** only. A retrained classifier recalibrated on 2,000
target-day benign flows separates the same days' attacks (AUROC 0.999–1.000). Proposed wording:

> "… are missed by the frozen detector at its fixed thresholds; after same-day recalibration a retrained classifier
> separates them, so the shift moves scores rather than erasing the signal."

The new numbers must enter through `research/publication.py` facts sourced from `recalibration_diagnosis.json`.

**Applied (approved by the user, 2026-11-17).** Every affected occurrence:

| Location | Before | After |
|---|---|---|
| `paper.tex` §IV-E | "lose detection almost entirely" | "are almost entirely missed by the frozen detector at its fixed operating thresholds" |
| `paper.tex` §IV-E | "Identical tools becoming undetectable suggests …" | "This does not make those attacks undetectable …", plus the recalibrated-classifier evidence (facts `rd_xgb_*`, labelled exploratory/post-hoc) and the extractor confound kept as a possibility |
| `paper_build/paper.py` (DOCX), 2018 transfer section | "were barely detected" / "Identical tools becoming undetectable suggests …" | same corrections as above |
| `paper_build/paper.py` (DOCX), conclusion | "the gate turned an undetectable zero-day scenario" | "a zero-day scenario that the frozen detector did not detect" (same over-claim, cyber-range result) |
| `CLAIM_AUDIT.md` §5, `RESEARCH_GAP_ANALYSIS.md`, `STATE_OF_THE_ART_REVIEW.md` | — | already qualified in §9 / Revision 1; §5 is kept as the historical audit text |

* No numerical result changed. The six new facts (`rd_xgb_{bf,dos}_{known,fpr,auroc}`) are read from
  `research_artifacts/recalibration_diagnosis.json` (the closed-set XGB recal@2000 row for 2018-02-14 and 2018-02-16).
* Rebuilt: `paper_numbers.tex`, the DOCX and the Word PDF. `paper.tex` was recompiled with Tectonic 0.17.0
  (checksum re-verified). `scripts/63` passes: 5 pages, 0 overfull boxes, 0 undefined references. The new log has
  4 underfull-vbox float-placement warnings (cosmetic).
* **Related sentence not changed** (outside the approved scope, flagged for decision). `paper.tex` §IV-E says
  "Recalibration controls false alarms … it cannot create separation the evidence lacks." It is literally true, but
  next to the corrected paragraph it implies that the *evidence* lacks separation on 2018. The diagnosis shows that the
  *supervised* evidence keeps it on several days, while the fused score loses it. Suggested wording: "it cannot restore
  separation that the fused score has lost". The DOCX has the same sentence (`paper_build/paper.py`: "cannot create separation that the evidence does not contain").

---

## 10. R3 Stage 0 — environment, regression gate, pilots (2026-11-17)

Stage 0 runs no R3 campaign. All new outputs live under `research_artifacts/r3/`, and the historical artifacts are protected (`PROTECTED_MANIFEST.json`).

### 10.1 Regression gate — PASS (`research_artifacts/r3/regression_gate_report.json`)

The gate ran `scripts/65_regression_gate.py` (code at `bf5fd3f`, main environment, 8,470 s):

| Check | Result |
|---|---|
| Historical artifacts (25 files, SHA-256 manifest) | unchanged |
| Frozen v1.1 model / threshold / report files (16) | byte-identical to tag `v1.1-research` |
| Frozen v1.1 re-scored on CSE-CIC-IDS2018 v2 | reproduces `frozen_v11_on_cic2018_v2.json` (binary metrics, per-label rows, sampling) |
| LOAFO, seeds 1–5, re-run **with per-flow score dumps** | 30/30 records; **6,690/6,690 values identical** |
| Per-day 2018, seeds 1–5, re-run with dumps | 50/50 records; **61,730/61,730 values identical** |
| Score completeness | 380 record×variant dumps, 15,327,730 evaluated flows; every flow has finite raw / surprisal / fused / p-value scores |
| Overwrite protection | writes to protected paths are refused (scripts 50, 54, 64, 65, 67) |

### 10.2 Finding: float32-identical duplicates crossed the historical splits

`research/data._finalize` de-duplicates on (features, fine label) at source precision and **then** casts the features to float32. Rows that differ only beyond float32 precision therefore survive as exact float32 duplicates:
* CICIDS2017: 22,818 extra copies (0.9 % of rows): 22,803 benign and 15 DoS.
* CSE-CIC-IDS2018 sample: 18,839.

In addition, 718 CICIDS2017 rows have features identical to a row with a *different* label (label conflict).

**Effect on the committed results.** `scripts/69_duplicate_overlap_audit.py` rebuilt the historical splits without training (`research_artifacts/r3/duplicate_overlap_audit.json`):

| Protocol | Twin location | Rows (mean, max) | Share |
|---|---|---|---|
| LOAFO | test benign row with a twin in **training** | 469 (max 478) of 150,000 | 0.31 % |
| LOAFO | test benign row with a twin in the **validation** split (the source of C1/C2) | 96 (max 109) | 0.064 % |
| Per-day 2018 | evaluation row with a twin in that day's **warm-up** | 0–2 rows on 9 of 10 days | — |
| Per-day 2018, 2018-02-28 (Infiltration day) | same | 165 of 19,193 | 0.86 % |

The per-day records' `warmup_eval_overlap = 0` counted shared *indices*, not shared *content*. The content check above supersedes it.

**Bound on the effect.** Each realized FPR is a fraction of test benign flows. Even if every twin had flipped its alert decision, the change would be at most:
* 0.31 percentage points for LOAFO, against the reported 1.00 %;
* 0.86 points on 2018-02-28, where every method is already near chance.

The likely direction is a slight *under*-estimate of FPR, because a twin of a training or calibration flow looks typical. None of the paper's conclusions depend on effects of this size. The paper and RESULTS keep the committed numbers, with this note.

**Fix (R3 onward).** R3 de-duplicates at float32 precision before any split (`research/data.dedup_float32`, R3_PROTOCOL §14 A1). The R3 leakage checker caught the problem on its first smoke run. The historical code path is unchanged, so the regression gate keeps proving exact reproduction.

### 10.3 Status labels

| Item | Status |
|---|---|
| Aegis-OSR LOAFO / temporal / 2018 results | **Reproduced** (exact; LOAFO and per-day checked in Stage 0) |
| Recalibration diagnosis (fusion loses supervised separation under 2018 shift) | **New exploratory finding** — not yet confirmed on independent data |
| Evidence-stream reliability gating (Contribution 1) | **Hypothesis** — criteria pre-specified (`RESEARCH_GAP_ANALYSIS.md` §3), untested |
| CLOSR | **Executed in pilot only** (official modules on CICIDS2017, 2 epochs); published numbers **not** reproduced (LycoS not approved) |
