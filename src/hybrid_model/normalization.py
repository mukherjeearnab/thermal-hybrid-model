"""Input feature normalization.

Input features (``temperature_sim``, ``power``, ``ambient``) are
standardized (zero mean, unit variance) before being fed to the MLP, which
is standard practice for stabilizing MLP training.

The residual *target* is intentionally left unnormalized: residuals here
are small (roughly the scale of a few degrees Celsius, driven by a small
known nonlinearity), so plain MSE on raw-degree residuals already yields
well-scaled gradients, and leaving the target in physical units means the
loss curve and reported errors are directly interpretable in degrees C
without an extra de-normalization step at inference time. This choice is
recorded in ``docs/pytorch_model.md``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FeatureNormalizer:
    """Per-feature z-score normalization: (x - mean) / std."""

    mean: np.ndarray
    std: np.ndarray
    feature_names: list

    @classmethod
    def fit(cls, features: np.ndarray, feature_names: list) -> "FeatureNormalizer":
        mean = features.mean(axis=0)
        std = features.std(axis=0)
        std = np.where(std < 1e-8, 1.0, std)  # avoid divide-by-zero for constant cols
        return cls(mean=mean, std=std, feature_names=list(feature_names))

    def transform(self, features: np.ndarray) -> np.ndarray:
        return (features - self.mean) / self.std

    def inverse_transform(self, features: np.ndarray) -> np.ndarray:
        return features * self.std + self.mean

    def to_dict(self) -> dict:
        return {
            "mean": self.mean.tolist(),
            "std": self.std.tolist(),
            "feature_names": self.feature_names,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FeatureNormalizer":
        return cls(
            mean=np.array(data["mean"], dtype=float),
            std=np.array(data["std"], dtype=float),
            feature_names=list(data["feature_names"]),
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
        logger.debug("Saved normalization statistics to %s", path)

    @classmethod
    def load(cls, path: str | Path) -> "FeatureNormalizer":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Normalization file not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))
