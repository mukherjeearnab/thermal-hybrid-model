"""Synthetic ground-truth thermal system.

The baseline FMU implements a simple linear first-order thermal model. The
synthetic "true" system used to generate measurements adds a small known
nonlinear loss term so that the baseline model remains qualitatively
correct but not exact -- this discrepancy is exactly what the PyTorch
residual model is trained to learn.

    C_true * dT_true/dt = P - (T_true - Ta)/R_true
                             - k_nonlinear * (T_true - Ta)^2
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SyntheticSystemParams:
    R_true: float = 0.5
    C_true: float = 100.0
    nonlinear_coefficient: float = 0.002
    noise_std: float = 0.1
    T_start: float = 25.0


def _piecewise_constant(time: np.ndarray, breakpoints: list[tuple[float, float]]) -> np.ndarray:
    """Evaluate a piecewise-constant signal defined by (time, value) breakpoints.

    Each breakpoint's value holds until the next breakpoint's time. Values
    before the first breakpoint use the first breakpoint's value.
    """
    breakpoints = sorted(breakpoints, key=lambda bp: bp[0])
    bp_times = np.array([bp[0] for bp in breakpoints])
    bp_values = np.array([bp[1] for bp in breakpoints])
    # index of the last breakpoint <= each sample time
    idx = np.searchsorted(bp_times, time, side="right") - 1
    idx = np.clip(idx, 0, len(bp_values) - 1)
    return bp_values[idx]


def make_input_trajectory(
    start_time: float,
    stop_time: float,
    step_size: float,
    ambient: float = 25.0,
    power_step_time: float = 20.0,
    power_after_step: float = 50.0,
    power_schedule: list[tuple[float, float]] | None = None,
    ambient_schedule: list[tuple[float, float]] | None = None,
) -> pd.DataFrame:
    """Create a reproducible piecewise-constant power/ambient trajectory.

    Args:
        start_time: Simulation start time [s].
        stop_time: Simulation stop time [s].
        step_size: Time increment between samples [s].
        ambient: Constant ambient temperature [degC], used when
            ``ambient_schedule`` is not given.
        power_step_time, power_after_step: Legacy single-step interface,
            used when ``power_schedule`` is not given (kept for backward
            compatibility / the ThermalPlantTest scenario).
        power_schedule: Optional list of ``(time, power)`` breakpoints for
            an arbitrarily complex up/down power profile, e.g.
            ``[(0, 0), (20, 50), (50, 20), (70, 60), (90, 10)]``.
        ambient_schedule: Optional list of ``(time, ambient)`` breakpoints,
            for a time-varying ambient temperature.

    Returns:
        DataFrame with columns ``time``, ``power``, ``ambient``.
    """
    time = np.arange(start_time, stop_time + step_size / 2, step_size)

    if power_schedule is not None:
        power = _piecewise_constant(time, power_schedule)
    else:
        power = np.where(time < power_step_time, 0.0, power_after_step)

    if ambient_schedule is not None:
        ambient_arr = _piecewise_constant(time, ambient_schedule)
    else:
        ambient_arr = np.full_like(time, ambient)

    return pd.DataFrame({"time": time, "power": power, "ambient": ambient_arr})


def simulate_true_system(
    trajectory: pd.DataFrame,
    params: SyntheticSystemParams,
) -> np.ndarray:
    """Integrate the nonlinear "true" thermal system with explicit Euler.

    A simple forward-Euler integrator is used (no SciPy dependency
    required); the step size in the trajectory is assumed small enough
    (0.1 s versus a ~50 s time constant) for this to be accurate.

    Args:
        trajectory: DataFrame with ``time``, ``power``, ``ambient`` columns.
        params: True-system physical parameters.

    Returns:
        Array of true temperatures, one per row of ``trajectory``.
    """
    time = trajectory["time"].to_numpy()
    power = trajectory["power"].to_numpy()
    ambient = trajectory["ambient"].to_numpy()

    n = len(time)
    temperature_true = np.empty(n, dtype=float)
    temperature_true[0] = params.T_start

    for i in range(1, n):
        dt = time[i] - time[i - 1]
        T = temperature_true[i - 1]
        Ta = ambient[i - 1]
        P = power[i - 1]
        linear_loss = (T - Ta) / params.R_true
        nonlinear_loss = params.nonlinear_coefficient * (T - Ta) ** 2
        dTdt = (P - linear_loss - nonlinear_loss) / params.C_true
        temperature_true[i] = T + dt * dTdt

    return temperature_true


def generate_synthetic_dataset(
    start_time: float,
    stop_time: float,
    step_size: float,
    params: SyntheticSystemParams,
    seed: int = 42,
    add_noise: bool = True,
    power_schedule: list[tuple[float, float]] | None = None,
    ambient_schedule: list[tuple[float, float]] | None = None,
) -> pd.DataFrame:
    """Generate a reproducible synthetic measurement dataset.

    Args:
        start_time: Simulation start time [s].
        stop_time: Simulation stop time [s].
        step_size: Communication step size [s].
        params: True-system parameters (including measurement noise std).
        seed: Random seed controlling both the trajectory and the noise.
        add_noise: If False, ``temperature_measured`` equals
            ``temperature_true`` exactly (useful for tests).

    Returns:
        DataFrame with columns: time, power, ambient, temperature_true,
        temperature_measured.
    """
    rng = np.random.default_rng(seed)

    trajectory = make_input_trajectory(
        start_time,
        stop_time,
        step_size,
        power_schedule=power_schedule,
        ambient_schedule=ambient_schedule,
    )
    temperature_true = simulate_true_system(trajectory, params)

    if add_noise and params.noise_std > 0:
        noise = rng.normal(loc=0.0, scale=params.noise_std, size=len(temperature_true))
    else:
        noise = np.zeros_like(temperature_true)

    temperature_measured = temperature_true + noise

    result = trajectory.copy()
    result["temperature_true"] = temperature_true
    result["temperature_measured"] = temperature_measured

    logger.info(
        "Generated synthetic dataset with %d samples (seed=%d, noise_std=%.4f)",
        len(result),
        seed,
        params.noise_std,
    )
    return result
