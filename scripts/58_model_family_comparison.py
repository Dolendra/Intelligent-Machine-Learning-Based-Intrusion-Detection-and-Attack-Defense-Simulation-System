"""E1+ — Do deeper or different model families detect *unseen* attacks better?

Compares the classifier families listed in the project proposal on the same research split:
logistic regression, decision tree, random forest, XGBoost, histogram gradient boosting
(LightGBM-style; scikit-learn implementation), linear SVM, kernel SVM (Nystroem RBF features +
linear SVM), and three neural networks (MLP/ANN, 1-D CNN, LSTM) in PyTorch.

Two evaluations per model, both at a benign false-alarm budget of 1% chosen on validation benign
flows (so models are compared at the same operating point, not at their own default thresholds):

* IID          all six families seen in training; precision / recall / F1 / MCC / ROC-AUC on the test split
* Held-out     leave-one-attack-family-out (6 folds): recall on the withheld family = zero-day recall

Output: research_artifacts/model_family_comparison.json, docs/research/MODEL_FAMILIES.md
Usage:  python scripts/58_model_family_comparison.py [--seed 1] [--quick]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier  # noqa: E402
from sklearn.kernel_approximation import Nystroem  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import f1_score, matthews_corrcoef, precision_score, recall_score, roc_auc_score  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.svm import LinearSVC  # noqa: E402
from sklearn.tree import DecisionTreeClassifier  # noqa: E402
from xgboost import XGBClassifier  # noqa: E402

from research.data import cap_per_family, feature_columns, load_cic2017, stratified_split  # noqa: E402
from research.features import SignedLogScaler  # noqa: E402
from research.protocols import LOAFO_FAMILIES, RARE_NATURAL_UNKNOWN  # noqa: E402

OUT_JSON = ROOT / "research_artifacts" / "model_family_comparison.json"
OUT_MD = ROOT / "docs" / "research" / "MODEL_FAMILIES.md"
ALPHA = 0.01


# ----------------------------------------------------------------------------- torch models
def _torch_model(kind: str, d: int):
    import torch.nn as nn

    if kind == "mlp":
        return nn.Sequential(nn.Linear(d, 128), nn.ReLU(), nn.Dropout(0.1), nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1))
    if kind == "cnn":
        class CNN(nn.Module):
            def __init__(self):
                super().__init__()
                self.conv = nn.Sequential(nn.Conv1d(1, 32, 5, padding=2), nn.ReLU(), nn.MaxPool1d(2),
                                          nn.Conv1d(32, 64, 3, padding=1), nn.ReLU(), nn.AdaptiveMaxPool1d(8))
                self.head = nn.Sequential(nn.Flatten(), nn.Linear(64 * 8, 64), nn.ReLU(), nn.Linear(64, 1))

            def forward(self, x):
                return self.head(self.conv(x.unsqueeze(1)))
        return CNN()
    if kind == "lstm":
        class LSTM(nn.Module):
            def __init__(self):
                super().__init__()
                self.rnn = nn.LSTM(input_size=1, hidden_size=32, batch_first=True)
                self.head = nn.Linear(32, 1)

            def forward(self, x):
                _, (h, _) = self.rnn(x.unsqueeze(-1))
                return self.head(h[-1])
        return LSTM()
    raise ValueError(kind)


class TorchBinary:
    """Small PyTorch binary classifier with class-balanced BCE and early stopping on a 10% split."""

    def __init__(self, kind: str, epochs: int, seed: int) -> None:
        self.kind, self.epochs, self.seed = kind, epochs, seed

    def fit(self, X: np.ndarray, y: np.ndarray):
        import torch

        torch.manual_seed(self.seed)
        torch.set_num_threads(max(1, torch.get_num_threads()))
        rng = np.random.default_rng(self.seed)
        idx = rng.permutation(len(X))
        nv = max(1, len(X) // 10)
        va, tr = idx[:nv], idx[nv:]
        Xt, yt = torch.tensor(X[tr], dtype=torch.float32), torch.tensor(y[tr], dtype=torch.float32)
        Xv, yv = torch.tensor(X[va], dtype=torch.float32), torch.tensor(y[va], dtype=torch.float32)
        self.net = _torch_model(self.kind, X.shape[1])
        pos = float(yt.sum())
        pw = torch.tensor([(len(yt) - pos) / max(pos, 1.0)]) ** 0.5
        loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=pw)
        opt = torch.optim.AdamW(self.net.parameters(), lr=2e-3, weight_decay=1e-5)
        best, best_state, bad, bs = float("inf"), None, 0, 512
        for _ in range(self.epochs):
            self.net.train()
            perm = torch.randperm(len(Xt))
            for s in range(0, len(Xt), bs):
                b = perm[s:s + bs]
                opt.zero_grad()
                loss = loss_fn(self.net(Xt[b]).squeeze(-1), yt[b])
                loss.backward()
                opt.step()
            self.net.eval()
            with torch.no_grad():
                v = float(loss_fn(self.net(Xv).squeeze(-1), yv))
            if v < best - 1e-5:
                best, bad = v, 0
                best_state = {k: t.clone() for k, t in self.net.state_dict().items()}
            else:
                bad += 1
                if bad >= 2:
                    break
        if best_state is not None:
            self.net.load_state_dict(best_state)
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        import torch

        self.net.eval()
        out = []
        with torch.no_grad():
            for s in range(0, len(X), 8192):
                out.append(self.net(torch.tensor(X[s:s + 8192], dtype=torch.float32)).squeeze(-1).numpy())
        return np.concatenate(out)


# ----------------------------------------------------------------------------- model zoo
def zoo(seed: int, epochs: int) -> dict[str, dict]:
    """name -> {make: () -> model, scaled: whether it needs the signed-log scaled input}."""
    return {
        "Logistic regression": {"make": lambda: LogisticRegression(max_iter=300, class_weight="balanced"), "scaled": True},
        "Decision tree": {"make": lambda: DecisionTreeClassifier(max_depth=20, class_weight="balanced", random_state=seed), "scaled": False},
        "Random forest": {"make": lambda: RandomForestClassifier(n_estimators=150, max_depth=20, class_weight="balanced_subsample",
                                                                 n_jobs=-1, random_state=seed), "scaled": False},
        "XGBoost": {"make": lambda: XGBClassifier(n_estimators=250, max_depth=8, learning_rate=0.1, subsample=0.8,
                                                  colsample_bytree=0.8, tree_method="hist", n_jobs=-1, random_state=seed), "scaled": False},
        "Hist. gradient boosting (LightGBM-style)": {"make": lambda: HistGradientBoostingClassifier(max_iter=250, learning_rate=0.1,
                                                                                                    class_weight="balanced", random_state=seed), "scaled": False},
        "Linear SVM": {"make": lambda: LinearSVC(C=1.0, class_weight="balanced", dual=False, max_iter=3000), "scaled": True},
        "Kernel SVM (RBF, Nyström)": {"make": lambda: make_pipeline(Nystroem(gamma=0.02, n_components=400, random_state=seed),
                                                                    LinearSVC(C=1.0, class_weight="balanced", dual=False, max_iter=3000)),
                                      "scaled": True},
        "MLP / ANN (PyTorch)": {"make": lambda: TorchBinary("mlp", epochs, seed), "scaled": True},
        "1-D CNN (PyTorch)": {"make": lambda: TorchBinary("cnn", epochs, seed), "scaled": True},
        "LSTM (PyTorch)": {"make": lambda: TorchBinary("lstm", max(2, epochs // 2), seed), "scaled": True},
    }


def scores(model, X: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    if hasattr(model, "decision_function"):
        return model.decision_function(X)
    return model.score(X)


def threshold_at(benign_scores: np.ndarray, alpha: float) -> float:
    """Smallest threshold whose benign false-alarm rate on validation is ≤ alpha."""
    return float(np.quantile(benign_scores, 1 - alpha, method="higher"))


def fit_eval(name, spec, Xtr, ytr, Xva_b, Xte, yte):
    m = spec["make"]()
    t0 = time.perf_counter()
    m.fit(Xtr, ytr)
    fit_s = time.perf_counter() - t0
    thr = threshold_at(scores(m, Xva_b), ALPHA)
    t1 = time.perf_counter()
    s = scores(m, Xte)
    inf_us = 1e6 * (time.perf_counter() - t1) / max(len(Xte), 1)
    return m, thr, s, fit_s, inf_us


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    seed = args.seed
    caps_tr = {"BENIGN": 60_000 if args.quick else 150_000, "_attack": 10_000 if args.quick else 25_000}
    caps_va = {"BENIGN": 20_000, "_attack": 4_000}
    caps_te = {"BENIGN": 30_000 if args.quick else 100_000, "_attack": 5_000 if args.quick else 15_000}
    epochs = 3 if args.quick else 8

    df = load_cic2017()
    base = df[~df["family"].isin(RARE_NATURAL_UNKNOWN)]
    feats = feature_columns(base)
    tr_all, va_all, te_all = stratified_split(base, (0.6, 0.1, 0.3), seed)

    def caps(d, spec):
        return {str(f): spec["BENIGN"] if f == "BENIGN" else spec["_attack"] for f in d["family"].unique()}

    def prep(train, val, test):
        sc = SignedLogScaler().fit(train[feats].to_numpy())
        raw = {k: d[feats].to_numpy(dtype=np.float32) for k, d in (("tr", train), ("va", val), ("te", test))}
        raw = {k: np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0) for k, v in raw.items()}
        scl = {k: sc.transform(d[feats].to_numpy()) for k, d in (("tr", train), ("va", val), ("te", test))}
        return raw, scl

    models = zoo(seed, epochs)
    results: dict[str, dict] = {n: {"iid": None, "heldout": {}} for n in models}

    # ---------------------------------------------------------------- IID
    train = cap_per_family(tr_all, caps(tr_all, caps_tr), seed)
    val = cap_per_family(va_all, caps(va_all, caps_va), seed)
    test = cap_per_family(te_all, caps(te_all, caps_te), seed)
    raw, scl = prep(train, val, test)
    ytr = (train["family"] != "BENIGN").to_numpy().astype(int)
    yte = (test["family"] != "BENIGN").to_numpy().astype(int)
    vb = (val["family"] == "BENIGN").to_numpy()
    for name, spec in models.items():
        X = scl if spec["scaled"] else raw
        _, thr, s, fit_s, inf_us = fit_eval(name, spec, X["tr"], ytr, X["va"][vb], X["te"], yte)
        pred = (s > thr).astype(int)
        results[name]["iid"] = {
            "precision": float(precision_score(yte, pred, zero_division=0)), "recall": float(recall_score(yte, pred)),
            "f1": float(f1_score(yte, pred)), "mcc": float(matthews_corrcoef(yte, pred)),
            "fpr": float(pred[yte == 0].mean()), "roc_auc": float(roc_auc_score(yte, s)),
            "fit_seconds": round(fit_s, 1), "inference_us_per_flow": round(inf_us, 2),
        }
        print(f"[IID] {name:42s} F1={results[name]['iid']['f1']:.4f} recall={results[name]['iid']['recall']:.4f} "
              f"FPR={results[name]['iid']['fpr']:.4f} fit={fit_s:.0f}s", flush=True)

    # ---------------------------------------------------------------- held-out families (LOAFO)
    for held in LOAFO_FAMILIES:
        train = cap_per_family(tr_all[tr_all["family"] != held], caps(tr_all, caps_tr), seed)
        val = cap_per_family(va_all[va_all["family"] != held], caps(va_all, caps_va), seed)
        test = pd.concat([cap_per_family(te_all[te_all["family"] == "BENIGN"], caps_te["BENIGN"], seed),
                          cap_per_family(base[base["family"] == held], caps_te["_attack"], seed)], ignore_index=True)
        raw, scl = prep(train, val, test)
        ytr = (train["family"] != "BENIGN").to_numpy().astype(int)
        yte = (test["family"] != "BENIGN").to_numpy().astype(int)
        vb = (val["family"] == "BENIGN").to_numpy()
        for name, spec in models.items():
            X = scl if spec["scaled"] else raw
            _, thr, s, _, _ = fit_eval(name, spec, X["tr"], ytr, X["va"][vb], X["te"], yte)
            pred = s > thr
            results[name]["heldout"][held] = {"zero_day_recall": float(pred[yte == 1].mean()),
                                              "fpr": float(pred[yte == 0].mean()),
                                              "auroc": float(roc_auc_score(yte, s))}
        print(f"[held-out {held}] " + " | ".join(f"{n.split(' (')[0]}={results[n]['heldout'][held]['zero_day_recall']:.2f}"
                                                  for n in models), flush=True)

    for name in models:
        h = results[name]["heldout"].values()
        results[name]["heldout_mean"] = {k: float(np.mean([x[k] for x in h])) for k in ("zero_day_recall", "fpr", "auroc")}

    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "seed": seed, "alpha": ALPHA, "quick": args.quick,
           "caps": {"train": caps_tr, "val": caps_va, "test": caps_te}, "torch_epochs": epochs, "results": results,
           "notes": ["Thresholds are set on validation benign flows for a 1% false-alarm budget (same operating point for all).",
                     "Histogram gradient boosting is scikit-learn's LightGBM-style implementation (LightGBM itself not installed).",
                     "CNN/LSTM read the 77 flow features as a 1-D sequence, as is common in the IDS literature; flows have no time axis."]}
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")

    md = ["# Model families on seen vs. unseen attacks (auto-generated)", "",
          f"_Generated {out['generated_at'][:19]}Z by `scripts/58_model_family_comparison.py`; research split seed {seed}; "
          f"every model thresholded for a 1% benign false-alarm rate on validation flows._", "",
          "| Model | IID F1 | IID recall | IID FPR | IID MCC | Fit (s) | µs/flow | Held-out zero-day recall (mean of 6) | Held-out AUROC |",
          "|---|---|---|---|---|---|---|---|---|"]
    for name, r in sorted(results.items(), key=lambda kv: -kv[1]["heldout_mean"]["zero_day_recall"]):
        i, h = r["iid"], r["heldout_mean"]
        md.append(f"| {name} | {i['f1']:.4f} | {i['recall']:.4f} | {100 * i['fpr']:.2f}% | {i['mcc']:.4f} | {i['fit_seconds']} | "
                  f"{i['inference_us_per_flow']} | {h['zero_day_recall']:.3f} | {h['auroc']:.3f} |")
    md += ["", "Per withheld family (zero-day recall at 1% FPR):", "",
           "| Model | " + " | ".join(LOAFO_FAMILIES) + " |", "|---|" + "---|" * len(LOAFO_FAMILIES)]
    for name, r in results.items():
        md.append(f"| {name} | " + " | ".join(f"{r['heldout'][f]['zero_day_recall']:.3f}" for f in LOAFO_FAMILIES) + " |")
    md += ["", *[f"* {n}" for n in out["notes"]], ""]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print("wrote", OUT_JSON, OUT_MD)


if __name__ == "__main__":
    main()
