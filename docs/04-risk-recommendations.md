# Risk & recommendations

## Risk engine (`security/risk/engine.py`)

```text
score ≈ 0.55·attack_base + 0.30·confidence·100 + 0.15·intensity·100
```

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
