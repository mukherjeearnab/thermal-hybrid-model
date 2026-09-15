#!/usr/bin/env python3
"""Evaluate hybrid predictions against measurements and produce a comparison plot."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hybrid_model.config import load_config  # noqa: E402
from hybrid_model.plotting import plot_temperature_comparison  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default=str(PROJECT_ROOT / "configs" / "default.yaml")
    )
    args = parser.parse_args()

    config = load_config(args.config)

    if not config.results.inference_path.exists():
        logger.error(
            "Inference results not found at %s. Run 'python scripts/run_hybrid.py' first.",
            config.results.inference_path,
        )
        sys.exit(1)

    results = pd.read_csv(config.results.inference_path)

    valid = results.dropna(subset=["temperature_measured"])
    if len(valid) > 0:
        baseline_rmse = rmse(
            valid["temperature_sim"].to_numpy(), valid["temperature_measured"].to_numpy()
        )
        hybrid_rmse = rmse(
            valid["temperature_hybrid"].to_numpy(),
            valid["temperature_measured"].to_numpy(),
        )
        logger.info("Baseline RMSE vs. measured: %.4f degC", baseline_rmse)
        logger.info("Hybrid RMSE vs. measured:   %.4f degC", hybrid_rmse)
        improvement = 100.0 * (baseline_rmse - hybrid_rmse) / baseline_rmse
        logger.info("Relative RMSE improvement:  %.1f%%", improvement)
    else:
        logger.warning("No measured temperature values available for evaluation.")

    plot_temperature_comparison(results, config.results.plot_path)


if __name__ == "__main__":
    main()
