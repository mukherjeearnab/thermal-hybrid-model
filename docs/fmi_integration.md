# FMI Integration

## What an FMU is

An FMU (Functional Mock-up Unit) is a zip archive produced according to
the Functional Mock-up Interface (FMI) standard, containing a compiled
model, a machine-readable description of its variables
(`modelDescription.xml`), and (for Co-Simulation) a native solver bundled
inside the FMU.

## Why FMI is used as the interface

FMI is a tool-independent standard for exchanging precompiled models and
supporting co-simulation between tools
[synopsys](https://www.synopsys.com/content/dam/synopsys/verification/documents/fmi-modelexchange-cosim-v2.0.pdf).
Using it as the boundary between Modelica and Python means:

- OpenModelica is a build-time dependency only — running training or
  inference never needs `omc`, only the compiled `.fmu`.
- The Python orchestration code (`FMUSimulator`) has no OpenModelica- or
  Modelica-specific logic; it only speaks the generic FMI Co-Simulation
  API via FMPy.
- The physics and ML layers stay decoupled: swapping in a different
  Modelica model (or even a non-Modelica FMU) requires no Python changes,
  as long as the exposed variable names match.

## Co-Simulation

This project exports FMI **2.0, Co-Simulation** (not Model Exchange). In
Co-Simulation, the FMU bundles its own solver; the importing tool
(Python, here) only calls `doStep()` to advance the FMU by a fixed
communication interval and reads/writes variables at each communication
point. Internally, between communication points, the FMU's own solver may
take many smaller integration steps — the fixed `step_size` seen by
Python is a *communication* step, not necessarily the underlying ODE
solver's step.

## Communication steps

The configured `step_size` (`simulation.step_size` in
`configs/default.yaml`, default `0.1` seconds) is passed to every
`doStep()` call. Since the thermal time constant here is `tau = R*C = 50s`,
a `0.1s` step comfortably resolves the dynamics.

## Variable references

FMI identifies variables by integer "value references" internally, but
these are not guaranteed stable across FMU exports. `FMUSimulator`
resolves every variable strictly by **name**, reading
`modelDescription.xml` through FMPy's `read_model_description()` and
building a name→valueReference map at load time
(`hybrid_model/fmu_simulator.py::FMUSimulator.__init__`). Any variable
missing from the FMU raises a clear `FMUError` immediately, rather than
silently proceeding with a stale reference.

## FMU lifecycle

`FMUSimulator` follows the standard FMI 2.0 Co-Simulation lifecycle:

1. `extract()` the FMU zip to a temporary directory.
2. `instantiate()` a slave instance.
3. `setupExperiment()` / `enterInitializationMode()` /
   `exitInitializationMode()`.
4. Repeated `setReal()` (inputs) → `doStep()` → `getReal()` (outputs).
5. `terminate()` and `freeInstance()`.
6. Remove the extracted temporary directory (`close()`).

Two usage patterns are supported:

- **Batch** (`simulate_batch`): runs an entire pre-built input trajectory
  in one call, used for dataset generation.
- **Step-wise** (`start_session` / `step` / `end_session`): advances one
  communication step at a time, interleaved with a PyTorch prediction,
  used for online hybrid inference.

## Limitations and error handling

- The FMU is assumed single-input-vector, single-scalar-output for this
  project's variable set (`power`, `ambient` in; `temperature` out); a
  more general multi-output orchestration would extend
  `FMUSimulator.get_outputs`.
- `simulate_batch` raises `FMUError` if the output contains any
  non-finite (`NaN`/`inf`) values, rather than silently returning a
  partially invalid dataset.
- Every FMU session (batch or step-wise) is wrapped so that
  `terminate()`/`freeInstance()` and the extracted-directory cleanup run
  even if an exception occurs mid-simulation, avoiding leaked FMU
  instances or temp files.
