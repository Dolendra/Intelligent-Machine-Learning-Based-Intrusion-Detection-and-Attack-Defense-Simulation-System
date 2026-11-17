# Requirements audit — pre-implementation report & proposal vs. what is built

Audited 2026-11-10 against the *Pre-Implementation Research & System Design Report* (architecture locked 20 Aug 2026) and the *Major Project Proposal Report*. Status: ✅ done · 🟡 partial / substituted (reason given) · ❌ not done.

Verification for this audit: 256 backend tests and 49 interface tests pass, the production build succeeds, and every page was opened in a real browser (Edge, via Playwright) with no console errors.

## A. Pre-implementation report

### Locked architecture decisions
| Decision | Status | Where / note |
|---|---|---|
| Cyber range + explainable IDS + response experimentation | ✅ | `cyberrange/`, Cyber Range page, `scripts/56_cyber_range_experiments.py` |
| Simulation is the central laboratory, not an animation | ✅ | Trace-driven range: recorded flows, real detectors, measured outcomes. The old animation is relabelled "Attack Storyboard (illustrative)". |
| Benchmark CIC-IDS2017 | ✅ | plus CSE-CIC-IDS2018 for transfer |
| Python + FastAPI | ✅ | `backend/` |
| PostgreSQL | 🟡 | SQLAlchemy + Alembic; SQLite by default, PostgreSQL via `IDS_DB_URL`. Range runs are stored as JSON records (`results/cyber_range/runs/`), not tables. |
| Redis Pub/Sub / Streams | 🟡 | In-process event hub + WebSockets. Range events use the locked envelope (event_id, run_id, event_type, timestamp, sequence, schema_version, payload). Redis is not needed for a single-host lab. |
| Mininet on Linux | 🟡 | Development host is Windows, so the range replays recorded flows instead of emulating packets. A Mininet back end is listed as future work. |
| Scapy / tcpdump / tshark | 🟡 | PCAP → flow ingestion via optional `cicflowmeter` (fails closed). No packet generation. |
| LR / DT / RF / XGBoost | ✅ | v1.1 selection; extended comparison in `scripts/58_model_family_comparison.py` |
| SHAP + LIME | ✅ | Detection page, Cyber Range "Why the incident was raised", E9 stability study |
| Next.js + React + TypeScript | 🟡 | React + TypeScript on Vite (same component model, no Next.js server) |
| React Flow / Cytoscape | ✅ | React Flow (`@xyflow/react`) |
| Apache ECharts | 🟡 | Recharts |
| Motion / Framer Motion | 🟡 | CSS transitions; all animation is driven by backend state |
| WebSockets | ✅ | `/api/ws/events`, `/api/ws/live` |
| LLM assistant (later stage) | ❌ | Deferred by design (Phase 13) |
| Local isolated lab first | ✅ | No network I/O in the range; LIVE response mode forbidden |

### Mandatory objectives
| # | Objective | Status |
|---|---|---|
| 1 | Rigorous data pipeline | ✅ cleaning, de-duplication, leakage-safe splits, versioned features |
| 2 | Train and compare multiple models | ✅ 4 (v1.1) + 10 families (script 58) |
| 3 | Global and local XAI | ✅ |
| 4 | False-positive reduction, not accuracy alone | ✅ threshold study, calibration study, conformal α control, range alert-threshold study (E3) |
| 5 | Controlled, reproducible simulation | ✅ seeded; identical seed ⇒ identical metrics (tested) |
| 6 | Simulation telemetry through the same feature pipeline | ✅ range flows use the 78-feature schema and the same frozen models and gate |
| 7 | Automated stateful attack scenarios | ✅ 9 scenarios, locked state machine |
| 8 | Controlled response recommendations and simulated actions | ✅ block / rate-limit / isolate / monitor / increase inspection |
| 9 | Measure detection, mitigation, recovery, attack success, service impact, latency | ✅ all measured per run |
| 10 | Reproducible experiments for a paper | ✅ per-run JSON, seeds, scripts, paper build in `docs/research/paper_build/` |

### Research questions
| RQ | Status | Evidence |
|---|---|---|
| RQ1 Explainable ML detection in a dynamic environment | ✅ | Range: detection latency, recall, FPR per scenario and detector |
| RQ2 Best model across benchmark and simulation | ✅ | Model-family comparison; detector comparison in the range |
| RQ3 Which features drive predictions | ✅ | Global SHAP, per-family drivers, E9 |
| RQ4 Reduce false positives without unacceptable recall loss | ✅ | Conformal α; range k-threshold: k = 3 removes false incidents at ≤ 2.4 s extra latency |
| RQ5 Generalisation to unseen scenarios | ✅ | LOAFO, temporal, CSE-CIC-IDS2018 (reported as a failure), range zero-day scenario |
| RQ6 Which response reduces impact most | ✅ | E8 defense comparison |
| RQ7 Do explanations improve analyst understanding | 🟡 | Explanation consistency/stability measured; a human study is future work |

