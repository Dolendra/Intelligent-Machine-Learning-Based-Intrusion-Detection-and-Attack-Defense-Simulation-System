# Phase 1 remediation plan

**Status:** PLAN ONLY. Proposed 2026-11-18. **No code has been changed.** Implementation needs:
1. approval of this plan;
2. an explicitly approved remediation branch (proposal in §8).

**Sources:** `docs/research/` FULL_REPOSITORY_AUDIT, SECURITY_AUDIT, ARCHITECTURE_AUDIT, ML_PIPELINE_AUDIT, RESEARCH_ALIGNMENT_REVIEW. All 104 findings are covered. Findings that are the same defect seen by two reviewers are merged into one remediation item (`R-xx`). The `Sources` column keeps every original ID.

## Legend

**Kind**

| Code | Meaning |
|---|---|
| C | Confirmed defect |
| P | Potential risk |
| R | Recommendation |
| U | Unverified assumption |

**Size**

| Code | Meaning |
|---|---|
| S | Under 1 hour, one module |
| M | Several modules, or a new test fixture |
| L | Cross-cutting change, or a new evaluation run |

**Tiers**

| Tier | Scope |
|---|---|
| P0 | Data integrity, misleading claims, incorrect risk decisions, silent failures, protection of frozen assets |
| P1 | Core application correctness, ML inference, CSV/PCAP, Docker runtime, security controls that do not work |
| P2 | Explainability, observability, reliability, WebSocket, queue, lifecycle, hardening |
| P3 | Maintainability and architecture |

**Research tracks** (§5) are planned separately and are not Phase 1 code work:

| Track | Scope |
|---|---|
| D | Documentation and claim corrections (Phase 2) |
| E | New versioned evaluations (Phase 2; needs approval to run) |
| PR | R3 protocol amendments (Phase 4) |

## Rules that apply to every item

1. **Frozen and historical files.**
   * Never modify the 16 frozen v1.1 files or the 25 manifest-protected research artifacts.
   * Never modify `main` or the `v1.1-research` tag.
   * Every corrected number goes into a **new, versioned** artifact, e.g. `research_artifacts/v11_reeval/…`, with a manifest. The old artifacts stay as they are.
2. **One item at a time.** Each item is implemented, then a regression test is added, then the full validation set (§7) is re-run, then the item is committed separately.
3. **Documentation.**
   * `main`-branch documents inherited by the remediation branch are corrected only on that branch. `main` itself stays unchanged until a merge is separately approved.
   * Superseded claims are marked, not deleted, so the history stays visible.
4. **No research compute.** No R3 training and no GPU runs in Phase 1. E-track evaluations run only after explicit approval.

---

## 1. Prioritised remediation matrix

### P0 — data integrity, misleading claims, incorrect risk, silent failures

