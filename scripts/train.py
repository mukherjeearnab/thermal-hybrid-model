#!/usr/bin/env python3
"""Train the PyTorch ResidualMLP on the pre-built residual dataset."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hybrid_model.config import load_config  # noqa: E402
from hybrid_model.training import train_residual_model  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default=str(PROJECT_ROOT / "configs" / "default.yaml")
    )
    args = parser.parse_args()

    config = load_config(args.config)

    if not config.data.processed_path.exists():
        logger.error(
            "Processed dataset not found at %s. Run "
            "'python scripts/generate_data.py' first.",
            config.data.processed_path,
        )
        sys.exit(1)

    dataset = pd.read_csv(config.data.processed_path)
    result = train_residual_model(config, dataset)

    logger.info(
        "Training complete. Final train_loss=%.6f, val_loss=%.6f",
        result["train_losses"][-1],
        result["val_losses"][-1],
    )


if __name__ == "__main__":
    main()
