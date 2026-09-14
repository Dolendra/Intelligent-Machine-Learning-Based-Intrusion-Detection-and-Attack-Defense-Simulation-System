# Aegis IDS — Viva-Day Demo Playbook

**Purpose:** Follow this document step-by-step on viva day. Do not invent clicks or numbers.

**Authoritative metrics:** [`PROJECT_REPORT.md`](PROJECT_REPORT.md)  
**Slides:** [`PRESENTATION.md`](PRESENTATION.md) / `Aegis_IDS_Viva_Presentation.pptx`  
**Q&A:** [`VIVA_QA.md`](VIVA_QA.md)

**Frozen baseline (v1.1-research):** Binary **Decision Tree @ 0.85** · Multiclass **Random Forest** (attack-only: Bot, BruteForce, DDoS, DoS, PortScan, WebAttack)  
**Product tag:** `v2.0-aegis-productionized`

---

## Numbers you may say (memorize)

| Class | What to say | Do **not** say |
|-------|-------------|----------------|
| Research (IID) | Binary F1 **0.99048** · Multiclass macro-F1 **0.99813** | “Live network accuracy” |
| Simulation assumptions | DDoS prior **0.82** · DoS prior **0.78** (`config.yaml`) | “We measured 82% real mitigation” |
| Controlled-lab (P11) | DDoS `BLOCK_SOURCE` **1.00** · DoS `RATE_LIMIT` **0.80** | “Same as simulation priors” |
| Security (P12) | Overall **PASS** | “Enterprise SOC certified” |

**One honesty line (use once):**  
> Research F1, simulation priors, and P11 lab measurements are three different measurement classes.

---

## 1. Pre-demo setup

### Environment requirements

| Item | Requirement |
|------|-------------|
| OS | Windows / Linux / macOS |
| Python | 3.10+ with project deps installed (`requirements.txt` / venv) |
| Node | 18+ (`frontend/package.json`) |
| Models | `models/trained_models/` present (frozen artifacts — **do not retrain**) |
| Demo flows | Bundled at `models/trained_models/demo_flows.json` (no raw CICIDS2017 needed) |
| Auth | Leave **off** for viva (`AEGIS_AUTH_ENABLED` unset / false) |
| Ports | API **8000**, UI **5173** free |

**Do not** depend on `MachineLearningCVE/` or raw CICIDS CSVs for the live demo. Sample flows come from the API → bundled `demo_flows.json` (or processed test split if present).

### Startup commands (from repo root)

**Terminal A — API**

```bash
uvicorn backend.main:app --port 8000
```

Optional seed of demo incidents:

```bash
# PowerShell
$env:DEMO_MODE="true"; uvicorn backend.main:app --port 8000
```

```bash
# bash
DEMO_MODE=true uvicorn backend.main:app --port 8000
```

**Terminal B — Frontend**

```bash
cd frontend
npm run dev
```

**Windows one-shot (if available):** `powershell -File scripts/start_all.ps1`

**Docker alternative:** `docker compose up --build` (sets `DEMO_MODE=true`; still needs `models/trained_models/`).