| R-ID | Sources | Sev | Kind | Files | Depends on | Correction | Regression test | Acceptance | Size |
|---|---|---|---|---|---|---|---|---|---|
| R-01 | ARCH-2, ML-5, ARCH-19 | High | C | `backend/services/pipeline.py:381-386`, `backend/services/live_stream.py:237,278`, `security/risk/engine.py` | — | Read `risk_score`. Pass the measured intensity for gate-only incidents. Make `compute_risk` return a TypedDict so a wrong key fails type checking. | A gate-only incident has `risk_score > 0` and the correct band (Heartbleed demo → HIGH). The live tick carries a risk > 0 for attacks. | Both tests pass. Incident page, exports and live risk are non-zero for attacks. | S |
| R-02 | SEC-5, ARCH-3, ARCH-22, SEC-8 | High | C | `alembic/env.py:20`, `database/db.py:203-208`, `backend/middleware/logging_mw.py:26,36`, `backend/routes/api.py` (login), `security/auth/service.py` | — | `fileConfig(..., disable_existing_loggers=False)`, only when run from the CLI. Read `aegis_user`/`aegis_role` in the logging middleware. Record login success and failure as `security_event` plus a metric. | After the lifespan starts, the `aegis.*` loggers are enabled and root ≤ INFO. A request produces an `http_request` log line containing the user. A failed login writes a security-event row. | Tests pass. A manual start shows request and 500-error logs. | S |
| R-03 | ARCH-18 | Medium | C | `backend/routes/api.py:320`, `backend/services/pipeline.py:1083-1127` | — | Make SHAP refresh a POST with an admin/`write_detect` permission. Write to a cache directory outside `models/trained_models`. Call `assert_writable`. | `GET /api/models/shap/global?refresh=true` never writes. The frozen-file diff stays empty. | The frozen v1.1 diff is empty after the test. | S |
| R-04 | ARCH-10, ML-22 | Medium | C | `backend/services/pipeline.py:253-268`, `backend/observability/health_checks.py:102`, `research/serving.py`, `pipeline.py:41-52` (lru_cache) | R-02 | Log and count gate exceptions, and surface `zero_day_status: "error"`. Readiness includes the gate when the policy needs it. Do not cache loader failures. | With the gate artifacts missing: readiness is not-ready under the `gate`/`union` policy, a metric increments, and the error is logged. A row with missing features does not nullify the whole batch. | Tests pass. | M |
| R-05 | SEC-1, SEC-2, SEC-7, SEC-28, SEC-16 | High | C | `security/auth/tokens.py:20-25`, `security/auth/users.py:17-20`, `database/bootstrap.py`, `backend/middleware/api_auth.py`, `rate_limit.py`, `request_limits.py`, `errors.py`, `backend/routes/api.py:57-108` | — | Fail closed at startup when auth is on and the secret is missing or weak, or equal to the API key, or a `ChangeMe*` seed is active. Remove both fallbacks. Honour the `DISABLE_*` switches only in dev/test, and log a WARNING. One helper computes the effective settings, used by the middleware and `/security/status`. | Startup with auth on and no secret raises. A token signed with the old constant gets 401. Seed `admin`/`ChangeMeAdmin!` gets 401 or startup fails. `/security/status` reports the overrides. A key-minted token is rejected. | All five tests pass. The P4/P5 suites still pass. | M |
| R-06 | SEC-3, SEC-23 (part) | High | C | `config.yaml:154`, `docker-compose.yml:7,11,26`, `backend/routes/api.py` (`/auth/users`) | R-05 | Refuse to start with auth off outside `AEGIS_ENV=development`. Compose binds to loopback, publishes only nginx, and enables auth with secrets from an `env_file`. Remove the anonymous `/auth/users` branch. Local demos keep working via `AEGIS_ENV=development`. | `AEGIS_ENV=production` with auth off fails at startup. Anonymous `/auth/users` gets 401/403. A compose lint asserts the loopback bindings. | Tests pass. The demo documentation is updated. | M |
| R-07 | SEC-4, SEC-20 (CSV part) | High | C | `backend/middleware/request_limits.py:55-57`, upload handlers in `backend/routes/api.py` | — | A pure ASGI middleware counts the body bytes actually received, whether or not Content-Length is present. Uploads are read in bounded chunks. The row cap is checked before the full parse. | A 5 MB chunked JSON body gets 413. A 40 MB chunked PCAP gets 413 from the middleware before the handler runs. A 12 MB chunked CSV gets 413/422 without a full parse. | Tests pass. RSS stays bounded (logged). | M |
| R-08 | SEC-6, SEC-18 | Medium | C | `security/response/store.py:163-184`, `database/db.py:149`, incident update path in `backend/services/pipeline.py` | — | Remove the count-based audit deletion; optionally add a hash chain. Pass the real actor to incident updates and simulations. | The audit rows of an executed action survive 600 later proposals. A PATCH by user X records actor X. | Tests pass. | S |

**P0 documentation and claims.** These are D-track items and are executed in Phase 2, but they are tracked here because they are P0: D-01 to D-08 in §5.

### P1 — core correctness, ML inference, CSV/PCAP, Docker, controls that do not work

