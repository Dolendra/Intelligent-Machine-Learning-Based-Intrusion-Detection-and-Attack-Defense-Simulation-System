# Team guide (3 members)

Everyone should understand the **full pipeline** for viva. Suggested ownership:

## Member 1 — ML / Data
- `MachineLearningCVE` loading & cleaning (`ml/preprocessing/`)
- Feature pipeline (`ml/features/`)
- Training & metrics (`scripts/01_*.py`, `02_*.py`, `training_report.json`)
- Notebooks `01` and `05`
- Talking point: why recall/F1 > accuracy; two-stage design

## Member 2 — Security intelligence
- SHAP / LIME (`explainability/`)
- Risk scoring & recommendations (`security/`)
- Incident storage (`database/`)
- Notebook `03`
- Talking point: explanations are decision support, not causality; recs are advisory

## Member 3 — Application / simulation
- FastAPI (`backend/`)
- React UI (`frontend/`)
- Simulation engine (`simulation/`)
- Docker / `start_all.ps1`
- Talking point: live demo of Detection + Simulation pages

## Shared demo script
Follow [`DEMO.md`](DEMO.md) together at least once before the viva.
