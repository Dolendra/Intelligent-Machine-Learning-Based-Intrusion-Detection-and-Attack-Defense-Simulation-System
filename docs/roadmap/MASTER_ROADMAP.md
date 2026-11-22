# AEGIS master roadmap

**Status:** adopted 2026-11-18 after the Phase 0 audit. This replaces the earlier 12-phase sequence: a correctness-remediation stage and a claim-correction stage now come **before** any further research compute or framework work.

**Target:** AEGIS — Adaptive, Explainable and Open-Set Cybersecurity Intelligence Framework. A modular, reproducible research platform whose contribution must be experimentally validated, never forced.

**Three goals, tracked separately:**

| Goal | Success means |
|---|---|
| Correct application | Every implemented function behaves correctly and is tested |
| Research contribution | A scientifically defensible new finding or method |
| Research framework | A modular platform for reproducible comparison of methods |

## Phases

Every phase ends with a phase report and an approval gate. No phase starts automatically.

| # | Phase | Purpose | Entry condition | Acceptance condition | Status |
|---|---|---|---|---|---|
| 0 | Audit completion | Establish the true state of the repository (four reviews + consolidation) | — | 9 audit documents reviewed by the user | **Done** (2026-11-18) |
| 1 | Correctness remediation | Fix the application, ML serving, feature processing, logging, risk, Docker and security defects (REMEDIATION_PLAN P0–P2 code items) | Remediation plan approved; remediation branch approved | Every fixed finding has a regression test; full suite + frontend + migration checks pass; frozen v1.1 and protected artifacts are unchanged | **Done** (P0/P1, 2026-11-18) |
| 2 | Research-claim correction | Correct misleading performance, false-alarm, temporal-generalization and mitigation claims (ML-1–ML-4, ML-12, RES-1, RES-3, RES-4, RES-11; decision E). Corrected numbers go into **new, versioned** artifacts | Phase 1 items that the corrected numbers depend on are done | Claims match the artifacts; publication tests extended with forbidden-phrase checks | **Done** (RESEARCH_INTEGRITY_REPORT.md) |
| 3 | R1b and R2 closure | Rebuild and validate both papers after the corrections; read the remaining closest papers (Springer Mondrian triage, MDPI fixed-FPR fusion, F4, F6) | Phase 2 done | Papers validated (script 63); novelty statement re-checked | **Done** (LaTeX validated 2026-11-22) |
| 4 | Research protocol redesign | Fix R3: randomised conformal p-values or matched-FPR reporting (RES-2); implemented and frozen tuning (RES-10); temporal protocol; per-day oracle and contamination controls (RES-9, RES-15); time-separated W_r/W_c (RES-8); family- and day-level uncertainty (RES-7); design-free confirmation flows (RES-6); no-port ablation (RES-12); timestamp ordering (RES-14); support/rejection criteria F1–F5 for reliability-aware fusion | Phase 3 done | R3_PROTOCOL amendment approved by the user | **Done**: R3_AMENDMENT.md, approved 2026-11-22 |
| 5 | Controlled benchmarking | CPU models, then TabM/CLOSR on the GPU within the approved budgets, all at matched realised FPR | Phase 4 approved | Benchmark report with CIs, failed runs and CPU/GPU agreement | **Reduced CPU campaign** (6 models; GPU models deferred): R3_RESULTS.md |
| 6 | Research investigation | When and why the supervised and novelty streams become unreliable; whether that can be estimated from benign data; cross-dataset LOAFO; within-2018 temporal | Phase 5 done | EVIDENCE_RELIABILITY_STUDY.md with support/rejection verdicts | **Done**: RS1 and RS2 rejected (EVIDENCE_RELIABILITY_STUDY.md). Within-2018 temporal not run |
| 7 | New method development | Only if Phase 6 supports it: formal method, pseudocode, complexity, fallback policy | Phase 6 supports the hypothesis | Method spec + implementation + tests | **Closed, not built**: the pre-registered gate stayed closed (negative result recorded) |
| 8 | Scientific validation | Ablations, independent data (subject to permission), multiple seeds, matched FPR, paired tests | Phase 7 done | Contribution supported, revised or rejected, and reported either way | **Done** for the R3 findings (R3_RESULTS.md §3, `scripts/76`); independent data not used (downloads on hold) |
| 9 | Modular framework development | Interchangeable detection / open-set / explanation / adaptation / decision modules behind typed interfaces | Phase 8 done | Interfaces with tests; existing behaviour preserved | **Done**: `framework/`, docs/FRAMEWORK.md |
| 10 | Full integration | Connect validated modules to the dashboard, response workflow and Cyber Range | Phase 9 done | End-to-end tests | **Done**: API + Research Lab + Docker verified |
| 11 | Final validation and publication | Security, deployment, performance, reproducibility and paper validation | Phase 10 done | Release checklist | **Done**: `scripts/75_release_validation.py` report, papers rebuilt and validated (docs/roadmap/PHASE4_11_COMPLETION_REPORT.md) |

## Standing rules (apply to every phase)

**Protected baselines and results**
- Never modify `main`, the `v1.1-research` tag or the frozen v1.1 files.
- Never overwrite historical results.
- New results go into new versioned files.

**Approvals**
- No push, merge or publication without explicit approval.
- No R3 training before the protocol is approved.
- No dataset download before licence permission is established (LycoS: HOLD).

**Research integrity**
- No test-set selection.
- Seed-level statistics; folds are not treated as independent samples.
- Every number traces to an artifact.
- Negative results are kept.
- Implemented features, validated findings and hypotheses are kept distinct.

**Scope**
- One phase at a time.
- Every phase ends with this report: Objective, Completed, Files changed, Experiments, Tests, Findings, Pending, Next phase, Approval needed.