| R-ID | Sources | Sev | Kind | Files | Depends on | Correction | Regression test | Acceptance | Size |
|---|---|---|---|---|---|---|---|---|---|
| R-09 | ARCH-1 | High | C | `Dockerfile.api:13-20`, `.github/workflows/ci.yml` | R-06 | COPY `cyberrange/`, `research/` (serving modules) and `research_artifacts/replay/` (pool + manifest). Add a compose smoke job. | CI: `docker compose up`; `/api/ready` returns 200; `/api/zero-day/status` returns available. | The smoke job passes. Locally, a build and run, **if Docker is available** (otherwise this stays an unverified assumption). | M |
| R-10 | ARCH-4, ML-13 | High | C | `backend/services/pipeline.py:938-990`, `backend/routes/api.py:379-400`, `ingestion/adapters.py` | — | Route `/predict/batch/csv` through `ingestion.pipeline.ingest_flows_csv`, so there is a single parser. | A raw MachineLearningCVE header row (leading spaces, duplicate column) is accepted by every CSV endpoint. | Test passes. The existing CSV tests still pass. | S |
| R-11 | ML-8, ML-14 | Medium | C | `ml/prediction/predictor.py:75-83,188-190`, `backend/routes/api.py:353`, `backend/schemas/api.py`, `ingestion/validate.py:74`, `research/serving.py:93` | R-10 | One documented NaN/Inf/missing-value policy: a per-row 422 with a reason. Reject non-finite JSON values in the schema. Always return `missing_features`. Do not zero-fill silently in DEMO_MODE (or impute train medians and flag it). The gate handling must be documented and consistent with this policy. | NaN or Infinity in `/predict` gives 422, not 500. One Infinity row in a CSV gives a per-row error and the other rows are scored. A missing feature is reported. | Tests pass. No 500 is reachable from malformed numbers. | M |
| R-12 | ML-9 | Medium | C / U | `ingestion/normalize.py:149`, `ingestion/cicflowmeter_runner.py`, `tests/` fixture | R-10 | Normalise `_` to a space. Add an alias table for the snake_case headers of Python `cicflowmeter`. Label PCAP as "experimental" until a real fixture validates the units. | A snake_case header fixture maps all 78 features. | Mapping test passes. Units parity is recorded as unverified until the tool and a fixture are available. | S/M |
| R-13 | ARCH-7, SEC-9, SEC-20 (rest) | Medium | C | `backend/routes/api.py:379,411,465,595,623,1159-1239`, `ingestion/cicflowmeter_runner.py:39`, `backend/routes/range.py` | — | Make the blocking handlers `def`, or use `run_in_threadpool`. Use an async subprocess. Run one shared analytics producer for `/ws/events`. Rate-limit and cap the range sweep, `limit` parameters and WebSocket connections. | `/health` p95 stays below 200 ms while a long CSV/PCAP job runs (a stub sleeps 5 s). Out-of-range `limit` values are clamped. | Tests pass. | M |
| R-14 | ARCH-5 | Medium | C | `security/response/service.py:342-359`; `tests/test_productionization_p6_persistence.py:95-98` | R-08 | Persist the final VERIFIED or FAILED status. Tighten the P6 test. | After approve, the DB row is VERIFIED or ACTIVE, and it is the same after a restart. | Test passes. `/ops/status` counts the action. | S |
| R-15 | ARCH-6 | Medium | C | `backend/services/pipeline.py:802-810` | — | Never force the status. A terminal incident keeps its status and only gets an event (or a 409). | Simulating a Resolved incident leaves it Resolved and `resolved_at` unchanged. | Test passes. | S |
| R-16 | ARCH-12 | Medium | P | `backend/services/pipeline.py:442`, `security/correlation/__init__.py:87` | — | IDs of at least 12 hex characters (or a sequence), with retry on IntegrityError. | A forced collision (patched `uuid`) is retried and recorded. | Test passes. | S |
| R-17 | SEC-10, SEC-11 | Medium | C / U | `backend/middleware/rate_limit.py`, `backend/main.py:119-136`, `frontend/nginx.conf`, uvicorn arguments | R-06 | Forward the client IP from nginx. Run uvicorn with `--proxy-headers --forwarded-allow-ips=<nginx>`. Key on the forwarded IP only from a trusted proxy. Place the limiter outside auth (or add an auth-failure limiter). | Two distinct `X-Forwarded-For` values from a trusted proxy get separate buckets. Untrusted XFF is ignored. Repeated bad keys get 429. | Tests pass. The U-1 assumption is checked when Docker is available. | M |
| R-18 | ML-21, SEC-22 | Low / Medium | P | `requirements.txt`, `requirements-lock.txt`, `Dockerfile.api:10-11`, CI | — | Regenerate a hashed lock file from the **current verified environment**, with no version changes to ML packages (sklearn 1.9.0, xgboost 3.2.0). Upgrade only the packages with advisories, such as `python-multipart`, and only after the full test suite plus the regression gate pass. Install from the lock in Docker and CI. | CI installs from the lock. The frozen models unpickle. The test suite passes. | Lock installed in CI. No ML version drift. | M |
| R-19 | ARCH-15 (+ lint) | Medium | C | `.github/workflows/ci.yml` | R-18 | Run CI on the `v3-openset-research`, `audit/**` and `remediation/**` branches. Add an Alembic upgrade+check step, ruff (and mypy on `backend/`, `security/`), and the compose smoke job (R-09). Align Node versions. The frozen-baseline checks stay read-only. **This changes CI configuration: it needs approval and does not run until something is pushed.** | The workflow lint passes. A local `act`-style dry run is not required. | Approved diff. Green on the first approved push. | M |

