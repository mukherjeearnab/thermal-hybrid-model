"""Training loop for ResidualMLP.

The FMU is never invoked here: training reads the pre-built processed
dataset (see :mod:`hybrid_model.dataset`) so that every epoch only performs
cheap tensor operations.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from .config import Config
from .dataset import train_validation_split
from .models import ResidualMLP
from .normalization import FeatureNormalizer

logger = logging.getLogger(__name__)


def set_seed(seed: int) -> None:
    """Set all relevant random seeds for reproducibility."""
    np.random.seed(seed)
    torch.manual_seed(seed)


def _write_loss_csv(path: Path, losses: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["epoch", "loss"])
        for epoch, loss in enumerate(losses, start=1):
            writer.writerow([epoch, loss])


def train_residual_model(config: Config, dataset: pd.DataFrame) -> dict:
    """Train ResidualMLP on a pre-built residual dataset.

    Args:
        config: Loaded project configuration.
        dataset: DataFrame as produced by
            :func:`hybrid_model.dataset.build_dataset`, containing the
            feature columns in ``config.model.input_features`` and a
            ``residual`` column.

    Returns:
        Dict with keys ``model``, ``normalizer``, ``train_losses``,
        ``val_losses``.
    """
    set_seed(config.project.seed)

    feature_cols = config.model.input_features
    missing = [c for c in feature_cols + ["residual"] if c not in dataset.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    train_df, val_df = train_validation_split(
        dataset, config.data.validation_fraction, config.project.seed
    )

    train_features = train_df[feature_cols].to_numpy(dtype=np.float32)
    val_features = val_df[feature_cols].to_numpy(dtype=np.float32)
    train_target = train_df[["residual"]].to_numpy(dtype=np.float32)
    val_target = val_df[["residual"]].to_numpy(dtype=np.float32)

    normalizer = FeatureNormalizer.fit(train_features, feature_cols)
    train_features_norm = normalizer.transform(train_features).astype(np.float32)
    val_features_norm = normalizer.transform(val_features).astype(np.float32)

    train_dataset = TensorDataset(
        torch.from_numpy(train_features_norm), torch.from_numpy(train_target)
    )
    val_features_t = torch.from_numpy(val_features_norm)
    val_target_t = torch.from_numpy(val_target)

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.training.batch_size,
        shuffle=True,
        generator=torch.Generator().manual_seed(config.project.seed),
    )

    model = ResidualMLP(
        input_size=len(feature_cols),
        hidden_sizes=config.model.hidden_sizes,
        output_size=config.model.output_size,
        activation=config.model.activation,
    )
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.training.learning_rate,
        weight_decay=config.training.weight_decay,
    )
    loss_fn = nn.MSELoss()

    train_losses: list[float] = []
    val_losses: list[float] = []

    for epoch in range(1, config.training.epochs + 1):
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            pred = model(batch_x)
            loss = loss_fn(pred, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1
        train_losses.append(epoch_loss / max(n_batches, 1))

        model.eval()
        with torch.no_grad():
            val_pred = model(val_features_t)
            val_loss = loss_fn(val_pred, val_target_t).item()
        val_losses.append(val_loss)

        if epoch % max(1, config.training.epochs // 10) == 0 or epoch == 1:
            logger.info(
                "epoch %d/%d train_loss=%.6f val_loss=%.6f",
                epoch,
                config.training.epochs,
                train_losses[-1],
                val_losses[-1],
            )

    _write_loss_csv(config.training.train_loss_path, train_losses)
    _write_loss_csv(config.training.val_loss_path, val_losses)

    save_checkpoint(
        model=model,
        normalizer=normalizer,
        checkpoint_path=config.training.checkpoint_path,
        normalization_path=config.training.normalization_path,
        feature_cols=feature_cols,
        config=config,
    )

    return {
        "model": model,
        "normalizer": normalizer,
        "train_losses": train_losses,
        "val_losses": val_losses,
    }


def save_checkpoint(
    model: ResidualMLP,
    normalizer: FeatureNormalizer,
    checkpoint_path: Path,
    normalization_path: Path,
    feature_cols: list,
    config: Config,
) -> None:
    """Save model weights and normalization statistics to disk."""
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "input_size": model.input_size,
            "hidden_sizes": config.model.hidden_sizes,
            "output_size": model.output_size,
            "activation": config.model.activation,
            "feature_cols": feature_cols,
        },
        checkpoint_path,
    )
    normalizer.save(normalization_path)
    logger.info("Saved checkpoint to %s", checkpoint_path)


def load_checkpoint(
    checkpoint_path: Path, normalization_path: Path
) -> tuple[ResidualMLP, FeatureNormalizer, list]:
    """Load a trained model and its normalizer from disk."""
    checkpoint_path = Path(checkpoint_path)
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    data = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model = ResidualMLP(
        input_size=data["input_size"],
        hidden_sizes=data["hidden_sizes"],
        output_size=data["output_size"],
        activation=data["activation"],
    )
    model.load_state_dict(data["state_dict"])
    model.eval()

    normalizer = FeatureNormalizer.load(normalization_path)
    return model, normalizer, data["feature_cols"]
