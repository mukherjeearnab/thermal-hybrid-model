"""Plotting utilities for comparing measured, baseline, and hybrid temperatures."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)


def plot_temperature_comparison(results: pd.DataFrame, output_path: str | Path) -> Path:
    """Plot measured, baseline (FMU), and hybrid temperature vs. time.

    Args:
        results: DataFrame with columns ``time``, ``temperature_sim``,
            ``temperature_hybrid``, and optionally ``temperature_measured``.
        output_path: File path for the saved PNG plot.

    Returns:
        The resolved output path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 5))

    if "temperature_measured" in results.columns and results["temperature_measured"].notna().any():
        ax.plot(
            results["time"],
            results["temperature_measured"],
            label="Measured",
            color="black",
            linewidth=1.0,
            alpha=0.6,
        )
    ax.plot(
        results["time"],
        results["temperature_sim"],
        label="Baseline (FMU)",
        color="tab:blue",
        linestyle="--",
    )
    ax.plot(
        results["time"],
        results["temperature_hybrid"],
        label="Hybrid (FMU + residual)",
        color="tab:red",
    )

    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Temperature [degC]")
    ax.set_title("Baseline vs. Hybrid vs. Measured Temperature")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    logger.info("Saved comparison plot to %s", output_path)
    return output_path
