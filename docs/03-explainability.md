# Explainability (SHAP + LIME)

**Primary:** `explainability/shap_engine.py` (SHAP)  
**Secondary:** `explainability/lime_engine.py` (LIME)

## Behavior

1. Run prediction
2. **SHAP:** TreeExplainer when possible; otherwise KernelExplainer / importance fallback
3. **LIME:** local tabular surrogate around the instance (falls back to importances if LIME unavailable)
4. Return top-K feature contributions + narrative

## API

```http
POST /api/explain
{ "features": {...}, "top_k": 10, "method": "shap" | "lime" }
```

## Academic framing (RQ3)

> Can explainable AI improve the interpretability of IDS predictions?

SHAP is the primary decision-support layer; LIME provides a complementary local view. Neither is treated as causal proof.
