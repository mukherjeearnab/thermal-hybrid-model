# Modelica Model

## Source files

- `modelica/ThermalPlant.mo` — the model itself.
- `modelica/ThermalPlantTest.mo` — a driver model that applies a power
  step and can be simulated directly in OMEdit/OMC to validate the model.

## Modelica syntax used

`ThermalPlant` is a plain equation-based Modelica `model`:

- `parameter Real` declares constants fixed at compile/simulation-start
  time (`R`, `C`, `T_start`).
- `input Real` / `output Real` declare the model's causal interface —
  the variables the FMU exposes for co-simulation.
- `initial equation` sets the state's value at `t = 0`.
- `equation` contains the ODE, using Modelica's `der()` operator for the
  time derivative.

## The thermal equation

```
C * der(temperature) = power - (temperature - ambient) / R
```

This is a standard lumped single-node thermal-resistance/capacitance
(RC) model: `power` flows into a thermal mass `C`, and heat leaks out to
`ambient` through a resistance `R`. Rearranged:

```
dT/dt = (P - (T - Ta)/R) / C
```

## Parameters

| Parameter | Meaning | Default |
|---|---|---|
| `R` | Thermal resistance | 0.5 K/W |
| `C` | Thermal capacitance | 100.0 J/K |
| `T_start` | Initial temperature | 25.0 degC |

## Inputs and outputs

| Variable | Direction | Units | Meaning |
|---|---|---|---|
| `power` | input | W | Applied power |
| `ambient` | input | degC | Ambient temperature |
| `temperature` | output | degC | Simulated device temperature |

## Initialization

`temperature = T_start` is set in the `initial equation` section, so the
FMU starts every simulation at `T_start` (25 degC by default) unless the
importing tool overrides the initial state.

## Running `ThermalPlantTest`

`ThermalPlantTest` instantiates `ThermalPlant` and drives it with:

- `ambient = 25 degC` (constant)
- `power = 0 W` for `t < 20 s`, then `power = 50 W` for `t >= 20 s`
- simulated from `t = 0` to `t = 100 s`

Open `modelica/ThermalPlantTest.mo` in OMEdit and simulate it directly, or
run it from the OMShell:

```
loadFile("modelica/ThermalPlant.mo");
loadFile("modelica/ThermalPlantTest.mo");
simulate(ThermalPlantTest, stopTime=100);
plot(plant.temperature);
```

### Interpreting the temperature plot

The plot should show `temperature` starting at 25 degC, staying flat until
`t = 20 s` (no power applied, already at steady state with ambient), then
rising smoothly toward a new steady state after the power step.

Expected steady-state temperature after the step:

```
T_steady = T_ambient + P * R = 25 + 50 * 0.5 = 50 degC
```

Expected thermal time constant (time to reach ~63% of the total change):

```
tau = R * C = 0.5 * 100 = 50 s
```

So the temperature should be roughly `25 + (50-25) * (1 - e^-1) ≈ 40.8 degC`
at `t = 20 + 50 = 70 s`, and should approach 50 degC as `t -> 100 s` (not
fully settled, since 100 s − 20 s = 80 s ≈ 1.6*tau). These values are used
directly in the validation tests in `tests/test_modelica_source.py` (static
checks) and would be used in a numerical OMC-based simulation test if one
is added.

## Exporting the FMU

See `scripts/export_fmu.py` and the "FMU export modes" section of the main
`README.md` for both the automatic (OMPython) and manual (OMEdit GUI)
export workflows. The exported FMU must be FMI 2.0, Co-Simulation type.