### P2 — explainability, observability, reliability, WebSocket, queue, lifecycle, hardening

| R-ID | Sources | Sev | Kind | Files | Correction | Regression test / acceptance | Size |
|---|---|---|---|---|---|---|---|
| R-20 | ML-6 | Medium | C | `explainability/lime_engine.py`, a new per-stage background artifact (new file; `shap_background.npy` stays untouched) | Use a per-stage background, explain the predicted class, map features by index. | LIME names equal the multiclass-selected features, and the explained class equals the prediction. | M |
| R-21 | ML-7 | Low | C | `explainability/shap_engine.py`, the explain route, UI | Return the stage-1 (alert) and stage-2 (family) explanations, labelled. | Attack explanations contain both stages. | M |
| R-22 | ARCH-9 | Medium | C | `ingestion/queue.py:114,166-183` | TTL/LRU eviction. Results retrievable. Configurable persistence. | 1,000 jobs keep memory bounded. Results can be fetched. | M |
| R-23 | ARCH-11, SEC-21 | Medium | C | `security/response/service.py:453`, `database/retention.py`, `backend/main.py`, `ingestion/cicflowmeter_runner.py:33` | A lifespan background task sweeps expired actions and purges retained data. Use `TemporaryDirectory`. | An action with a 1 s duration expires without a restart. The temp directory is removed. | M |
| R-24 | ARCH-13, ARCH-14, ARCH-24, SEC-23 (rest), SEC-27 | Medium | C | `frontend/nginx.conf`, `frontend/vite.config.ts`, `frontend/src/services/api.ts:1349-1362`, `backend/main.py:120` | Upgrade headers in nginx, `ws: true` in Vite, a same-origin `wsUrl`, CORS as the outermost middleware, `client_max_body_size 32m`, security headers. Token via subprotocol or a short-lived ticket. | A 401 carries the CORS header. A `wsUrl` unit test. A compose WebSocket handshake in the smoke job. | M |
| R-25 | ARCH-17 | Low | C | `backend/routes/v3.py:111-127`, `backend/routes/api.py:1182-1205` | Accept the WebSocket first, then send an error frame and close with 4401/4403. | The client receives 4401. | S |
| R-26 | ARCH-8, SEC-25 | Medium | P | `backend/main.py`, `backend/recovery/startup.py:42` | Enforce a single worker (fail if `WEB_CONCURRENCY` > 1), and document it. Recovery reclaims only actions older than a lease. | Startup with 2 workers fails. A fresh EXECUTING action is not reclaimed. | S |
| R-27 | ARCH-23, SEC-24, SEC-26 | Medium | P / R | `security/response/service.py:186-270`, `security/rbac.py`, UI | Approver must differ from proposer (four-eyes). Approve+execute becomes atomic, with a status rollback on pre-execution errors. Validate targets against an allowlist. | Self-approval gets 403. Unknown adapter → status returns to PROPOSED. An invalid target gets 422. | M |
| R-28 | SEC-12, SEC-13, SEC-14, SEC-17 | Low | C | `backend/middleware/api_auth.py:177-178,254`, `security/auth/tokens.py:56-70`, `security/auth/users.py:168-174` | Constant-time comparison; header-only keys; multiple keys; `token_version` revocation; `iat` and maximum-lifetime checks; byte comparison; dummy-hash timing. | A token is invalid after logout. A non-ASCII signature gets 401, not 500. A `?api_key=` query parameter gets 401. | M |
| R-29 | SEC-15, SEC-19, SEC-29 | Low | C | public status routes, `backend/services/pipeline.py:996-1018`, `backend/schemas/api.py:133-136`, `scripts/40_db_backup_restore.py` | Trim public payloads; disable `/docs` in production; neutralise CSV cells; add `max_length`; restore only after verification. | A formula cell is escaped. Public endpoints carry no absolute paths. A corrupt backup does not destroy the target. | M |
| R-30 | ML-15, ML-16, ML-18, ML-23 | Low | C | `security/recommendations/engine.py:168`, `backend/services/pipeline.py:91,170`, `backend/services/decision_trace.py:37`, `security/response/planner.py:12` | Risk confidence = P(attack). Report the predictor's threshold. Correct the certainty-band wording. Align the DDoS plan with the recommendation. | Trace labels both numbers. `model_info` threshold == predictor threshold. | S |
| R-31 | ARCH-20, ARCH-21, ARCH-25, ARCH-26, ARCH-16 | Low | C / P | `cyberrange/engine.py:46`, `backend/middleware/metrics_mw.py`, `rate_limit.py`, `simulation/engine/core.py`, `backend/services/pipeline.py:566-585`, `backend/main.py:82`, `database/url.py:27`, `alembic.ini:4` | Move `RUNS_DIR` out of the repo or git-ignore it. Bound in-memory maps. Use route-template metric labels. Persist batches once. Drain the queue on shutdown. SQLite WAL + busy timeout. Absolute Alembic `script_location`. | A UI range run leaves `git status` clean. Starting from another CWD still runs Alembic. | M |

