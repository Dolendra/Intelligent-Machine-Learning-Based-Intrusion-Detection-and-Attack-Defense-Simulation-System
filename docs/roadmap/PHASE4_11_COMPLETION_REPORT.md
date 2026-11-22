# Phases 4–11 completion report

**Branch:** `research/phase4-11-completion` (from `main` at `de470a4`). **Date:** 2026-11-22.

## Objective

Complete the research project end to end from the point where Phase 3 stopped:
* protocol redesign;
* a controlled benchmark;
* the evidence-reliability investigation;
* a new method only if that investigation supports it;
* validation, the modular framework, integration, and final validation and publication.

Standing rules applied throughout:
* frozen v1.1 untouched;
* no historical output overwritten;
* no new ML algorithm;
* no dataset downloads;
* every published number traced to an artifact;
* negative results kept.

## Completed

| Phase | Outcome | Main documents |
|---|---|---|
| 4 Protocol redesign | Four protocol fixes implemented and tested: PR-01 smoothed conformal p-values, PR-02 frozen configs, PR-03 unified method names and a feature-only leakage report, PR-04 cross-dataset LOAFO. Also a staleness screen. Hypotheses A1–A7 and RS1/RS2 pre-registered; the user approved the campaign. | `docs/research/R3_AMENDMENT.md` |
| 5 Controlled benchmarking | Reduced CPU campaign: 6 evidence models × seeds 101–105 × 4 protocols, 780 records. **A1, A2, A4, A5 supported; A6 setting- and model-dependent; A7 rejected.** | `docs/research/R3_RESULTS.md` |
| 6 Evidence reliability | **RS1 and RS2 rejected.** The benign-only kNN screen saturates (0.62–1.00 on every 2018 day). | `docs/research/EVIDENCE_RELIABILITY_STUDY.md` |
| 7 New method | **Not built.** The pre-registered gate stayed closed; recorded as a negative result. | same |
| 8 Validation | Leave-one-fold-out, replication on new seeds, p-value rule, metric agreement and anomalous-day checks. Every verdict except A7 is stable under single-fold removal. | `R3_RESULTS.md` §3; `scripts/76_r3_validation.py` |
| 9 Modular framework | Typed module interfaces, registry and composable pipeline. The default pipeline is decision-identical to the service. | `docs/FRAMEWORK.md` |
| 10 Integration | `/api/framework/*`, `/api/research/r3`, Research Lab "R3 campaign" tab, end-to-end test. Docker production mode verified. | `docs/FRAMEWORK.md`, `docs/IMPLEMENTATION_STATUS.md` |
| 11 Final validation and publication | Both papers updated with an R3 section, the IEEE LaTeX recompiled (Tectonic) and validated (`scripts/63`: all checks pass). Release validation report generated. | `docs/research/Aegis_OSR_paper_ieee.pdf`, `docs/research/Aegis_Research_Paper.{docx,pdf}`, `reports/release/` |

## Findings (research)

1. **In-distribution (LOAFO).** Fixed Fisher fusion of a supervised stream with kNN benign novelty raises zero-day
   detection at a matched 1 % FPR for every tree-based evidence model tested (+0.134 to +0.268). It replicates the Phase 2
   XGBoost estimate on new seeds (+0.228 vs +0.218).
2. **Cross-network.** After per-day recalibration on CSE-CIC-IDS2018, the same fusion detects fewer known attacks than its
   own evidence model for all six models. The direction is confirmatory; the size is model-dependent.
3. **No transfer, no safe fixed rule.** The LOAFO gain does not transfer to unseen families on the new network, and
   max fusion is not a safe fixed alternative.
4. **No benign-only screen.** A benign-only exceedance screen does not predict stream reliability, so no gated method
   is justified by the development data.
5. **Exploratory only.** Refreshing the kNN reference with the warm-up flows largely removes the inversion. This needs
   its own pre-registered test.

## Tests and checks

| Check | Result |
|---|---|
| Python test suite (`pytest`) | 494 passed |
| Frontend (`vitest`, `tsc`) | 51 passed; typecheck clean |
| Regression gate (LOAFO, seed 1, `--tag phase4`) | PASS: historical artifacts unchanged, frozen v1.1 identical to tag, exact reproduction, complete dumps, overwrite protection |
| Leakage | `campaign_c`: 390 splits, all pass. `campaign_b`: fatal-on-failure checker, no traceback (`STREAM_NOTE.json`) |
| Reproduction anchor | 21,300 record values recomputed from per-flow dumps, max abs. diff 5.0×10⁻⁷ |
| LaTeX validation (`scripts/63`) | tables, macros, placeholders, cross-document headline facts, log (no undefined refs, 0 overfull boxes): PASS |
| Release validation (`scripts/75`) | **PASS** (`reports/release/release_validation_20261122_phase11b.json`): security 10/10 categories, integrity (32 protected files), framework parity (18 flows, 0 mismatches), R3 analysis. The first attempt (`..._phase11.json`) failed because the script did not isolate its environment. Its security checks then started the app against the developer database, which refused to start in production mode; startup recovery had already reclaimed 1 orphaned response action. The script now uses the test configuration with a throwaway database. |

## Deviations (all recorded before results were read, or execution-only)

* Seeds 101–105 instead of 101–110. Library defaults, no tuning. One warm-up window (2000).
* CatBoost dropped for compute (amendment 2, before any result). TabM and CLOSR deferred (GPU; LycoS hold).
* The campaign ran as two parallel streams (`R3_AMENDMENT.md` §5c). This is an execution change only.

## Pending / not done

* GPU campaign (TabM, CLOSR) and independent confirmation data (NF-v3, LycoS): blocked by budget and licence holds.
* Confirmatory test of the reference-refresh lead; within-2018 temporal protocol; no-port ablation (RES-12).
* Playwright browser journeys (optional).

## Approval

Pushing or merging this branch to `main` needs the user's approval.
