# PyTorch Residual Model

## Why residual learning

The Modelica model already captures the known, dominant physics (a linear
RC thermal circuit). The synthetic "true" system used for measurements
differs only through a small, unmodeled nonlinear loss term. Rather than
training a neural network to predict the temperature outright — which
would throw away the physically meaningful baseline and require the
network to relearn linear heat-transfer behavior from scratch — this
project trains PyTorch to predict only the *residual*:

```
residual(t) = temperature_measured(t) - temperature_sim(t)
```

This keeps the physical model as an interpretable, extrapolation-friendly
baseline, and lets the (much smaller, much easier) ML task focus purely on
the discrepancy the physics doesn't capture. It also means the network's
output stays bounded and small, which is easier to train reliably than
predicting absolute temperature.

## Input features

```
temperature_sim   -- current simulated temperature from the FMU
power             -- currently applied power
ambient           -- current ambient temperature
```

These are exactly the FMU's own I/O plus its own output, so the residual
model can be evaluated at inference time using only what the FMU already
produces.

## Target construction

```
residual = temperature_measured - temperature_sim
```

Computed once during dataset preparation (`hybrid_model/dataset.py`), not
recomputed during training. Training is **never** done directly on
`temperature_measured` — see the project's `configs/default.yaml` for how
`residual` is the only target column referenced in `training.py`.

## Architecture

```
Linear(3, 32) -> Tanh -> Linear(32, 32) -> Tanh -> Linear(32, 1)
```

Implemented in `hybrid_model/models.py::ResidualMLP`, fully configurable
via `configs/default.yaml` (`model.hidden_sizes`, `model.activation`).

## Normalization

- **Inputs** are standardized to zero mean / unit variance
  (`hybrid_model/normalization.py::FeatureNormalizer`), fit only on the
  training split and reused unchanged for validation and inference.
- **Targets** (residuals) are left unnormalized. Residuals here are
  already small and in physically meaningful degrees Celsius, so
  unnormalized MSE gives well-scaled gradients and the loss/error values
  are directly interpretable without an inverse-transform step. If a
  future version uses a system with much larger or smaller residuals,
  target normalization should be added and documented here.

## Loss function

Mean squared error:

```
L = (1/N) * sum_i (e_i - e_hat_i)^2
```

## Checkpointing

`hybrid_model/training.py::save_checkpoint` saves a single `.pt` file
containing the model's `state_dict` plus enough architecture metadata
(`input_size`, `hidden_sizes`, `output_size`, `activation`,
`feature_cols`) to reconstruct the model without needing the original
config, plus a separate `normalization.json` with the fitted feature
mean/std. `load_checkpoint` reverses this exactly, so
`model(normalizer.transform(x))` after reload matches the pre-save model
bit-for-bit (see `tests/test_model.py`).

## Inference

At inference time (`hybrid_model/inference.py`), for each FMU step:

1. Read `temperature_sim` from the FMU.
2. Build the feature vector `[temperature_sim, power, ambient]`.
3. Normalize with the saved `FeatureNormalizer`.
4. Predict `predicted_residual` with the loaded `ResidualMLP`.
5. Compute `temperature_hybrid = temperature_sim + predicted_residual`.