### P3 — maintainability and architecture (after P0–P2; no restructuring in Phase 1)

| R-ID | Sources | Kind | Proposal | Size |
|---|---|---|---|---|
| R-32 | ARCH-27 | R | Consolidate: one auth-settings helper (shared with R-05), one WebSocket-auth dependency, one PCAP-ingest service, one replay/scoring module for `live_stream` and `cyberrange`. Mark `simulation/` as a legacy demo. | L |
| R-33 | ARCH-28 | R | Split `api.py`, `pipeline.py` and `api.ts` by bounded context. Inject the scorer into `cyberrange`. Move observability out of the web package. **Deferred to Phase 9 planning.** | L |
| R-34 | ARCH-29 | R | Add Pydantic response models for UI-consumed routes, and generate TypeScript types from OpenAPI in CI. Add the missing v3 incident fields to the TS types. | M |
| R-35 | ARCH-30, ML-19, ML-17 | R | Remove or label dead endpoints and client methods. Renumber the duplicate `scripts/30_*`. Move legacy research files out of the main tree (in a new commit; history kept). Fix or delete script 14. Align `ModelVersionRef` seeds. Mark Infiltration/Heartbleed as unpredictable by the frozen model. | M |
| R-36 | ARCH-15 (frontend) | R | Frontend tests for Detection, IncidentDetail, LiveMonitor, ZeroDayLab, Reports, System, Dashboard, Login, prioritising the flows touched by R-01, R-10, R-14, R-15 and R-24. | M |

---

## 2. Dependency graph

```
R-02 logging ──► R-04 gate visibility
R-05 auth fail-closed ──► R-06 compose/defaults ──► R-09 Docker image ──► R-19 CI smoke
                                       └──────────► R-17 proxy/rate limit
R-18 lock file ──► R-19 CI
R-10 one CSV parser ──► R-11 NaN/Inf policy ──► R-12 PCAP headers
R-08 audit append-only ──► R-14 VERIFIED persisted ──► R-27 four-eyes
R-01, R-03, R-07, R-13, R-15, R-16: independent
R-20 → R-21 (explanations)
D-track (Phase 2) depends on: R-01 (risk numbers in docs), R-03 (frozen-file safety);
E-track depends on: approval to run evaluations
PR-track (Phase 4) depends on: Phase 2 and Phase 3 complete
```

## 3. Recommended implementation order (Phase 1)

