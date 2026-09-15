"""Tests for hybrid_model.fmu_simulator.

These tests require a compiled ThermalPlant.fmu (see
scripts/export_fmu.py) and the FMPy package. They are skipped
automatically when either is unavailable, since OpenModelica is an
external dependency that may not be installed in every environment.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

fmpy = pytest.importorskip("fmpy")

from hybrid_model.fmu_simulator import FMUSimulator  # noqa: E402

FMU_PATH = PROJECT_ROOT / "artifacts" / "fmu" / "ThermalPlant.fmu"

requires_fmu = pytest.mark.skipif(
    not FMU_PATH.exists(),
    reason="ThermalPlant.fmu not found; run scripts/export_fmu.py first.",
)


@requires_fmu
def test_load_fmu_and_inspect_variables():
    sim = FMUSimulator(FMU_PATH, input_names=["power", "ambient"], output_names=["temperature"])
    try:
        names = set(sim._var_refs.keys())
        assert {"power", "ambient", "temperature"}.issubset(names)
    finally:
        sim.close()


@requires_fmu
def test_batch_simulation_produces_finite_output():
    sim = FMUSimulator(FMU_PATH, input_names=["power", "ambient"], output_names=["temperature"])
    try:
        time = np.arange(0.0, 10.0, 0.1)
        inputs = pd.DataFrame(
            {"time": time, "power": np.where(time < 5.0, 0.0, 50.0), "ambient": 25.0}
        )
        result = sim.simulate_batch(inputs, step_size=0.1, output_column="temperature_sim")
        assert "temperature_sim" in result.columns
        assert np.all(np.isfinite(result["temperature_sim"].to_numpy()))
    finally:
        sim.close()


@requires_fmu
def test_missing_variable_raises_clear_error():
    from hybrid_model.fmu_simulator import FMUError

    with pytest.raises(FMUError):
        FMUSimulator(FMU_PATH, input_names=["power", "does_not_exist"], output_names=["temperature"])
