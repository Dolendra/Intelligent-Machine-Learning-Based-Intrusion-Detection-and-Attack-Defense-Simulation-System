# Risk & recommendations

## Risk engine (`security/risk/engine.py`)

Frozen blend weights from `config.yaml` → `risk.weights` (project convention):

```text
score ≈ 0.50·attack_base
      + 0.25·confidence·100
      + 0.15·intensity·100
      + 0.10·asset_criticality·(scaled)
```

| Weight | Component |
|-------:|-----------|
| 50% | Attack-family base severity |
| 25% | Model confidence |
| 15% | Traffic intensity |
| 10% | Asset criticality |

Severity bands (configurable in `config.yaml`):

| Score | Severity |
|------:|----------|
| 0–30 | LOW |
| 31–60 | MEDIUM |
| 61–80 | HIGH |
| 81–100 | CRITICAL |

These bands are **project conventions**, not universal standards.

## Recommendation engine (`security/recommendations/engine.py`)

Maps attack families → advisory defensive actions (rate limiting, WAF, isolation, …).

**Important:** recommendations are **not** auto-executed against real networks.