| Step | Items | Notes |
|---|---|---|
| 1 | **R-01** | Risk key; most user-visible |
| 2 | R-02 | Logging; needed to observe every later fix |
| 3 | R-03 | Protects frozen artifacts |
| 4 | R-04 | |
| 5 | R-05 → R-06 | |
| 6 | R-07 | |
| 7 | R-08 → R-14 | |
| 8 | R-15, R-16 | |
| 9 | R-10 → R-11 → R-12 | |
| 10 | R-13 | |
| 11 | R-18 → R-09 → R-17 → R-19 | R-19 needs approval to change CI |
| 12 | P2 items R-20 … R-31 | Grouped review after the P0/P1 report |
| 13 | P3 | Proposal only; to be scheduled in Phase 9 planning |

Each step ends with:
* the full validation set (§7);
* a commit on the remediation branch;
* a short entry in the Phase 1 report.

**Stop after P0 + P1 for a review** before starting P2.

## 4. Files affected (Phase 1, P0–P2)

**Backend**
* `backend/main.py`
* `backend/routes/{api,v3,range}.py`
* `backend/services/{pipeline,live_stream,decision_trace}.py`
* `backend/middleware/{api_auth,rate_limit,request_limits,logging_mw,errors,metrics_mw}.py`
* `backend/observability/health_checks.py`
* `backend/recovery/startup.py`
* `backend/schemas/api.py`

**Security**
* `security/auth/{tokens,users,service}.py`
* `security/rbac.py`
* `security/response/{service,store,planner}.py`
* `security/risk/engine.py`
* `security/recommendations/engine.py`
* `security/correlation/__init__.py`

**Ingestion**
* `ingestion/{normalize,validate,adapters,queue,cicflowmeter_runner}.py`

**ML and explainability**
* `ml/prediction/predictor.py`: inference input handling only; no model or threshold change.
* `explainability/{lime_engine,shap_engine}.py`

**Research**
* `research/serving.py`: input handling and errors only; no model change.

**Database**
* `database/{db,bootstrap,url,retention}.py`
* `alembic/env.py`
* `alembic.ini`

**Frontend**
* `frontend/{nginx.conf,vite.config.ts}`
* `frontend/src/services/api.ts`
* affected pages

**Deployment and CI**
* `Dockerfile.api`
* `docker-compose.yml`
* `config.yaml`: auth and environment keys only; the ML sections are not touched.
* `requirements*.txt`
* `.github/workflows/ci.yml`

**Tests**
* new `tests/test_remediation_*.py`
* tightened `tests/test_productionization_p6_persistence.py`

**Not touched in Phase 1**
* the 16 frozen v1.1 files
* the 25 manifest-protected artifacts
* `research/{openset,protocols,conformal,data}.py`
* every result JSON

## 5. Research correction plan (separate from Phase 1 code work)

### 5.1 D-track — claim and documentation corrections (Phase 2; P0 priority; text only, no new numbers)

| D-ID | Sources | Documents | Correction |
|---|---|---|---|
| D-01 | ML-1 | `docs/PROJECT_REPORT.md:190`, `docs/research/publication/TABLES.md:39`, `docs/GENERALIZATION.md`, `docs/VIVA_QA.md`, `docs/PRESENTATION.md`, `frontend/src/pages/ModelsPage.tsx:364` | Relabel the existing figures "test @ 0.5 (argmax)". Add the 0.85 test figures **only after E-01** produces them. |
| D-02 | ML-2 | PROJECT_REPORT, README "Sample evaluation" | State that macro-F1 is conditional on a correct stage 1. Add the end-to-end per-family table once E-02 produces it. |
| D-03 | ML-3 | GENERALIZATION.md, PROJECT_REPORT, VIVA_QA, **`docs/IMPLEMENTATION_STATUS.md:13,19`** | Mark the P10/script-25 temporal holdout as **superseded (contaminated)**. Point to the research temporal protocol. |
| D-04 | ML-4 | README v3 section, `config.yaml` comment, docs | Document the `union` policy and the system-level benign incident rate (0.81 % vs 0.09 %). Decide the default policy (a user decision). |
| D-05 | ML-12 | PROJECT_REPORT, VIVA_QA, `EMPIRICAL_MITIGATION.md` | Relabel P11 as "harness validation (deterministic by construction)". Drop the measured−simulation deltas. |
| D-06 | RES-1 | `README.md:87,99`, `docs/research/AEGIS_OSR.md:75` | Use the paper's conditional FPR wording. Replace "restores" with "re-targets the threshold; realised FPR 0–10 % per day". |
| D-07 | RES-3, RES-11, decision E | `docs/research/paper.tex:45,137`, conclusion; `docs/research/paper_build/paper.py`; `research/publication.py` | Add the per-day XGB / max / Fisher table, built from all days (not only 02-14 and 02-16). Fix "retrained". Use hypothesis wording for the extractor confound. Apply the approved sentence replacement (decision E). Rebuild and validate both papers (Phase 3). |
| D-08 | RES-4, RES-16, RES-11 | `PRIOR_WORK_COMPARISON.md:231`, `RESEARCH_GAP_ANALYSIS.md` Contributions 1–2, `CLAIM_AUDIT.md` | Narrow the claims as in RES-4. Cite the classical Fisher-vs-min-p trade-off. Quote per-day ranges. |
| D-09 | ML-10, RES-12 | PROJECT_REPORT ("ports dropped") | State that Destination Port is a feature. |

