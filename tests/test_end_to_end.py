"""End-to-end test of the full pipeline: dataset -> training -> inference.

Requires a compiled ThermalPlant.fmu (see scripts/export_fmu.py). Skipped
automatically if the FMU or FMPy is unavailable.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

fmpy = pytest.importorskip("fmpy")

from hybrid_model.config import load_config  # noqa: E402
from hybrid_model.dataset import build_dataset  # noqa: E402
from hybrid_model.inference import INFERENCE_COLUMNS, run_hybrid_inference  # noqa: E402
from hybrid_model.training import train_residual_model  # noqa: E402

FMU_PATH = PROJECT_ROOT / "artifacts" / "fmu" / "ThermalPlant.fmu"

requires_fmu = pytest.mark.skipif(
    not FMU_PATH.exists(),
    reason="ThermalPlant.fmu not found; run scripts/export_fmu.py first.",
)


@requires_fmu
def test_full_pipeline_runs_end_to_end(tmp_path):
    config = load_config(PROJECT_ROOT / "configs" / "default.yaml", root=tmp_path)
    # Point at the real FMU while keeping outputs isolated in tmp_path.
    config.simulation.fmu_path = FMU_PATH
    config.training.epochs = 3

    dataset = build_dataset(config)
    assert len(dataset) > 0

    train_result = train_residual_model(config, dataset)
    assert len(train_result["train_losses"]) == config.training.epochs

    inputs = pd.read_csv(config.data.raw_path)[
        ["time", "power", "ambient", "temperature_measured"]
    ]
    results = run_hybrid_inference(config, inputs)

    assert config.results.inference_path.exists()
    assert list(results.columns) == INFERENCE_COLUMNS
    assert results["temperature_hybrid"].notna().all()
    assert results["temperature_hybrid"].apply(lambda v: v == v).all()  # no NaN
