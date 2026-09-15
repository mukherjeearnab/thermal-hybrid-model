# Reproducibility

## Environment

| Component | Version used in development |
|---|---|
| Python | 3.10+ |
| OpenModelica | 1.21+ (any release supporting FMI 2.0 CS export) |
| PyTorch | >= 2.1 (see `requirements.txt`) |
| FMPy | >= 0.3.20 |
| NumPy | >= 1.24 |
| pandas | >= 2.0 |
| matplotlib | >= 3.7 |
| pytest | >= 7.4 |

Record the exact resolved versions for a given run with:

```bash
pip freeze > artifacts/metrics/pip_freeze.txt
omc --version
```

## Random seeds

A single seed (`project.seed` in `configs/default.yaml`, default `42`) is
used everywhere randomness matters:

- `hybrid_model.synthetic_system.generate_synthetic_dataset` — trajectory
  and measurement-noise RNG.
- `hybrid_model.dataset.train_validation_split` — deterministic
  train/validation split.
- `hybrid_model.training.set_seed` — NumPy and PyTorch seeding before
  model initialization and the shuffled `DataLoader`.

Given the same config and the same FMU, the full pipeline
(`generate_data.py` → `train.py` → `run_hybrid.py`) is deterministic on a
given machine/PyTorch build. (Bit-for-bit reproducibility across different
hardware/PyTorch versions is not guaranteed by PyTorch itself.)

## Configuration files

All paths and hyperparameters live in `configs/default.yaml`. To
reproduce a run exactly, keep (or version-control) the exact config file
used, not just the default.

## Hashing artifacts

Compute and record SHA-256 hashes of the key artifacts after a run:

```bash
sha256sum artifacts/fmu/ThermalPlant.fmu
sha256sum data/processed/residual_dataset.csv
sha256sum artifacts/checkpoints/residual_model.pt
```

These hashes are the values referenced in `docs/provenance.md`'s
`fmu_sha256`, `dataset_sha256`, and `checkpoint_sha256` fields.

## Commands to reproduce a result end to end

```bash
pip install -r requirements.txt
python scripts/export_fmu.py --mode=automatic
python scripts/generate_data.py
python scripts/train.py
python scripts/run_hybrid.py
python scripts/evaluate.py
pytest
```

Re-running these commands with an unchanged `configs/default.yaml` and
unchanged Modelica source should regenerate byte-identical CSV datasets
and (modulo PyTorch/hardware non-determinism) closely matching model
weights.
