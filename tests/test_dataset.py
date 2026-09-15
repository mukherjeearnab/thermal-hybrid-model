"""Tests for hybrid_model.dataset, using a monkeypatched FMU simulator so
that no real FMU or OpenModelica install is required.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

fmpy = pytest.importorskip("fmpy")  # fmu_simulator (imported by dataset) needs FMPy

from hybrid_model import dataset as dataset_mod  # noqa: E402
from hybrid_model.config import load_config  # noqa: E402


class _FakeFMUSimulator:
    """Drop-in stand-in for FMUSimulator.simulate_batch used in tests."""

    def __init__(self, fmu_path, input_names, output_names):
        self.input_names = input_names
        self.output_names = output_names

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def simulate_batch(self, inputs, step_size, output_column="temperature"):
        # Simple linear response for a deterministic, fast test double.
        result = inputs.copy()
        result[output_column] = inputs["ambient"] + 0.5 * inputs["power"]
        return result


@pytest.fixture()
def tmp_config(tmp_path, monkeypatch):
    config_text = f"""
project:
  name: test
  seed: 7

simulation:
  fmu_path: fake.fmu
  start_time: 0.0
  stop_time: 5.0
  step_size: 0.5
  initial_temperature: 25.0
  input_variables:
    power: power
    ambient: ambient
  output_variables:
    temperature: temperature

thermal_model:
  R: 0.5
  C: 100.0
  T_start: 25.0

synthetic_system:
  R_true: 0.5
  C_true: 100.0
  nonlinear_coefficient: 0.002
  noise_std: 0.0

data:
  raw_path: data/raw/m.csv
  processed_path: data/processed/p.csv
  validation_fraction: 0.2

model:
  input_features: [temperature_sim, power, ambient]
  hidden_sizes: [8, 8]
  activation: tanh
  output_size: 1

training:
  epochs: 2
  batch_size: 4
  learning_rate: 0.01
  weight_decay: 0.0
  checkpoint_path: artifacts/checkpoints/m.pt
  normalization_path: artifacts/checkpoints/n.json
  train_loss_path: artifacts/metrics/tl.csv
  val_loss_path: artifacts/metrics/vl.csv

results:
  inference_path: results/r.csv
  plot_path: results/plots/p.png
"""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_path = config_dir / "default.yaml"
    config_path.write_text(config_text)

    (tmp_path / "fake.fmu").write_text("placeholder")

    config = load_config(config_path, root=tmp_path)

    monkeypatch.setattr(dataset_mod, "FMUSimulator", _FakeFMUSimulator)
    return config


def test_build_dataset_has_required_columns(tmp_config):
    df = dataset_mod.build_dataset(tmp_config)
    assert list(df.columns) == dataset_mod.REQUIRED_OUTPUT_COLUMNS


def test_build_dataset_residual_is_measured_minus_sim(tmp_config):
    df = dataset_mod.build_dataset(tmp_config)
    expected = df["temperature_measured"] - df["temperature_sim"]
    pd.testing.assert_series_equal(df["residual"], expected, check_names=False)


def test_build_dataset_writes_files(tmp_config):
    dataset_mod.build_dataset(tmp_config)
    assert tmp_config.data.raw_path.exists()
    assert tmp_config.data.processed_path.exists()


def test_train_validation_split_is_deterministic(tmp_config):
    df = dataset_mod.build_dataset(tmp_config)
    train1, val1 = dataset_mod.train_validation_split(df, 0.3, seed=1)
    train2, val2 = dataset_mod.train_validation_split(df, 0.3, seed=1)
    pd.testing.assert_frame_equal(train1, train2)
    pd.testing.assert_frame_equal(val1, val2)
    assert len(train1) + len(val1) == len(df)