**Regression tests for the D-track:** extend `tests/test_paper_claims.py` with forbidden-phrase checks over README and `docs/**`:
* "guaranteed benign false-alarm"
* "restores false-alarm control"
* "@ 0.85" next to 0.99048
* "temporally separated" without the "superseded" note

### 5.2 E-track — new versioned evaluations (Phase 2; **each needs explicit approval to run**; frozen models, no training)

| E-ID | Sources | What | Output (new files) | Size |
|---|---|---|---|---|
| E-01 | ML-1 | Score the frozen DT once on `data/processed/test.parquet` at 0.85. Report both operating points. | `research_artifacts/v11_reeval/v11_test_metrics_by_threshold.json` + manifest | S |
| E-02 | ML-2 | End-to-end per-family detection and family accuracy at 0.85 on the test split and the replay pool | same folder | S |
| E-03 | ML-4 | System-level benign incident rate per policy (frozen / gate / union) on held-out benign data | same folder | S |
| E-04 | RES-3, RES-4, RES-22 | Matched-FPR re-analysis from the **existing** per-flow dumps (no retraining): per-day XGB / max / Fisher, temporal oracle, TPR@1 % FPR | `research_artifacts/reanalysis/` | M |
| E-05 | RES-7 | Day- and family-level summaries; hierarchical bootstrap from existing records | `research_artifacts/reanalysis/` | M |

### 5.3 PR-track — R3 protocol amendments (Phase 4; nothing runs until approved; **no R3 training**)

| PR-ID | Sources | Amendment |
|---|---|---|
| PR-01 | RES-2 | Randomised (smoothed) conformal p-values as the primary rule, with the deterministic rule reported as a sensitivity check. Report recall at matched realised FPR. Rewrite H4 as a tolerance on smoothed p-values. Unit test with heavily tied scores. |
| PR-02 | RES-10 | Implement Optuna tuning with an equal trial budget per model, on training-only validation data. Freeze configs to files. `--campaign` refuses to run without frozen configs. Add the temporal protocol to the runner. |
| PR-03 | RES-18 | Equal data volume for early-stopped and reference models (or a documented asymmetry). Unified method names. Feature-only leakage hash as a report. |
| PR-04 | RES-6 | Design-free confirmation flows: a time-split half of each small family, never used before; plus cross-dataset LOAFO. |
| PR-05 | RES-7, RES-5 | Family- and day-level CIs or a hierarchical bootstrap. Calibration-conditional bounds for small windows. Multiplicity statement. |
| PR-06 | RES-8, RES-9, RES-15 | Time-separated W_r / W_c. Per-day oracle@W. Warm-up contamination sensitivity. |
| PR-07 | RES-12, RES-13, RES-14, RES-19 | No-port ablation. Tool-level known/unknown split. Timestamp-ordered 2018 cache with a monotonicity check. Label-conflict counts. |
| PR-08 | RESEARCH_ALIGNMENT_REVIEW §5 | Support and rejection criteria F1–F5 for reliability-aware fusion, fixed **before** evaluation (user decision F). |
| PR-09 | RES-17 | `assert_writable` in scripts 51, 52, 58 and 61. This is a code change, but it guards research assets, so it can be done in Phase 1 (S). |
| PR-10 | RES-20, RES-21 | State the Mondrian conditional scope. Mark α = 0.001 cells n/a when \|C2\| < 1000. |
| PR-11 | ML-11, ML-20 | For any **new** production model version, which is outside Phase 1 and needs approval: select candidates after tuning each one's threshold on validation data; use a deterministic cost proxy instead of wall-clock latency; report a day- or group-wise split next to the IID split. The frozen v1.1 model is not retrained; for it, these findings are documented as limitations (D-01, D-03). |

