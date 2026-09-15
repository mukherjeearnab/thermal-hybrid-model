"""Build the residual-training dataset by joining FMU output with
synthetic measurements.

This module does not train or invoke PyTorch; it only runs the FMU (once,
in batch) and computes:

    residual = temperature_measured - temperature_sim

The resulting dataset is saved to disk so that the training script never
needs to execute the FMU per-batch.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Config
from .fmu_simulator import FMUSimulator
from .synthetic_system import SyntheticSystemParams, generate_synthetic_dataset

logger = logging.getLogger(__name__)

REQUIRED_OUTPUT_COLUMNS = [
    "time",
    "power",
    "ambient",
    "temperature_sim",
    "temperature_true",
    "temperature_measured",
    "residual",
]


def build_dataset(config: Config) -> pd.DataFrame:
    """Generate synthetic measurements, run the FMU, and join the two.

    Args:
        config: Loaded project configuration.

    Returns:
        DataFrame with columns matching :data:`REQUIRED_OUTPUT_COLUMNS`.
    """
    synth_params = SyntheticSystemParams(
        R_true=config.synthetic_system.R_true,
        C_true=config.synthetic_system.C_true,
        nonlinear_coefficient=config.synthetic_system.nonlinear_coefficient,
        noise_std=config.synthetic_system.noise_std,
        T_start=config.simulation.initial_temperature,
    )

    power_schedule = getattr(config.synthetic_system, "power_schedule", None)
    ambient_schedule = getattr(config.synthetic_system, "ambient_schedule", None)

    measured = generate_synthetic_dataset(
        start_time=config.simulation.start_time,
        stop_time=config.simulation.stop_time,
        step_size=config.simulation.step_size,
        params=synth_params,
        seed=config.project.seed,
        power_schedule=power_schedule,
        ambient_schedule=ambient_schedule,
    )

    config.data.raw_path.parent.mkdir(parents=True, exist_ok=True)
    measured.to_csv(config.data.raw_path, index=False)
    logger.info("Saved raw synthetic measurements to %s", config.data.raw_path)

    input_names = list(config.simulation.input_variables.values())
    output_names = list(config.simulation.output_variables.values())

    with FMUSimulator(
        fmu_path=config.simulation.fmu_path,
        input_names=input_names,
        output_names=output_names,
    ) as sim:
        fmu_inputs = measured[["time", "power", "ambient"]].copy()
        sim_result = sim.simulate_batch(
            fmu_inputs,
            step_size=config.simulation.step_size,
            output_column="temperature_sim",
        )

    joined = measured.merge(
        sim_result[["time", "temperature_sim"]], on="time", how="inner"
    )
    joined["residual"] = joined["temperature_measured"] - joined["temperature_sim"]
    joined = joined[REQUIRED_OUTPUT_COLUMNS]

    if joined.isnull().values.any():
        raise ValueError("Joined dataset contains missing values after merge.")

    config.data.processed_path.parent.mkdir(parents=True, exist_ok=True)
    joined.to_csv(config.data.processed_path, index=False)
    logger.info(
        "Saved processed residual dataset (%d rows) to %s",
        len(joined),
        config.data.processed_path,
    )
    return joined


def train_validation_split(
    df: pd.DataFrame, validation_fraction: float, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a dataset into train/validation subsets.

    Splits chronologically: the first ``(1 - validation_fraction)`` of the
    (time-ordered) rows are used for training, and the remaining, later
    rows are held out as validation. This means validation covers a
    genuinely unseen time range rather than being interspersed samples
    from the same trajectory the model trained on.

    Args:
        df: Dataset, assumed already sorted (or sortable) by ``time``.
        validation_fraction: Fraction of rows (from the end) held out.
        seed: Unused for the chronological split; kept for interface
            compatibility with earlier random-split behavior.
    """
    df_sorted = df.sort_values("time").reset_index(drop=True)
    n_val = int(round(len(df_sorted) * validation_fraction))
    n_train = len(df_sorted) - n_val
    train_df = df_sorted.iloc[:n_train].reset_index(drop=True)
    val_df = df_sorted.iloc[n_train:].reset_index(drop=True)
    return train_df, val_df