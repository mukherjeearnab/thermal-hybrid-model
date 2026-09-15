"""Tests for hybrid_model.models and checkpointing via hybrid_model.training."""

import sys
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hybrid_model.models import ResidualMLP  # noqa: E402
from hybrid_model.normalization import FeatureNormalizer  # noqa: E402
from hybrid_model.training import load_checkpoint, save_checkpoint, set_seed  # noqa: E402


class _FakeTrainingConfig:
    def __init__(self, hidden_sizes, activation):
        self.model = type("M", (), {"hidden_sizes": hidden_sizes})()


def test_model_accepts_batch_and_shape():
    model = ResidualMLP(input_size=3, hidden_sizes=(32, 32), output_size=1)
    x = torch.randn(16, 3)
    y = model(x)
    assert y.shape == (16, 1)


def test_training_reduces_loss_on_toy_dataset():
    set_seed(0)
    torch.manual_seed(0)
    x = torch.randn(64, 3)
    true_w = torch.tensor([[1.5], [-2.0], [0.5]])
    y = x @ true_w + 0.01 * torch.randn(64, 1)

    model = ResidualMLP(input_size=3, hidden_sizes=(16, 16), output_size=1)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = torch.nn.MSELoss()

    initial_loss = loss_fn(model(x), y).item()
    for _ in range(200):
        optimizer.zero_grad()
        loss = loss_fn(model(x), y)
        loss.backward()
        optimizer.step()
    final_loss = loss_fn(model(x), y).item()

    assert final_loss < initial_loss


def test_checkpoint_save_and_reload_roundtrip(tmp_path):
    class _Cfg:
        class model:
            hidden_sizes = [16, 16]
            activation = "tanh"

    model = ResidualMLP(input_size=3, hidden_sizes=(16, 16), output_size=1, activation="tanh")
    features = np.random.default_rng(0).normal(size=(20, 3)).astype(np.float32)
    normalizer = FeatureNormalizer.fit(features, ["temperature_sim", "power", "ambient"])

    checkpoint_path = tmp_path / "model.pt"
    normalization_path = tmp_path / "norm.json"

    save_checkpoint(
        model=model,
        normalizer=normalizer,
        checkpoint_path=checkpoint_path,
        normalization_path=normalization_path,
        feature_cols=["temperature_sim", "power", "ambient"],
        config=_Cfg(),
    )

    reloaded_model, reloaded_normalizer, feature_cols = load_checkpoint(
        checkpoint_path, normalization_path
    )

    x = torch.from_numpy(features[:4])
    with torch.no_grad():
        original_pred = model(x)
        reloaded_pred = reloaded_model(x)

    assert torch.allclose(original_pred, reloaded_pred)
    assert feature_cols == ["temperature_sim", "power", "ambient"]
    np.testing.assert_allclose(normalizer.mean, reloaded_normalizer.mean)