### Health / readiness checks (before the panel enters)

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/ready
```

| Check | Expect |
|-------|--------|
| `/api/health` | `"status": "ok"` (may also show `models_loaded`) |
| `/api/ready` | `"ready": true`, `"status": "ready"`, `dependencies.models.status` ≈ `"ok"` |

If ready is **503 / NOT_READY**: stop and fix models path / restart API. Do not start the UI demo until ready is green.

### Browser URL

- UI: **http://127.0.0.1:5173/**
- API docs (backup): http://127.0.0.1:8000/docs
- Sidebar should show **Auth off (demo)** when auth is disabled

### 3-minute preflight checklist

- [ ] `/api/ready` → ready  
- [ ] Open Detection → **DDoS** → **Load sample flow** → **Detect & classify** → Attack / DDoS  
- [ ] **Why?** → SHAP tab has bars (or labeled fallback)  
- [ ] Click incident link → **Controlled response** section visible  
- [ ] Simulation **Run simulation** → **Play** reaches recovered  
- [ ] PPTX + this file open on a second screen / printed  

---

## 2. Demo data (exact)

| What | Where | How used |
|------|-------|----------|
| Primary live samples | `models/trained_models/demo_flows.json` | Via UI: **Demo flow type** → **Load sample flow** → `GET /api/demo/flow?attack_type=…` |
| Batch samples | Same bundle | **Batch sample (12)** → `GET /api/demo/flows?n=12&…` |
| Optional CI CSV | `tests/fixtures/pcap/golden_flows.csv` | Only if you must show CSV upload — **not** required for the 17-step path |
| Raw CICIDS2017 | Not in Git | **Do not** open or upload on viva day |

**Primary walkthrough attack:** **DDoS** (clearest BLOCK_SOURCE story for P11).

**Expected after Detect & classify (DDoS sample):**

| Field | Expect |
|-------|--------|
| Binary verdict | Attack (malicious) |
| Family | **DDoS** |
| Ground truth chip | `Ground truth: DDoS` (when loaded from demo API) |
| Confidence | High (typically near 1.0 on bundled vectors) |
| Risk / severity | Elevated / high band |
| Recommendation | Advisory defense aligned with DDoS (e.g. block / rate-limit style wording) |
| Incident | Auto-logged → link like `INC-…` |

If the sample is misclassified: switch to another type (DoS / PortScan), or fall back to §7 without debugging models live.

---

## 3. Safety explanation (say once, early)

> Response actions run on a **CONTROLLED test adapter** — **DRY_RUN** and lab plane only. There is **no live firewall or EDR**. Every execute path goes through **propose → dry-run → human Approve**. Approve triggers controlled execution plus **verification**; **Rollback** is available. Simulation efficacy numbers are **assumptions**, separate from P11 lab measurements.

---

## 4. Seventeen-step demonstration flow

**Suggested timing:** ~8–10 minutes full path · **≤5 min cut:** Steps 1–9 + 16 + one honesty line.

Use attack type **DDoS** unless noted.

---

### Step 1 — Dashboard

| | |
|--|--|
| **Go to** | Sidebar → **Dashboard** (`/`) |
| **Click / type** | Nothing required. Optionally point at KPI cards / recent incidents. |
| **Examiner should see** | “Security Overview”; incident/risk summary. With `DEMO_MODE=true`, seeded incidents may appear. |
| **Say** | “Analyst overview. WebSocket refresh is UI telemetry — **not** live packet capture.” |
| **Expected** | Page loads without API errors. |
| **If it fails** | Hard-refresh. If blank, verify API ready. Else open Detection and skip KPIs. |

---

### Step 2 — Detection

| | |
|--|--|
| **Go to** | Sidebar → **Detection** (`/detection`) |
| **Click / type** | Land on **Detection Lab**. |
| **Examiner should see** | Controls: Demo flow type, Load sample flow, Detect & classify, Batch sample (12). |
| **Say** | “Two-stage lab: binary Decision Tree, then attack-family Random Forest, then risk and recommendation.” |
| **Expected** | Page header “Detection Lab”. |
| **If it fails** | Use `/docs` Swagger `POST /api/predict` as backup; or §7 slides. |

---

### Step 3 — Load traffic

| | |
|--|--|
| **Click / type** | **Demo flow type** = `DDoS` → **Load sample flow** |
| **Examiner should see** | Feature vector loaded; **Ground truth: DDoS** (or equivalent label). Busy text may show “Loading…”. |
| **Say** | “Bundled CICIDS-style flow vector from `demo_flows.json` — we are **not** reading raw CICIDS CSVs in this demo.” |
| **Expected** | Features appear; Detect button enables. |
| **If it fails** | Retry once. Try `DoS`. Confirm `/api/demo/flow?attack_type=DDoS` in browser. Else §7. |

---

### Step 4 — Binary detection

| | |
|--|--|
| **Click / type** | **Detect & classify** |
| **Examiner should see** | Verdict **Attack** (or malicious); confidence; pipeline progressing. |
| **Say** | “Stage-1 frozen Decision Tree, threshold **0.85**, separates attack vs benign. Research IID binary F1 is **0.99048**.” |
| **Expected** | Malicious / attack verdict for DDoS sample. |
| **If it fails** | Note error banner. Try Batch sample (12). Do not retrain. Fall back to Models page metrics or §7. |

---

### Step 5 — Attack classification

| | |
|--|--|
| **Click / type** | Same result panel — point at family label |
| **Examiner should see** | Family **DDoS** (attack-only multiclass). |
| **Say** | “Stage-2 Random Forest on attack-only six families. Multiclass macro-F1 **0.99813** on the frozen IID test.” |
| **Expected** | Family matches ground truth for demo vector. |
| **If it fails** | Say residual confusions exist (PortScan/DoS/WebAttack); show Research page or confusion figure under `models/trained_models/figures/`. |

---

### Step 6 — Confidence

| | |
|--|--|
| **Click / type** | Point at Confidence / certainty band on the result card |
| **Examiner should see** | Numeric confidence and risk/severity chips. |
| **Say** | “Confidence supports triage; we still require human judgment before any response.” |
| **Expected** | High confidence on bundled DDoS. |
| **If it fails** | Continue to SHAP; confidence is secondary. |

---

### Step 7 — SHAP explanation

| | |
|--|--|
| **Click / type** | Open **Why?** panel → tab **SHAP** (LIME is secondary) |
| **Examiner should see** | Feature attributions (bars/list). Optional: **What-if counterfactual**. |
| **Say** | “SHAP attributions for decision support — **not** causal proof. LIME is secondary.” |
| **Expected** | SHAP content or an explicit fallback label. |
| **If it fails** | Switch to LIME tab. If both empty, say XAI may degrade under load and show a figure from `models/trained_models/figures/` or the report. |

---

### Step 8 — Risk assessment

| | |
|--|--|
| **Click / type** | Point at Risk / Severity; optionally **Why this risk?** |
| **Examiner should see** | Risk band and short explainer. |
| **Say** | “Risk blends attack family, confidence, and policy — it drives the advisory recommendation.” |
| **Expected** | Elevated risk for DDoS attack. |
| **If it fails** | Continue; recommendation may still render. |

---

### Step 9 — Recommendation

| | |
|--|--|
| **Click / type** | Point at **Recommended defense** / action list |
| **Examiner should see** | Advisory actions + disclaimer that this is not live enforcement. |
| **Say** | “Advisory only until an analyst opens the controlled response gate.” |
| **Expected** | DDoS-aligned recommendation text. |
| **If it fails** | State the mapping verbally (DDoS → block/rate-limit style) and continue to incident. |

---

### Step 10 — Create incident

| | |
|--|--|
| **Click / type** | Click the auto-logged incident link (`Logged as INC-…`). There is **no** separate “Create incident” button — attack predicts auto-create. |
| **Examiner should see** | Incident detail page (`/incidents/:id`) with timeline / status. |
| **Say** | “Detection creates a durable incident record for audit and response.” |
| **Expected** | Incident page loads with attack metadata. |
| **If it fails** | Sidebar → **Reports** → open any incident (seeded if `DEMO_MODE=true`). |

---

### Step 11 — Propose response

| | |
|--|--|
| **Click / type** | Section **Controlled response (P3)** → **Propose response** |
| **Examiner should see** | New pending action; note “Adapters: DRY_RUN / CONTROLLED test plane — no live firewall/EDR.” |
| **Say** | “Propose opens the gate — nothing executes yet.” |
| **Expected** | Action appears with pending state. |
| **If it fails** | Refresh incident. Confirm auth is off. Use Swagger propose endpoint only if comfortable; else explain the gate verbally and skip to Simulation. |

---

### Step 12 — Dry run

| | |
|--|--|
| **Click / type** | **Dry run** |
| **Examiner should see** | Dry-run result / status update on the action (preview, not enforce). |
| **Say** | “Dry run validates the planned action safely before approval.” |
| **Expected** | Dry-run succeeds or shows structured preview. |
| **If it fails** | Say dry-run is the safe preview; proceed to Approve only if UI allows, otherwise explain and go to Simulation. |

---

### Step 13 — Approval

| | |
|--|--|
| **Click / type** | **Approve** (human gate) |
| **Examiner should see** | Status moves past pending; audit events update. |
| **Say** | “Human approval is mandatory. With auth enabled this is RBAC-enforced; today auth is off for the open demo.” |
| **Expected** | Approve succeeds. |
| **If it fails** | Do **not** force. Explain Reject path exists. Continue to Simulation / Reports. |

---

### Step 14 — Controlled execution

| | |
|--|--|
| **Click / type** | Usually **none** — Approve triggers controlled execute on the test adapter. Point at audit / action status. |
| **Examiner should see** | Executed / applied-style status on CONTROLLED adapter (not a real firewall). |
| **Say** | “Execution is on the **CONTROLLED** lab adapter only — hard boundary against live network enforcement.” |
| **Expected** | Action shows executed / verified-related audit entries. |
| **If it fails** | Point at code/docs boundary: `docs/SECURITY_MODEL.md` / P12 PASS. Do not attempt live controls. |

---

### Step 15 — Verification

| | |
|--|--|
| **Click / type** | Point at verification / timeline events after Approve. Optional: **Rollback** to show fail-safe. |
| **Examiner should see** | Verified (or equivalent) audit evidence; Rollback available when permitted. |
| **Say** | “Verify confirms lab-plane effect; Rollback is the fail-safe. P11 measured DDoS block effectiveness **1.00** and DoS rate-limit **0.80** on this controlled plane — **not** the simulation priors **0.82 / 0.78**.” |
| **Expected** | Verification evidence visible, or you can state P11 numbers from the report. |
| **If it fails** | Open `models/trained_models/empirical_mitigation_report.json` or `docs/EMPIRICAL_MITIGATION.md`. |

---

### Step 16 — Simulation / recovery

| | |
|--|--|
| **Go to** | From Detection/Incident: **Simulate this incident**, **or** Sidebar → **Simulation** |
| **Click / type** | Attack **DDoS** → **Run simulation** → **Play** (or **Step**). Optionally **Apply defense**. Wait until **Recovered**. |
| **Examiner should see** | Lifecycle: attack → detect → recommend → defend → recover. Efficacy labels from config. |
| **Say** | “Pedagogical visualization. Defense efficacy here is an **assumption** — DDoS **0.82**, DoS **0.78** — separate from P11 lab measurements.” |
| **Expected** | Status reaches Recovered. |
| **If it fails** | Use **Step** slowly. If create fails, narrate phases from empty-state list and show PPT architecture slide. |

---

### Step 17 — Reports / evidence

| | |
|--|--|
| **Go to** | Sidebar → **Reports** (`/reports`) |
| **Click / type** | Open an incident if needed. Optional: **Export CSV** / **Export JSON** / **Export PDF**. Optional Lab: **Models** / **Research** / **System**. |
| **Examiner should see** | Incident list/analytics; export downloads; optional frozen metrics on Models. |
| **Say** | “Reporting and audit for viva evidence. P12 final security validation: overall **PASS**. Contribution is integration + honest evaluation — not a novel IDS algorithm.” |
| **Expected** | Exports download or Models shows health/metrics. |
| **If it fails** | Show on-disk evidence (§7). Close with the 30-second explanation. |

---

## 5. Timed shortcuts

| Length | Path |
|--------|------|
| **≤5 min** | 1 → 2–9 (DDoS + SHAP + risk + rec) → 16 → honesty line → stop |
| **~8–10 min** | Full 1–17 |
| **Extra if asked** | Models (frozen DT/RF) · Research (temporal/PSI) · System (`/api/ready`) · Campaigns |

---

## 6. Phrases to use / avoid

| Prefer | Avoid |
|--------|--------|
| Prototype / decision-support | “Production SOC platform” |
| Controlled / lab adapter | “We blocked the campus firewall” |
| Advisory recommendations | “We auto-mitigate in production” |
| IID / temporal research results | “Guarantees live accuracy” |
| Simulation assumptions 0.82 / 0.78 | “82% real-world mitigation proven” |
| P11 measured 1.00 / 0.80 | “Same number as simulation” |
| P12 security validation PASS | “Certified secure for enterprise” |

---

## 7. Fallback demo (API / UI / model failure)

**Do not** retrain, edit thresholds, or debug adapters in front of examiners.

### Fallback A — Architecture + evidence (no UI)

1. Open `docs/Aegis_IDS_Viva_Presentation.pptx` (18 slides).  
2. Walk: Architecture → ML results → XAI/Risk → Simulation → Controlled response → P11 → P12 → Limitations.  
3. Quote the numbers table at the top of this file.

### Fallback B — Artifacts on disk

| Show | Path |
|------|------|
| Report | `docs/PROJECT_REPORT.md` |
| Model freeze | `models/trained_models/model_metadata.json` |
| Demo vectors | `models/trained_models/demo_flows.json` |
| Figures | `models/trained_models/figures/` |
| P11 empirical | `models/trained_models/empirical_mitigation_report.json` or `docs/EMPIRICAL_MITIGATION.md` |
| P12 validation | `reports/final_security_validation_report.json` or `docs/FINAL_SECURITY_VALIDATION.md` |
| Readiness doc | `docs/POST_MERGE_VERIFICATION.md` |

### Fallback C — API only (UI down)

1. Open http://127.0.0.1:8000/docs  
2. `GET /api/ready` → ready  
3. `GET /api/demo/flow?attack_type=DDoS` → features  
4. Predict endpoint with those features → show attack/DDoS  
5. Narrate incident → propose → dry-run → approve → verify from memory / report

### Fallback closer

> Even without the live UI, the repository contains frozen models, bundled demo flows, empirical P11 results, and a P12 PASS security validation report that define what the system does and what it deliberately does not do.

---

## 8. Final 30-second explanation

When the examiner says: *“Okay, explain what your system actually does.”*

> **Aegis IDS** takes CICIDS-style network **flows**, runs a frozen **Decision Tree** (attack vs benign @ 0.85) and **Random Forest** (attack family), explains the decision with **SHAP**, scores **risk**, and emits an **advisory** defense. Analysts can open a **controlled** response path—propose, dry-run, approve, verify, rollback—on a **lab adapter**, never a live firewall. We also **simulate** the attack–defense lifecycle with labelled assumption priors, and we separately measured mitigation in P11 (**DDoS 1.00**, **DoS 0.80**) and validated security boundaries in P12 (**PASS**). It is a **productionized prototype** for decision support—not an enterprise auto-blocking SOC.

---

## 9. Closing lines (pick one)

- “Contribution is **end-to-end integration + honest measurement classes**, not a novel classifier.”  
- “Research F1 **0.99048** / macro-F1 **0.99813**, simulation priors **0.82 / 0.78**, P11 **1.00 / 0.80**, P12 **PASS** — keep them separate.”  

Full Q&A: [`VIVA_QA.md`](VIVA_QA.md) · Slides: [`PRESENTATION.md`](PRESENTATION.md) · Team: [`TEAM.md`](TEAM.md)
