# Evaluation & research questions

## ML

Accuracy, Precision, Recall, F1, ROC-AUC, confusion matrices — see `training_report.json`.

## Explainability

Qualitative review of SHAP rankings vs domain expectations (e.g. high `Flow Packets/s` for volumetric attacks).

## Recommendations

Attack type → expected primary action table correctness.

## Simulation

State machine reaches mitigation for each scenario.

## Research questions

1. How well can ML separate malicious vs benign flows?
2. Which flow features matter most?
3. Does SHAP improve interpretability?
4. Can classifications map to actionable defenses?
5. Does simulation improve understanding of the attack–defense lifecycle?
