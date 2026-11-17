"""Unsupervised novelty detectors trained on benign traffic only.

Every detector exposes ``fit(X_benign)`` and ``score(X)`` where a *higher* score means
"less like the benign training traffic". Inputs are already scaled (``SignedLogScaler``).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import IsolationForest


# --------------------------------------------------------------------------- autoencoder
@dataclass
class NumpyAutoencoder:
    """Torch-free inference for a trained MLP autoencoder (exported weights)."""

    weights: list[np.ndarray] = field(default_factory=list)
    biases: list[np.ndarray] = field(default_factory=list)
    feature_weights: np.ndarray | None = None  # per-feature error weights (1/var on benign val)

    def reconstruct(self, X: np.ndarray) -> np.ndarray:
        h = np.asarray(X, dtype=np.float32)
        last = len(self.weights) - 1
        for i, (W, b) in enumerate(zip(self.weights, self.biases)):
            h = h @ W + b
            if i != last:
                h = np.where(h > 0, h, 0.01 * h)  # LeakyReLU, matches training
        return h

    def feature_errors(self, X: np.ndarray, batch: int = 200_000) -> np.ndarray:
        out = np.empty_like(np.asarray(X, dtype=np.float32))
        for s in range(0, len(X), batch):
            xb = np.asarray(X[s:s + batch], dtype=np.float32)
            out[s:s + batch] = (xb - self.reconstruct(xb)) ** 2
        return out

    def score(self, X: np.ndarray) -> np.ndarray:
        err = self.feature_errors(X)
        if self.feature_weights is not None:
            err = err * self.feature_weights
        return err.mean(axis=1)

    def to_dict(self) -> dict:
        return {
            "weights": [w.tolist() for w in self.weights],
            "biases": [b.tolist() for b in self.biases],
            "feature_weights": None if self.feature_weights is None else self.feature_weights.tolist(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NumpyAutoencoder":
        fw = d.get("feature_weights")
        return cls(
            weights=[np.asarray(w, dtype=np.float32) for w in d["weights"]],
            biases=[np.asarray(b, dtype=np.float32) for b in d["biases"]],
            feature_weights=None if fw is None else np.asarray(fw, dtype=np.float32),
        )


class AutoencoderDetector:
    """Under-complete MLP autoencoder; novelty = weighted reconstruction error."""

    name = "autoencoder"

    def __init__(
        self,
        hidden: tuple[int, ...] = (64, 32, 12),
        epochs: int = 25,
        batch_size: int = 1024,
        lr: float = 2e-3,
        weight_decay: float = 1e-5,
        patience: int = 4,
        seed: int = 0,
        threads: int | None = None,
        verbose: bool = False,
    ) -> None:
        self.hidden = hidden
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.weight_decay = weight_decay
        self.patience = patience
        self.seed = seed
        self.threads = threads
        self.verbose = verbose
        self.model_: NumpyAutoencoder | None = None
        self.history_: list[dict] = []

    def fit(self, X: np.ndarray) -> "AutoencoderDetector":
        import torch
        from torch import nn

        if self.threads:
            torch.set_num_threads(self.threads)
        torch.manual_seed(self.seed)
        rng = np.random.default_rng(self.seed)
        X = np.asarray(X, dtype=np.float32)
        idx = rng.permutation(len(X))
        n_val = max(1, int(0.1 * len(X)))
        Xtr = torch.from_numpy(X[idx[n_val:]])
        Xva = torch.from_numpy(X[idx[:n_val]])

        dims = [X.shape[1], *self.hidden]
        layers: list[nn.Module] = []
        enc = list(zip(dims[:-1], dims[1:]))
        dec = [(b, a) for a, b in reversed(enc)]
        pairs = enc + dec
        for i, (a, b) in enumerate(pairs):
            layers.append(nn.Linear(a, b))
            if i != len(pairs) - 1:
                layers.append(nn.LeakyReLU(0.01))
        net = nn.Sequential(*layers)
        opt = torch.optim.AdamW(net.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=self.epochs)
        loss_fn = nn.MSELoss()

        best, best_state, bad = float("inf"), None, 0
        for epoch in range(self.epochs):
            net.train()
            perm = torch.randperm(len(Xtr))
            tot = 0.0
            for s in range(0, len(Xtr), self.batch_size):
                xb = Xtr[perm[s:s + self.batch_size]]
                opt.zero_grad()
                loss = loss_fn(net(xb), xb)
                loss.backward()
                opt.step()
                tot += loss.item() * len(xb)
            sched.step()
            net.eval()
            with torch.no_grad():
                val = loss_fn(net(Xva), Xva).item()
            self.history_.append({"epoch": epoch + 1, "train_loss": tot / len(Xtr), "val_loss": val})
            if self.verbose:
                print(f"  AE epoch {epoch + 1:02d} train={tot / len(Xtr):.5f} val={val:.5f}")
            if val < best - 1e-6:
                best, bad = val, 0
                best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
            else:
                bad += 1
                if bad >= self.patience:
                    break
        if best_state is not None:
            net.load_state_dict(best_state)

        linears = [m for m in net if isinstance(m, nn.Linear)]
        self.model_ = NumpyAutoencoder(
            weights=[m.weight.detach().numpy().T.copy() for m in linears],
            biases=[m.bias.detach().numpy().copy() for m in linears],
        )
        # Standardize per-feature errors on held-out benign so no single feature dominates.
        fe = self.model_.feature_errors(Xva.numpy())
        self.model_.feature_weights = (1.0 / np.maximum(fe.mean(axis=0), 1e-4)).astype(np.float32)
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        if self.model_ is None:
            raise RuntimeError("AutoencoderDetector is not fitted")
        return self.model_.score(X)


# --------------------------------------------------------------------------- isolation forest
class IsolationForestDetector:
    name = "isolation_forest"

    def __init__(self, n_estimators: int = 200, max_samples: int = 512, seed: int = 0) -> None:
        self.model = IsolationForest(
            n_estimators=n_estimators, max_samples=max_samples, random_state=seed, n_jobs=-1
        )

    def fit(self, X: np.ndarray) -> "IsolationForestDetector":
        self.model.fit(X)
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        return -self.model.score_samples(X)
