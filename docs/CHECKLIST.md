# Submission checklist

## Must have for demo day
- [ ] API running (`uvicorn backend.main:app --port 8000`)
- [ ] UI running (`cd frontend && npm run dev` or `npm run preview`)
- [ ] Models present in `models/trained_models/`
- [ ] Walkthrough rehearsed from `docs/DEMO.md` (Detect → Simulate this incident → Play)
- [ ] Dashboard shows incidents (seeded if `DEMO_MODE=true`)

## Report package
- [ ] `docs/PROJECT_REPORT.md` reviewed by all members
- [ ] `docs/IMPLEMENTATION_STATUS.md` matches claims in slides/report
- [ ] `docs/Aegis_IDS_Project_Report.docx` generated (`python scripts/06_export_report_docx.py`)
- [ ] Figures from `models/trained_models/figures/`
- [ ] Metrics match `models/trained_models/training_report.json` / `model_comparison.md`
- [ ] Optional research: `python scripts/11_calibration_hpo_experiment.py` + notebook 07
- [ ] `python scripts/13_write_model_metadata.py` for reproducibility metadata

## Presentation
- [ ] Slides from `docs/PRESENTATION.md` / PowerPoint
- [ ] Each member can explain full pipeline (not only their module)
- [ ] Safety line rehearsed: no real attacks / no auto-mitigation

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
