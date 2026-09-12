# Model comparison (from training_report.json)

## Binary validation

| Model | Precision | Recall | F1 | ROC-AUC |
|-------|----------:|-------:|---:|--------:|
| logistic_regression | 0.7206 | 0.9706 | 0.8272 | 0.9860 |
| decision_tree | 0.9845 | 0.9966 | 0.9905 | 0.9989 |
| random_forest | 0.9863 | 0.9961 | 0.9912 | 0.9999 |
| xgboost | 0.9961 | 0.9899 | 0.9930 | 0.9999 |

**Best binary:** `xgboost`
**Test:** precision=0.9963, recall=0.9896, F1=0.9930, ROC-AUC=0.999938250188364

## Multiclass validation (macro / weighted F1)

| Model | macro-F1 | weighted-F1 | accuracy |
|-------|---------:|------------:|---------:|
| random_forest | 0.8063 | 0.9935 | 0.9906 |
| xgboost | 0.9194 | 0.9981 | 0.9982 |

**Best multiclass:** `xgboost`
**Test:** macro-F1=0.9175, weighted-F1=0.9981
