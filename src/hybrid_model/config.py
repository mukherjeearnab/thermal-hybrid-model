"""Configuration loading and validation.

All scripts load a single YAML configuration file (see
``configs/default.yaml``) through :func:`load_config`. Keeping configuration
separate from code lets the FMU path, model architecture, and training
hyperparameters change without touching any Python source.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when the configuration file is missing keys or invalid values."""


def _require(d: dict, key: str, path: str) -> Any:
    if key not in d:
        raise ConfigError(f"Missing required configuration key '{path}.{key}'")
    return d[key]


@dataclass
class SimulationConfig:
    fmu_path: Path
    start_time: float
    stop_time: float
    step_size: float
    initial_temperature: float
    input_variables: dict
    output_variables: dict


@dataclass
class ThermalModelConfig:
    R: float
    C: float
    T_start: float


@dataclass
class SyntheticSystemConfig:
    R_true: float
    C_true: float
    nonlinear_coefficient: float
    noise_std: float
    power_schedule: list | None = None
    ambient_schedule: list | None = None


@dataclass
class DataConfig:
    raw_path: Path
    processed_path: Path
    validation_fraction: float


@dataclass
class ModelConfig:
    input_features: list
    hidden_sizes: list
    activation: str
    output_size: int


@dataclass
class TrainingConfig:
    epochs: int
    batch_size: int
    learning_rate: float
    weight_decay: float
    checkpoint_path: Path
    normalization_path: Path
    train_loss_path: Path
    val_loss_path: Path


@dataclass
class ResultsConfig:
    inference_path: Path
    plot_path: Path


@dataclass
class ProjectConfig:
    name: str
    seed: int


@dataclass
class Config:
    project: ProjectConfig
    simulation: SimulationConfig
    thermal_model: ThermalModelConfig
    synthetic_system: SyntheticSystemConfig
    data: DataConfig
    model: ModelConfig
    training: TrainingConfig
    results: ResultsConfig
    root: Path = field(default_factory=Path.cwd)

    def resolve(self, path: Path) -> Path:
        """Resolve a config-relative path against the project root."""
        path = Path(path)
        return path if path.is_absolute() else self.root / path


def load_config(config_path: str | Path, root: str | Path | None = None) -> Config:
    """Load and validate a YAML configuration file.

    Args:
        config_path: Path to the YAML configuration file.
        root: Project root used to resolve relative paths. Defaults to the
            parent directory of ``config_path``'s grandparent (i.e. the
            project root when the config lives in ``configs/``), falling
            back to the current working directory.

    Returns:
        A populated :class:`Config` dataclass.

    Raises:
        ConfigError: If the file is missing or required keys are absent.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        raise ConfigError(f"Configuration file is empty or malformed: {config_path}")

    if root is None:
        # configs/default.yaml -> project root is parent of 'configs'
        root = config_path.resolve().parent.parent

    root = Path(root)

    try:
        project_raw = _require(raw, "project", "")
        sim_raw = _require(raw, "simulation", "")
        thermal_raw = _require(raw, "thermal_model", "")
        synth_raw = _require(raw, "synthetic_system", "")
        data_raw = _require(raw, "data", "")
        model_raw = _require(raw, "model", "")
        training_raw = _require(raw, "training", "")
        results_raw = _require(raw, "results", "")

        project = ProjectConfig(
            name=_require(project_raw, "name", "project"),
            seed=int(_require(project_raw, "seed", "project")),
        )
        simulation = SimulationConfig(
            fmu_path=root / _require(sim_raw, "fmu_path", "simulation"),
            start_time=float(_require(sim_raw, "start_time", "simulation")),
            stop_time=float(_require(sim_raw, "stop_time", "simulation")),
            step_size=float(_require(sim_raw, "step_size", "simulation")),
            initial_temperature=float(
                _require(sim_raw, "initial_temperature", "simulation")
            ),
            input_variables=_require(sim_raw, "input_variables", "simulation"),
            output_variables=_require(sim_raw, "output_variables", "simulation"),
        )
        thermal_model = ThermalModelConfig(
            R=float(_require(thermal_raw, "R", "thermal_model")),
            C=float(_require(thermal_raw, "C", "thermal_model")),
            T_start=float(_require(thermal_raw, "T_start", "thermal_model")),
        )
        power_schedule_raw = synth_raw.get("power_schedule")
        ambient_schedule_raw = synth_raw.get("ambient_schedule")
        synthetic_system = SyntheticSystemConfig(
            R_true=float(_require(synth_raw, "R_true", "synthetic_system")),
            C_true=float(_require(synth_raw, "C_true", "synthetic_system")),
            nonlinear_coefficient=float(
                _require(synth_raw, "nonlinear_coefficient", "synthetic_system")
            ),
            noise_std=float(_require(synth_raw, "noise_std", "synthetic_system")),
            power_schedule=[tuple(bp) for bp in power_schedule_raw]
            if power_schedule_raw
            else None,
            ambient_schedule=[tuple(bp) for bp in ambient_schedule_raw]
            if ambient_schedule_raw
            else None,
        )
        data = DataConfig(
            raw_path=root / _require(data_raw, "raw_path", "data"),
            processed_path=root / _require(data_raw, "processed_path", "data"),
            validation_fraction=float(
                _require(data_raw, "validation_fraction", "data")
            ),
        )
        model = ModelConfig(
            input_features=list(_require(model_raw, "input_features", "model")),
            hidden_sizes=list(_require(model_raw, "hidden_sizes", "model")),
            activation=str(_require(model_raw, "activation", "model")),
            output_size=int(_require(model_raw, "output_size", "model")),
        )
        training = TrainingConfig(
            epochs=int(_require(training_raw, "epochs", "training")),
            batch_size=int(_require(training_raw, "batch_size", "training")),
            learning_rate=float(_require(training_raw, "learning_rate", "training")),
            weight_decay=float(_require(training_raw, "weight_decay", "training")),
            checkpoint_path=root
            / _require(training_raw, "checkpoint_path", "training"),
            normalization_path=root
            / _require(training_raw, "normalization_path", "training"),
            train_loss_path=root
            / _require(training_raw, "train_loss_path", "training"),
            val_loss_path=root / _require(training_raw, "val_loss_path", "training"),
        )
        results = ResultsConfig(
            inference_path=root / _require(results_raw, "inference_path", "results"),
            plot_path=root / _require(results_raw, "plot_path", "results"),
        )
    except ConfigError:
        raise
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid configuration value: {exc}") from exc

    if not (0.0 < data.validation_fraction < 1.0):
        raise ConfigError(
            "data.validation_fraction must be strictly between 0 and 1, "
            f"got {data.validation_fraction}"
        )
    if simulation.step_size <= 0:
        raise ConfigError("simulation.step_size must be positive")
    if simulation.stop_time <= simulation.start_time:
        raise ConfigError("simulation.stop_time must be greater than start_time")
    if thermal_model.R <= 0 or thermal_model.C <= 0:
        raise ConfigError("thermal_model.R and thermal_model.C must be positive")

    cfg = Config(
        project=project,
        simulation=simulation,
        thermal_model=thermal_model,
        synthetic_system=synthetic_system,
        data=data,
        model=model,
        training=training,
        results=results,
        root=root,
    )
    logger.debug("Loaded configuration from %s (root=%s)", config_path, root)
    return cfg


def load_json(path: str | Path) -> dict:
    """Load a JSON file into a dict, raising ConfigError on failure."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)
