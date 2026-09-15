"""Tests for hybrid_model.synthetic_system."""

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hybrid_model.synthetic_system import (  # noqa: E402
    SyntheticSystemParams,
    generate_synthetic_dataset,
    make_input_trajectory,
    simulate_true_system,
)


def test_trajectory_length():
    df = make_input_trajectory(0.0, 100.0, 0.1)
    expected_len = int(round(100.0 / 0.1)) + 1
    assert len(df) == expected_len


def test_initial_temperature_is_correct():
    params = SyntheticSystemParams(T_start=25.0)
    df = make_input_trajectory(0.0, 10.0, 0.1)
    temps = simulate_true_system(df, params)
    assert temps[0] == 25.0


def test_temperature_increases_after_power_step():
    params = SyntheticSystemParams()
    df = make_input_trajectory(0.0, 100.0, 0.1, power_step_time=20.0, power_after_step=50.0)
    temps = simulate_true_system(df, params)
    idx_before = np.searchsorted(df["time"].to_numpy(), 20.0) - 1
    idx_end = len(temps) - 1
    assert temps[idx_end] > temps[idx_before]


def test_deterministic_for_fixed_seed():
    params = SyntheticSystemParams()
    df1 = generate_synthetic_dataset(0.0, 50.0, 0.1, params, seed=123)
    df2 = generate_synthetic_dataset(0.0, 50.0, 0.1, params, seed=123)
    np.testing.assert_array_equal(
        df1["temperature_measured"].to_numpy(), df2["temperature_measured"].to_numpy()
    )


def test_different_seeds_differ():
    params = SyntheticSystemParams()
    df1 = generate_synthetic_dataset(0.0, 50.0, 0.1, params, seed=1)
    df2 = generate_synthetic_dataset(0.0, 50.0, 0.1, params, seed=2)
    assert not np.array_equal(
        df1["temperature_measured"].to_numpy(), df2["temperature_measured"].to_numpy()
    )


def test_nonlinearity_makes_output_differ_from_linear_baseline():
    linear_params = SyntheticSystemParams(nonlinear_coefficient=0.0)
    nonlinear_params = SyntheticSystemParams(nonlinear_coefficient=0.01)

    df_linear = generate_synthetic_dataset(0.0, 100.0, 0.1, linear_params, seed=0, add_noise=False)
    df_nonlinear = generate_synthetic_dataset(
        0.0, 100.0, 0.1, nonlinear_params, seed=0, add_noise=False
    )

    assert not np.allclose(
        df_linear["temperature_true"].to_numpy(),
        df_nonlinear["temperature_true"].to_numpy(),
    )
