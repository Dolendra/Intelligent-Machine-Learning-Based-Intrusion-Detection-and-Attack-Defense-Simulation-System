# Aegis IDS — Intelligent Intrusion Detection Platform

**One-sentence pitch:** An intelligent ML-based intrusion detection platform that detects and classifies network attacks, explains predictions, assesses risk, recommends defenses, and interactively simulates the attack-to-defense lifecycle.

**Repository:** https://github.com/Dolendra/Intelligent-Machine-Learning-Based-Intrusion-Detection-and-Attack-Defense-Simulation-System

[![CI](https://github.com/Dolendra/Intelligent-Machine-Learning-Based-Intrusion-Detection-and-Attack-Defense-Simulation-System/actions/workflows/ci.yml/badge.svg)](https://github.com/Dolendra/Intelligent-Machine-Learning-Based-Intrusion-Detection-and-Attack-Defense-Simulation-System/actions/workflows/ci.yml)

## Dataset already in this repo

| Folder | Role |
|--------|------|
| `MachineLearningCVE/` | **Primary** — CICIDS2017 flow features for ML |
| `TrafficLabelling/` | Alternate labelled export (not required for training) |

Default training uses **full dataset** (`sample_frac: 1.0`) and drops rare classes (`min_class_count: 50`).

## Quick start (local)

```bash
python -m pip install -r requirements.txt
python scripts/01_prepare_data.py      # once (full CICIDS2017)
python scripts/02_train_models.py      # once
python scripts/05_plot_evaluation.py   # report figures → models/trained_models/figures/

# One-click (Windows): API + UI in two terminals
powershell -File scripts/start_all.ps1

# Or manually:
# Terminal A
uvicorn backend.main:app --reload --port 8000
# Terminal B
cd frontend && npm install && npm run dev
```

- UI: http://127.0.0.1:5173/  
- API docs: http://127.0.0.1:8000/docs  
- Demo script: [`docs/DEMO.md`](docs/DEMO.md)
- Optional env overrides: copy `.env.example` → `.env`

### Docker (after models are trained)

```bash
docker compose up --build
```

UI on port **5173**, API on **8000**. Requires `models/trained_models/` and `data/processed/` present on the host build context.

## Architecture

![Aegis IDS architecture](docs/architecture.svg)

```text
Network flow → preprocess → binary ML → multiclass → risk → SHAP/LIME
→ recommendation → simulation → dashboard
```

### Sample evaluation figures

<p>
<img src="models/trained_models/figures/binary_confusion_matrix.png" alt="Binary confusion matrix" width="280"/>
<img src="models/trained_models/figures/binary_roc.png" alt="Binary ROC" width="280"/>
<img src="models/trained_models/figures/feature_importance.png" alt="Feature importance" width="280"/>
</p>

Pipeline: **Network flow → preprocess → binary ML → (if attack) multiclass → risk → SHAP → recommendation → simulation → dashboard**

## Reproduce report metrics

| Artifact | Path |
|----------|------|
| Training metrics JSON | `models/trained_models/training_report.json` |
| Markdown comparison | `models/trained_models/model_comparison.md` |
| Confusion / ROC / importance | `models/trained_models/figures/` |
| Data summary | `data/processed/summary.json` |

```bash
python scripts/04_export_comparison.py
python scripts/05_plot_evaluation.py
pytest -q
```

## Docs

| Doc | Purpose |
|-----|---------|
| [`docs/00-index.md`](docs/00-index.md) | Module index |
| [`docs/DEMO.md`](docs/DEMO.md) | 2-minute viva demo |
| [`docs/TEAM.md`](docs/TEAM.md) | 3-member ownership guide |
| [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md) | Full report draft |
| [`docs/Aegis_IDS_Project_Report.docx`](docs/Aegis_IDS_Project_Report.docx) | Word export |
| [`docs/Aegis_IDS_Viva_Presentation.pptx`](docs/Aegis_IDS_Viva_Presentation.pptx) | Viva PowerPoint |
| [`docs/PRESENTATION.md`](docs/PRESENTATION.md) | Slide outline |
| [`docs/CHECKLIST.md`](docs/CHECKLIST.md) | Submission checklist |
| [`notebooks/01_data_analysis.ipynb`](notebooks/01_data_analysis.ipynb) | EDA |
| [`notebooks/03_explainability_demo.ipynb`](notebooks/03_explainability_demo.ipynb) | SHAP/LIME demo |
| [`notebooks/05_model_evaluation.ipynb`](notebooks/05_model_evaluation.ipynb) | Evaluation figures |

## Team split (suggested)

- **Member 1 — ML/Data:** dataset, features, training, evaluation  
- **Member 2 — Security intelligence:** SHAP, risk, recommendations, incidents  
- **Member 3 — App/Simulation:** FastAPI, React, topology visualization  

## Safety note

The simulation **visualizes** attack and defense. It does **not** launch real cyberattacks or auto-execute destructive network changes. Recommendations are advisory.
