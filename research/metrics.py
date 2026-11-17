"""Open-set IDS metrics and statistics."""
from __future__ import annotations

import numpy as np
from scipy import stats
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score

from research.openset import BENIGN, UNKNOWN_ATTACK, ZERO_DAY


def _safe_auc(y: np.ndarray, s: np.ndarray, fn=roc_auc_score) -> float:
    return float(fn(y, s)) if 0 < y.sum() < len(y) else float("nan")


ALPHA_GRID = (0.001, 0.01, 0.05)


def detection_metrics(
    method: dict, groups: np.ndarray, alpha: float, unknown_families: np.ndarray | None = None
) -> dict:
    """``groups`` ∈ {'benign','known','unknown'} per flow; alerts are ``pvalue <= alpha``."""
    score, pval = method["score"], method["pvalue"]
    alert = pval <= alpha
    b, k, u = groups == "benign", groups == "known", groups == "unknown"
    out = {
        "fpr": float(alert[b].mean()) if b.any() else float("nan"),
        "known_recall": float(alert[k].mean()) if k.any() else float("nan"),
        "zero_day_recall": float(alert[u].mean()) if u.any() else float("nan"),
        "auroc_unknown": float("nan"),
        "auprc_unknown": float("nan"),
        "auroc_all": float("nan"),
    }
    for a in ALPHA_GRID:  # operating curve: nominal alpha vs realized FPR / recall
        al = pval <= a
        out[f"fpr@{a}"] = float(al[b].mean()) if b.any() else float("nan")
        out[f"zero_day_recall@{a}"] = float(al[u].mean()) if u.any() else float("nan")
        out[f"known_recall@{a}"] = float(al[k].mean()) if k.any() else float("nan")
    if u.any() and b.any():
        sel = b | u
        out["auroc_unknown"] = _safe_auc(u[sel].astype(int), score[sel])
        out["auprc_unknown"] = _safe_auc(u[sel].astype(int), score[sel], average_precision_score)
    if (k | u).any() and b.any():
        out["auroc_all"] = _safe_auc((~b).astype(int), score)
    if unknown_families is not None and u.any():
        out["zero_day_recall_by_family"] = {
            str(f): float(alert[u & (unknown_families == f)].mean())
            for f in np.unique(unknown_families[u])
        }
    return out


def openset_attribution(labels: np.ndarray, families: np.ndarray, groups: np.ndarray) -> dict:
    """How Aegis-OSR labels flows: known attacks attributed correctly, unknowns marked unknown."""
    labels = labels.astype(str)
    families = families.astype(str)
    is_unknown_label = np.isin(labels, [UNKNOWN_ATTACK, ZERO_DAY])
    u, k = groups == "unknown", groups == "known"
    truth = np.where(u, "UNKNOWN", families)
    pred = np.where(is_unknown_label, "UNKNOWN", labels)
    res = {
        "unknown_flagged_as_unknown": float(is_unknown_label[u].mean()) if u.any() else float("nan"),
        "unknown_misattributed_to_known": float((~is_unknown_label & (labels != BENIGN))[u].mean()) if u.any() else float("nan"),
        "unknown_missed_as_benign": float((labels == BENIGN)[u].mean()) if u.any() else float("nan"),
        "known_family_accuracy": float((labels[k] == families[k]).mean()) if k.any() else float("nan"),
        "openset_macro_f1": float(f1_score(truth, pred, average="macro", zero_division=0)),
    }
    return res


def mean_ci(values, confidence: float = 0.95) -> dict:
    v = np.asarray([x for x in values if x is not None and not np.isnan(x)], dtype=float)
    if v.size == 0:
        return {"mean": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "std": float("nan"), "n": 0}
    if v.size == 1:
        return {"mean": float(v[0]), "ci_low": float(v[0]), "ci_high": float(v[0]), "std": 0.0, "n": 1}
    sem = stats.sem(v)
    h = sem * stats.t.ppf((1 + confidence) / 2, v.size - 1) if sem > 0 else 0.0
    return {"mean": float(v.mean()), "ci_low": float(v.mean() - h), "ci_high": float(v.mean() + h),
            "std": float(v.std(ddof=1)), "n": int(v.size)}


def paired_test(a, b) -> dict:
    """Wilcoxon signed-rank (two-sided) on paired observations a vs b."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    d = a - b
    res = {"n": int(a.size), "mean_diff": float(d.mean()) if d.size else float("nan"),
           "wins": int((d > 0).sum()), "losses": int((d < 0).sum()), "ties": int((d == 0).sum())}
    if a.size >= 5 and np.any(d != 0):
        w = stats.wilcoxon(a, b, zero_method="zsplit")
        res.update({"statistic": float(w.statistic), "p_value": float(w.pvalue)})
    else:
        res.update({"statistic": float("nan"), "p_value": float("nan")})
    return res


def seed_level_test(a_by_seed, b_by_seed) -> dict:
    """Paired comparison over **independent seeds** (each value = fold-average within a seed).

    Folds inside a seed share one data split, so fold × seed pairs are not independent; this is
    the test to cite. Reports a paired t-test (primary), Wilcoxon signed-rank (n ≥ 5; its minimum
    two-sided p with n = 5 is 0.0625), and a 95% t-interval for the mean difference.
    """
    a, b = np.asarray(a_by_seed, float), np.asarray(b_by_seed, float)
    ok = ~(np.isnan(a) | np.isnan(b))
    a, b = a[ok], b[ok]
    d = a - b
    res = {"n_seeds": int(d.size), "mean_diff": float(d.mean()) if d.size else float("nan"),
           "diff_ci_low": float("nan"), "diff_ci_high": float("nan"), "positive_seeds": int((d > 0).sum()),
           "t_statistic": float("nan"), "t_p_value": float("nan"), "wilcoxon_p_value": float("nan")}
    if d.size >= 2 and np.any(d != 0):
        t = stats.ttest_rel(a, b)
        sem = stats.sem(d)
        h = sem * stats.t.ppf(0.975, d.size - 1)
        res.update({"t_statistic": float(t.statistic), "t_p_value": float(t.pvalue),
                    "diff_ci_low": float(d.mean() - h), "diff_ci_high": float(d.mean() + h)})
    if d.size >= 5 and np.any(d != 0):
        res["wilcoxon_p_value"] = float(stats.wilcoxon(a, b, zero_method="zsplit").pvalue)
    return res
