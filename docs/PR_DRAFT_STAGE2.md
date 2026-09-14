# Pull request draft: `stage2/productionization` → `main`

GitHub CLI is not authenticated in this environment. Open the PR after login:

```bash
gh auth login
gh pr create --base main --head stage2/productionization --title "Stage-2 productionization + research/submission package" --body-file docs/PR_DRAFT_STAGE2.md
```

Or use the compare link:

https://github.com/Dolendra/Intelligent-Machine-Learning-Based-Intrusion-Detection-and-Attack-Defense-Simulation-System/compare/main...stage2/productionization?expand=1

---

## Summary

- Stage-2 Phases A–F scaffolding: schema-versioned CSV/PCAP ingest, in-process detect queue, Postgres URL + opt-in auth/RBAC, API hardening + advisory response plan, in-process metrics + CI stage2-gate, cyber-range sim validation
- Research docs synced to frozen v1.1: Decision Tree @ 0.85 + Random Forest (attack-only); corrected stale XGBoost claims
- Phase-2 research write-ups: temporal holdout, IID drift, residual errors, model-selection rationale + figures
- Submission pack: DEMO.md, VIVA_QA.md, regenerated DOCX + PPTX

## Honest framing

- Auth/rate-limit remain **off by default**
- Controlled response is **advisory/simulation only** (no live mitigation)
- Metrics are in-process prototype counters (not Prometheus)
- External-dataset evaluation is **future work**
- Research baseline on `main` remains the academic freeze; this PR promotes Stage-2 + synced docs

## Test plan

- [ ] `pytest tests -q` (or at least stage2-gate tests)
- [ ] `GET /api/security/status` reports `2-phase-f`
- [ ] `GET /api/metrics` returns single-process snapshot
- [ ] `python scripts/27_cyber_range_sim_validate.py` → all_ok
- [ ] Frontend typecheck/build
- [ ] Spot-check Research page decisions (temporal / drift / selection)
- [ ] Open `docs/Aegis_IDS_Viva_Presentation.pptx` title slide and fill team/college/year
