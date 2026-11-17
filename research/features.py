"""Feature transform shared by every research model.

Flow features span ~10 orders of magnitude (bytes/s vs flag counts), so we apply a signed
``log1p`` followed by standardization and clipping. Monotone transforms do not change what
tree models can learn, while they make reconstruction-based novelty detectors well behaved.
The fitted transform is plain NumPy so it can be exported to the serving stack unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SignedLogScaler:
    mean_: np.ndarray | None = None
    scale_: np.ndarray | None = None
    clip: float = 8.0

    @staticmethod
    def _slog(X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        return np.sign(X) * np.log1p(np.abs(X))

    def fit(self, X: np.ndarray) -> "SignedLogScaler":
        L = self._slog(X)
        self.mean_ = L.mean(axis=0)
        std = L.std(axis=0)
        self.scale_ = np.where(std < 1e-6, 1.0, std)  # constant columns pass through as 0
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.mean_ is None:
            raise RuntimeError("SignedLogScaler is not fitted")
        Z = (self._slog(X) - self.mean_) / self.scale_
        return np.clip(Z, -self.clip, self.clip).astype(np.float32)

    def inverse_transform(self, Z: np.ndarray) -> np.ndarray:
        """Map scaled values back to raw feature units (exact unless the value was clipped)."""
        L = np.asarray(Z, dtype=np.float64) * self.scale_ + self.mean_
        return np.sign(L) * np.expm1(np.abs(L))

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)

    def to_dict(self) -> dict:
        return {"mean": self.mean_.tolist(), "scale": self.scale_.tolist(), "clip": self.clip}

    @classmethod
    def from_dict(cls, d: dict) -> "SignedLogScaler":
        return cls(mean_=np.asarray(d["mean"]), scale_=np.asarray(d["scale"]), clip=float(d["clip"]))
