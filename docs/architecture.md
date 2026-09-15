# Architecture

## Data flow

```mermaid
flowchart LR
    Inputs[Power and ambient inputs]
    FMU[OpenModelica ThermalPlant FMU]
    Sim[Simulated temperature]
    ML[PyTorch ResidualMLP]
    Residual[Predicted residual]
    Hybrid[Hybrid temperature]

    Inputs --> FMU
    FMU --> Sim
    Sim --> ML
    Inputs --> ML
    ML --> Residual
    Sim --> Hybrid
    Residual --> Hybrid
```

## Component responsibilities

### Modelica model (`modelica/ThermalPlant.mo`)

Encodes the known physics: a single lumped thermal mass with a
linear heat-loss path to ambient. This is the interpretable, physically
grounded baseline. It is intentionally simple and intentionally
*incomplete* — see `docs/modelica_model.md`.

### FMU (compiled artifact)

OpenModelica compiles `ThermalPlant.mo` into an FMI 2.0 Co-Simulation FMU.
The FMU is the portable, tool-independent artifact that Python actually
runs; nothing in the Python code depends on OpenModelica being installed
at *inference* time, only at *export* time.

### Python orchestration layer (`src/hybrid_model/`)

- `fmu_simulator.py`: drives the FMU through FMI (set inputs, step,
  read outputs), resolving all variable references by name.
- `synthetic_system.py`: generates synthetic ground-truth measurements
  from a slightly nonlinear "true" system (standing in for real sensor
  data).
- `dataset.py`: joins FMU output with synthetic measurements and computes
  residual targets, without touching PyTorch.
- `training.py` / `models.py`: train and checkpoint the residual model.
- `inference.py`: runs the FMU and the trained model together, step by
  step, to produce hybrid predictions.
- `plotting.py`: renders the comparison plot.
- `config.py`: the single point where all file paths and hyperparameters
  are loaded and validated from `configs/default.yaml`.

### PyTorch model (`ResidualMLP`)

A small 3→32→32→1 MLP that predicts only the *residual* error of the
simulation, not the temperature itself. It never runs inside Modelica;
Modelica and PyTorch remain fully independent artifacts connected only
through the Python orchestration layer.

## Why FMI as the boundary

FMI is a standardized, tool-independent interface for exchanging
precompiled simulation models and supporting co-simulation between tools
[synopsys](https://www.synopsys.com/content/dam/synopsys/verification/documents/fmi-modelexchange-cosim-v2.0.pdf).
Using FMI means:

- OpenModelica is only required at export time, not at every training or
  inference run.
- The same FMU could in principle be produced by a different Modelica
  tool without changing any Python code.
- The Python layer treats the physical model as a black box with a
  well-defined input/output contract (`power`, `ambient` in;
  `temperature` out), which keeps the physics and ML layers decoupled.