### Experiment programme (§18)
| Exp | Status | Artefact |
|---|---|---|
| E1 model comparison | ✅ | `training_report.json`, `MODEL_FAMILIES.md` |
| E2 feature selection | 🟡 | Dual SelectKBest in use; script 10 exists, its report is not regenerated |
| E3 threshold optimisation | ✅ | `threshold_operating_point.json`, range threshold suite |
| E4 imbalance | 🟡 | √-balanced and balanced class weights; no resampling ablation |
| E5 generalisation | ✅ | temporal + cross-dataset + LOAFO |
| E6 attack intensity | ✅ | range `intensity` suite |
| E7 multi-attacker | ✅ | range `attackers` suite |
| E8 defense comparison | ✅ | range `defense` suite |
| E9 XAI stability | ✅ | `XAI_STABILITY.md` |
| E10 real-time performance | ✅ | P8 envelope; range wall time |

### Acceptance tests (§21.1)
| Test | Status |
|---|---|
| Each scenario creates exactly one tracked run | ✅ |
| Stop/reset leaves a known state | ✅ (new run; old run kept) |
| Every prediction references a model version and run ID | 🟡 API predictions carry the model version; range flow verdicts carry the run ID |
| Every explanation references the exact prediction | ✅ |
| Every response references a detection and has an outcome | ✅ |
| Frontend reconstructs state after reconnect | ✅ `GET /api/range/runs/{id}` |
| No scenario can target an external interface | ✅ the range performs no network I/O |
| Results reproducible from stored configuration | ✅ `tests/test_cyber_range.py` |

## B. Proposal report

| Item | Status | Note |
|---|---|---|
| CIC-IDS2017 | ✅ | |
| CSE-CIC-IDS2018 | ✅ | frozen-model transfer + open-set transfer, 5 seeds |
| NSL-KDD, UNSW-NB15, TON_IoT | ❌ | not available on this machine — future work |
| Cleaning, missing values, duplicates, normalisation, label encoding, class balancing | ✅ | |
| Correlation analysis, feature selection, statistics | ✅ | dimensionality reduction (PCA) ❌ |
| RF, XGBoost, DT, LR | ✅ | |
| LightGBM | 🟡 | scikit-learn histogram gradient boosting (LightGBM-style); LightGBM itself not installed |
| SVM | ✅ | linear and RBF (Nyström) |
| ANN, CNN, LSTM | ✅ | PyTorch, in the model-family comparison |
| SHAP, LIME, feature importance, local & global | ✅ | |
| Cyber threat intelligence | ✅ | MITRE ATT&CK tactic/technique on every detection; kill-chain summary per campaign; campaign correlation by source |
| Detect known **and unknown** attacks | ✅ | Aegis-OSR Zero-Day Gate — the main research contribution |
| Reduce false positives | ✅ | |
| Metrics incl. detection rate, FPR, MCC, ROC-AUC | ✅ | |
| Attack categories DDoS, DoS, brute force, botnet, port scan, infiltration, web (SQLi, XSS) | ✅ | Malware and IoT-specific attacks ❌ (no such data) |
| Dashboard | ✅ | React SOC console (instead of Streamlit) |

## C. Bugs found and fixed in this audit

| Bug | Fix |
|---|---|
| "Save investigation" always failed (it asked to move an incident to the status it already had) | Notes-only updates are now allowed in every state and recorded in the audit trail |
| Real-time "incident created" push was never sent (no event loop in worker threads) | Broadcast scheduled onto the WebSocket loop |
| Every detection without a source opened its own one-incident "campaign" | Campaigns only when a source is given; new *Source host* field on Detection |
| "Load sample" always returned the same flow | Random sample each time |
| Reports showed only the newest 50 incidents while tiles counted all | Loads up to 1,000 and says so |
| Live Monitor stuck on "Connecting…" when the replay pool is missing | Shows "Unavailable" |
| Job progress bar was a fixed fake 60% and gave up silently after 9 s | Indeterminate bar; 60 s with a message |
| "Frozen missed" badge and tile used different definitions | Aligned |
| Misleading text: Research Lab "updates automatically", "both keep false alarms near X%", Dashboard gate tile, System eyebrow, response stepper jumping to "Dry run", "Approve" hiding that it also executes | Corrected |
| Simulator was animation-only (the report's first listed risk) | Replaced by the trace-driven cyber range; animation relabelled |
| Missing favicon (the only console error on all pages) | Added |
