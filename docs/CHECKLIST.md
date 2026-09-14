# Submission checklist

## Must have for demo day
- [ ] API running (`uvicorn backend.main:app --port 8000`)
- [ ] UI running (`cd frontend && npm run dev` or `npm run preview`)
- [ ] Models present in `models/trained_models/`
- [ ] Walkthrough rehearsed from `docs/DEMO.md` (viva-day 17-step playbook; ≤5 min cut if needed)
- [ ] Preflight: `/api/ready` + Detection DDoS sample + SHAP + Controlled response + Simulation recovered
- [ ] Dashboard shows incidents (seeded if `DEMO_MODE=true`)
- [ ] Fallback pack ready: PPTX + `PROJECT_REPORT.md` + P11/P12 JSON if UI fails
- [ ] Skim `docs/VIVA_QA.md` numbers card (DT @ 0.85, RF, F1/ROC)

## Report package
- [ ] `docs/PROJECT_REPORT.md` reviewed by all members (models/metrics match freeze)
- [ ] `docs/IMPLEMENTATION_STATUS.md` matches claims in slides/report
- [ ] `docs/Aegis_IDS_Project_Report.docx` generated (`python scripts/06_export_report_docx.py`)
- [ ] Figures from `models/trained_models/figures/` (incl. temporal / drift / model selection)
- [ ] Metrics match `models/trained_models/training_report.json` / `model_comparison.md`
- [ ] Temporal + drift + error sections reviewed for honest wording
- [ ] `python scripts/13_write_model_metadata.py` for reproducibility metadata (if regenerating)

## Presentation
- [ ] Slides from `docs/PRESENTATION.md` / regenerate PPTX: `python scripts/08_export_presentation_pptx.py` (**18 slides**, v2.0)
- [ ] Open `docs/Aegis_IDS_Viva_Presentation.pptx` and fill Team / College / Year on title slide
- [ ] Cross-check every number against `docs/PROJECT_REPORT.md` (research vs sim vs P11)
- [ ] Each member can explain full pipeline (not only their module)
- [ ] Safety line rehearsed: no real attacks / no auto-mitigation
- [ ] Trap questions from `docs/VIVA_QA.md` rehearsed once

## Code hygiene
- [ ] `pytest -q` passes
- [ ] No secrets in repo (`.env` gitignored)
- [ ] README quick start works on a clean machine (or Docker)

## Optional
- [ ] `python scripts/14_fit_calibrated_binary.py` then set `models.use_calibrated_binary: true`
- [ ] `python scripts/18_scenario_aware_evaluation.py` / `20_data_drift_report.py`
- [ ] `alembic upgrade head` (also runs via `init_db` when Alembic is installed)
- [ ] `docker compose up --build` then `python scripts/19_docker_compose_smoke.py`
- [ ] GitHub push via HTTPS / `scripts/push_github.ps1`
