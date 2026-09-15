# OpenModelica + PyTorch Residual Hybrid Model

A minimal, runnable example of coupling a physics-based Modelica thermal
simulation with a PyTorch residual-correction model:

```
T_hybrid(t) = T_sim(t) + e_hat_theta(t)
```

where `T_sim` comes from an OpenModelica FMU and `e_hat_theta` is a small
neural network trained to predict the discrepancy between the simulation
and (synthetic) measurements.

## Objective

Physics-based models are interpretable and grounded in known laws, but are
often slightly wrong due to unmodeled effects. Rather than throwing the
physical model away, this project keeps it as the baseline and trains a
PyTorch MLP to learn only the *residual* error:

```
residual(t) = T_measured(t) - T_sim(t)
T_hybrid(t) = T_sim(t) + predicted_residual(t)
```

See `docs/architecture.md` for the full data-flow diagram and
`docs/pytorch_model.md` for why residual learning is used instead of
training directly on measurements.

## Project layout

```
modelica/    Modelica source (ThermalPlant.mo, ThermalPlantTest.mo)
src/hybrid_model/  Python package: config, FMU orchestration, dataset,
                    PyTorch model, training, inference, plotting
scripts/     Command-line entry points for each workflow stage
configs/     YAML configuration (single source of truth for paths/params)
tests/       pytest suite
docs/        Architecture, model, FMI, reproducibility, provenance docs
data/, artifacts/, results/   Generated outputs (not committed)
```

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

Requires Python 3.10+.

### 2. Install OpenModelica

Install OpenModelica separately from https://openmodelica.org/download/.
Make sure `omc` (the OpenModelica compiler) is available on your `PATH`:

```bash
omc --version
```

`OMPython` (included in `requirements.txt`) is used to drive `omc` from
Python for automatic FMU export. If automatic export is unreliable on your
platform, use the manual OMEdit workflow described below.

## Workflow

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install OpenModelica separately, ensure `omc` is on PATH

# 3. Export the FMU
python scripts/export_fmu.py --mode=automatic
# or, if automatic export is unreliable on your platform:
python scripts/export_fmu.py --mode=manual

# 4. Generate synthetic measurements and FMU predictions
python scripts/generate_data.py

# 5. Train the PyTorch residual model
python scripts/train.py

# 6. Run hybrid inference
python scripts/run_hybrid.py

# 7. Evaluate and plot results
python scripts/evaluate.py

# 8. Run tests
pytest
```

Equivalently, `make all` runs steps 3–7 (after `make install`).

### FMU export modes

- `--mode=automatic`: uses `OMPython` to script `omc` directly and write
  `artifacts/fmu/ThermalPlant.fmu`.
- `--mode=manual`: prints step-by-step instructions for exporting the FMU
  through the OMEdit GUI, for platforms where the automatic scripting API
  is unreliable. Copy the resulting `.fmu` file into
  `artifacts/fmu/ThermalPlant.fmu` and continue with step 4.

### Dataset generation

`scripts/generate_data.py` does two things:

1. Generates synthetic "true" measurements from a slightly nonlinear
   ground-truth system (`src/hybrid_model/synthetic_system.py`), saved to
   `data/raw/synthetic_measurements.csv`.
2. Runs the FMU once over the same input trajectory, joins it with the
   synthetic measurements, computes `residual = measured - sim`, and saves
   `data/processed/residual_dataset.csv`.

The FMU is **not** invoked again during training.

### Training

`scripts/train.py` trains `ResidualMLP` (a 3→32→32→1 MLP) on the processed
dataset, writing:

- `artifacts/checkpoints/residual_model.pt` — model weights + architecture
- `artifacts/checkpoints/normalization.json` — feature normalization stats
- `artifacts/metrics/train_loss.csv`, `artifacts/metrics/val_loss.csv`

### Inference

`scripts/run_hybrid.py` runs the FMU and the trained `ResidualMLP` together,
step by step, and writes `results/hybrid_predictions.csv`.

### Evaluation

`scripts/evaluate.py` computes baseline vs. hybrid RMSE against the
synthetic measurements and saves a comparison plot to
`results/plots/temperature_comparison.png`.

### Testing

```bash
pytest -v
```

Tests that require a compiled FMU (loading it via FMPy, running batch
simulation, the full end-to-end pipeline) are skipped automatically if
`artifacts/fmu/ThermalPlant.fmu` or FMPy is not available, so the rest of
the suite still runs without OpenModelica installed.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `omc: command not found` | OpenModelica not on `PATH` | Install OpenModelica and add its `bin/` directory to `PATH` |
| `OMPython` import error | Package not installed / OMC not reachable | `pip install OMPython`, or use `--mode=manual` |
| `FMUError: Required FMU variable(s) not found` | FMU compiled from a stale/edited `.mo` file without re-export | Re-run `scripts/export_fmu.py` after any Modelica change |
| Training loss is `NaN` | Corrupted or unjoined dataset | Re-run `scripts/generate_data.py`; check `data/processed/residual_dataset.csv` for missing values |
| Tests involving the FMU are skipped | No `artifacts/fmu/ThermalPlant.fmu` present | Run `scripts/export_fmu.py` first |

## License

MIT — see `LICENSE`.