**Campaign deferral.** The previously approved CPU campaign and GPU budgets (TabM ≤ 42 GPU-h, CLOSR ≤ 46 GPU-h with 5 seeds) stay **deferred** until PR-01 to PR-03 are approved, as the user directed after the audit.

## 6. Modular-framework readiness (assessment only; no restructuring)

| Module | Reusable as-is | Needs an interface first |
|---|---|---|
| Detection | `research/r3_models.py` registry and `factory()` | Serving loads hard-coded v1.1 file names (`pipeline.py:41-52`). Needs a `DetectionModel` interface with capability flags (proba, native explanation). |
| Open-set | `AegisOSR(clf_factory, methods)`, `research/serving.py` | An `OpenSetDetector` interface (`fit`, `calibrate`, `score`, `p_value`). CLOSR adapter not yet written. |
| Explanation | `shap_engine` (correct for the label model) | Explicit "which model / which background" contract (R-20, R-21). |
| Adaptation | per-day recalibration code in `research/openset.py` | A runtime interface. Its design depends on Phase 6. |
| Decision / risk | `security/detection_policy.py`, `security/risk/engine.py` | Typed risk result (R-01). Policy registry. |
| Response | `security/response` adapter contract | Already interface-based. Add four-eyes (R-27). |
| Evaluation | `research/protocols.py`, `artifact_guard.py`, `scoredump.py` | Protocol registry including temporal (PR-02). |

## 7. Validation set run after every remediation item

1. `MPLBACKEND=Agg DISABLE_RATE_LIMIT=true python -m pytest tests -q`, plus the security subset **without** `DISABLE_RATE_LIMIT`.
2. `npm run typecheck`, `npm test`, `vite build` (scratch outDir).
3. Alembic `upgrade head` + `check` on a throwaway DB.
4. `verify_manifest() == {}` and `frozen_v11_diff() == []`.
5. `git diff --stat v1.1-research -- <FROZEN_V11>` is empty, and the branch is still clean of protected-artifact changes.

## 8. Risks to frozen research assets, and safeguards

| Risk | Where | Safeguard |
|---|---|---|
| A runtime GET overwrites a frozen file | ARCH-18 (`global_shap_summary.json`) | R-03 first; integrity test in every validation run |
| Re-evaluation scripts write next to frozen artifacts | E-01 to E-03 | New `research_artifacts/v11_reeval/` folder; `assert_writable`; manifest |
| Dependency changes break unpickling or reproduction | R-18 | No ML package version changes; regression gate re-run before any non-ML upgrade is accepted |
| Scripts writing protected files without the guard | RES-17 | PR-09 |
| Doc corrections rewriting history | D-track | Mark superseded; never delete old numbers; new artifacts only |
| Accidental change to `main` | all | Work only on the approved remediation branch; no push or merge without approval |

**Proposed branch:** `remediation/phase1-correctness`, created locally from `audit/full-repository-2026-11` so that the audit documents are included. Not pushed. **Needs your approval.**

## 9. Exact first implementation task (after approval)

**R-01: fix the risk-score key.**

1. In `backend/services/pipeline.py:384`, read `g_risk["risk_score"]`. At `:381`, pass the measured intensity (`intensity_report(features)["value"]`) for gate-only incidents.
2. In `backend/services/live_stream.py:278`, read `risk["risk_score"]`.
3. Add `RiskResult(TypedDict)` as the return type of `security/risk/engine.py:compute_risk`.
4. Add `tests/test_remediation_r01_risk.py`:
   * a gate-only incident (Heartbleed replay flow) persists `risk_score > 0` with severity HIGH;
   * the live tick for an attack has `risk_score > 0`;
   * a dedup update raises the stored risk.
5. Run the validation set (§7). Commit as `fix(R-01): read risk_score key; gate-only risk uses measured intensity`.

Expected size: S, about 1 hour including tests. No frozen file, model, threshold or result is touched.
