# Submission checklist

## Must have for demo day
- [ ] API running (`uvicorn backend.main:app --port 8000`)
- [ ] UI running (`cd frontend && npm run dev` or `npm run preview`)
- [ ] Models present in `models/trained_models/`
- [ ] Walkthrough rehearsed from `docs/DEMO.md`
- [ ] Dashboard shows seeded incidents

## Report package
- [ ] `docs/PROJECT_REPORT.md` reviewed by all members
- [ ] `docs/Aegis_IDS_Project_Report.docx` generated (`python scripts/06_export_report_docx.py`)
- [ ] Figures attached / embedded from `models/trained_models/figures/`
- [ ] Metrics match `models/trained_models/model_comparison.md`
- [ ] Citations added in Related Work section

## Presentation
- [ ] Slides built from `docs/PRESENTATION.md`
- [ ] Each member can explain full pipeline (not only their module)

## Code hygiene
- [ ] `pytest -q` passes
- [ ] No secrets in repo (`.env` gitignored)
- [ ] README quick start works on a clean machine (or Docker)

## Optional
- [ ] GitHub: `gh auth login` then `powershell -File scripts\push_github.ps1`
- [ ] `docker compose up --build`
- [ ] Full-dataset note in report if using `sample_frac: 1.0`
