#!/usr/bin/env python3
"""Run the online hybrid FMU + ResidualMLP pipeline and save predictions."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hybrid_model.config import load_config  # noqa: E402
from hybrid_model.inference import run_hybrid_inference  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default=str(PROJECT_ROOT / "configs" / "default.yaml")
    )
    args = parser.parse_args()

    config = load_config(args.config)

    if not config.training.checkpoint_path.exists():
        logger.error(
            "Trained checkpoint not found at %s. Run 'python scripts/train.py' first.",
            config.training.checkpoint_path,
        )
        sys.exit(1)
    if not config.data.raw_path.exists():
        logger.error(
            "Raw measurements not found at %s. Run "
            "'python scripts/generate_data.py' first.",
            config.data.raw_path,
        )
        sys.exit(1)

    inputs = pd.read_csv(config.data.raw_path)[
        ["time", "power", "ambient", "temperature_measured"]
    ]

    results = run_hybrid_inference(config, inputs)
    logger.info("Hybrid inference complete: %d rows written.", len(results))


if __name__ == "__main__":
    main()
