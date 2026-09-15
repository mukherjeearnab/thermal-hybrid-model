"""Online hybrid inference: FMU -> ResidualMLP -> hybrid temperature.

Data flow, per time step:

    power, ambient -> FMU -> temperature_sim -> ResidualMLP -> predicted_residual
    temperature_hybrid = temperature_sim + predicted_residual
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from .config import Config
from .fmu_simulator import FMUSimulator
from .models import ResidualMLP
from .normalization import FeatureNormalizer
from .training import load_checkpoint

logger = logging.getLogger(__name__)

INFERENCE_COLUMNS = [
    "time",
    "power",
    "ambient",
    "temperature_sim",
    "predicted_residual",
    "temperature_hybrid",
    "temperature_measured",
]


def run_hybrid_inference(
    config: Config,
    inputs: pd.DataFrame,
    model: ResidualMLP | None = None,
    normalizer: FeatureNormalizer | None = None,
    feature_cols: list | None = None,
) -> pd.DataFrame:
    """Run the FMU + ResidualMLP hybrid pipeline over an input trajectory.

    Args:
        config: Loaded project configuration.
        inputs: DataFrame with columns ``time``, ``power``, ``ambient``,
            and optionally ``temperature_measured`` for later comparison.
        model, normalizer, feature_cols: Pre-loaded artifacts; if omitted,
            they are loaded from the paths in ``config``.

    Returns:
        DataFrame with columns matching :data:`INFERENCE_COLUMNS`.
    """
    if model is None or normalizer is None or feature_cols is None:
        model, normalizer, feature_cols = load_checkpoint(
            config.training.checkpoint_path, config.training.normalization_path
        )
    model.eval()

    input_names = list(config.simulation.input_variables.values())
    output_names = list(config.simulation.output_variables.values())

    times = inputs["time"].to_numpy()
    n = len(inputs)
    temperature_sim = np.empty(n, dtype=float)
    predicted_residual = np.empty(n, dtype=float)

    with FMUSimulator(
        fmu_path=config.simulation.fmu_path,
        input_names=input_names,
        output_names=output_names,
    ) as sim:
        sim.start_session(start_time=float(times[0]))
        try:
            for i in range(n):
                row = inputs.iloc[i]
                step_inputs = {name: float(row[name]) for name in input_names}

                if i == 0:
                    sim.set_inputs(step_inputs)
                    outputs = sim.get_outputs(output_names)
                else:
                    outputs = sim.step(
                        current_time=float(times[i - 1]),
                        step_size=config.simulation.step_size,
                        inputs=step_inputs,
                    )
                t_sim = outputs[output_names[0]]
                temperature_sim[i] = t_sim

                feature_row = {
                    "temperature_sim": t_sim,
                    "power": row["power"],
                    "ambient": row["ambient"],
                }
                feature_vec = np.array(
                    [[feature_row[c] for c in feature_cols]], dtype=np.float32
                )
                feature_vec_norm = normalizer.transform(feature_vec).astype(np.float32)
                with torch.no_grad():
                    pred = model(torch.from_numpy(feature_vec_norm))
                predicted_residual[i] = float(pred.item())
        finally:
            sim.end_session()

    result = inputs.copy()
    result["temperature_sim"] = temperature_sim
    result["predicted_residual"] = predicted_residual
    result["temperature_hybrid"] = temperature_sim + predicted_residual

    if "temperature_measured" not in result.columns:
        result["temperature_measured"] = np.nan

    result = result[INFERENCE_COLUMNS]

    if not np.all(np.isfinite(result["temperature_hybrid"])):
        raise ValueError("Hybrid inference produced non-finite temperature values.")

    config.results.inference_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(config.results.inference_path, index=False)
    logger.info("Saved hybrid inference output to %s", config.results.inference_path)
    return result
