# Aegis IDS — Demo Script (5–10 minutes)

**Frozen baseline (v1.1):** Binary **Decision Tree** @ threshold **0.85** · Multiclass **Random Forest** (attack-only: Bot, BruteForce, DDoS, DoS, PortScan, WebAttack).

## Before you start (2 minutes setup)

```bash
# API (from repo root)
uvicorn backend.main:app --port 8000

# UI
cd frontend && npm run dev
```

- Open **http://127.0.0.1:5173/**
- Optional: `DEMO_MODE=true` seeds demo incidents (docker-compose does this by default)
- Have `docs/PRESENTATION.md` slides ready if the panel wants a short deck first

## One-sentence opener (15 s)

> We built **Aegis IDS** — an ML-based intrusion detection **prototype** that detects and classifies CICIDS2017 flows, explains predictions with SHAP, scores risk, recommends **advisory** defenses, and **simulates** the attack–defense lifecycle. We do **not** capture live packets or auto-block networks.

---

## Timed walkthrough

| Time | Page | What to do | What to say |
|------|------|------------|-------------|
| 0:00–0:45 | **Dashboard** | Show KPIs / recent incidents | “Analyst overview — incidents, risk bands. WebSocket refresh is UI telemetry, **not** live capture.” |
| 0:45–3:30 | **Detection** | Load **DDoS** sample → Detect | “Stage-1 Decision Tree: attack vs benign @ 0.85. Stage-2 Random Forest: family. Note confidence, certainty band, risk, recommendation, rules.” |
| | | Open **Why?** (SHAP) | “Feature attributions — decision support, not causality proof. LIME is secondary.” |
| | | Point to decision trace | “Traffic → ML → risk → recommendation → incident — one integrated pipeline.” |
| | | **Simulate this incident** | Hand off to Simulation with context. |
| 3:30–5:30 | **Simulation** | Play / advance to recover | “Controlled visualization: attack → detect → recommend → defend → recover. Efficacy values are **assumptions**.” |
| | | Without vs with defense | “Pedagogical comparison — **not** measured real-world mitigation.” |
| 5:30–6:30 | **Incident / Reports** | Open incident lifecycle | “Statuses and analyst notes. `defense_action` is a recorded note, not an executed control.” |
| | | Optional export PDF/CSV | “Reporting for viva evidence.” |
| 6:30–7:30 | **Models** (optional) | Show health / metrics | “Frozen artifacts: DT F1≈0.990 · RF macro-F1≈0.998 on IID test.” |
| 7:30–8:30 | **Research** (optional) | Temporal / drift notes | “Friday temporal holdout; IID PSI≈0; residual PortScan/DoS/WebAttack confusions. External dataset = future work.” |
| 8:30–9:00 | Close | Return to Dashboard | “Contribution is **integration + honest evaluation**, not a novel IDS algorithm.” |

**If short on time (≤5 min):** Dashboard → Detection (DDoS + SHAP) → Simulate → one honesty line → stop.

**If Stage-2 branch demo:** mention Detection CSV/queue ingest is productionization scaffolding; research baseline remains CICIDS CSV flows.

---

## Phrases to use / avoid

| Prefer | Avoid |
|--------|--------|
| Prototype / decision-support | “Production SOC platform” |
| Controlled simulation | “We ran real attacks” |
| Advisory recommendations | “We auto-mitigate” |
| IID / temporal benchmark results | “Guarantees live accuracy” |
| Assumed defense efficacy | “82% real mitigation proven” |

---

## Checklist before the panel

- [ ] API `/api/health` and `/api/ready` return OK  
- [ ] Detection DDoS sample classifies as attack  
- [ ] SHAP panel renders (or fallback is labeled)  
- [ ] Simulation reaches recovered  
- [ ] You can state DT @ 0.85 and RF attack-only without notes  

Full Q&A: [`VIVA_QA.md`](VIVA_QA.md) · Slides: [`PRESENTATION.md`](PRESENTATION.md) · Team roles: [`TEAM.md`](TEAM.md)
