"""FMI 2.0 Co-Simulation orchestration through FMPy.

FMI is the boundary between the Modelica simulation and Python: OpenModelica
exports ``ThermalPlant.mo`` as an FMU, and this module drives that FMU
through the standard FMI Co-Simulation API. Variable references are always
resolved by name from the FMU's model description -- never hard-coded --
so that regenerating the FMU (even with different internal value
references) does not silently break the orchestration layer.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

try:
    from fmpy import extract, read_model_description
    from fmpy.fmi2 import FMU2Slave
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "FMPy is required for FMU simulation. Install it with 'pip install fmpy'."
    ) from exc

logger = logging.getLogger(__name__)


class FMUError(Exception):
    """Raised for FMU loading, variable resolution, or simulation errors."""


class FMUSimulator:
    """Loads and drives an FMI 2.0 Co-Simulation FMU by variable name.

    Example:
        >>> sim = FMUSimulator(
        ...     fmu_path="artifacts/fmu/ThermalPlant.fmu",
        ...     input_names=["power", "ambient"],
        ...     output_names=["temperature"],
        ... )
        >>> df = sim.simulate_batch(inputs_df, start_time=0.0, step_size=0.1)
        >>> sim.close()
    """

    def __init__(
        self,
        fmu_path: str | Path,
        input_names: Iterable[str],
        output_names: Iterable[str],
    ) -> None:
        self.fmu_path = Path(fmu_path)
        if not self.fmu_path.exists():
            raise FMUError(f"FMU file not found: {self.fmu_path}")

        self.input_names = list(input_names)
        self.output_names = list(output_names)

        self.model_description = read_model_description(str(self.fmu_path))
        self._var_refs: dict[str, int] = {
            v.name: v.valueReference for v in self.model_description.modelVariables
        }

        missing = [
            name
            for name in [*self.input_names, *self.output_names]
            if name not in self._var_refs
        ]
        if missing:
            available = sorted(self._var_refs.keys())
            raise FMUError(
                f"Required FMU variable(s) not found: {missing}. "
                f"Available variables: {available}"
            )

        self._unzipdir = extract(str(self.fmu_path))
        self._fmu: FMU2Slave | None = None
        self._instantiated = False
        logger.debug(
            "Loaded FMU '%s' with variables %s",
            self.fmu_path.name,
            list(self._var_refs.keys()),
        )

    def _value_reference(self, name: str) -> int:
        if name not in self._var_refs:
            raise FMUError(
                f"Variable '{name}' is not present in the FMU model description."
            )
        return self._var_refs[name]

    # -- lifecycle -----------------------------------------------------

    def _instantiate(self, start_time: float) -> None:
        self._fmu = FMU2Slave(
            guid=self.model_description.guid,
            unzipDirectory=self._unzipdir,
            modelIdentifier=self.model_description.coSimulation.modelIdentifier,
            instanceName="ThermalPlantInstance",
        )
        self._fmu.instantiate()
        self._fmu.setupExperiment(startTime=start_time)
        self._fmu.enterInitializationMode()
        self._fmu.exitInitializationMode()
        self._instantiated = True

    def _terminate(self) -> None:
        if self._instantiated and self._fmu is not None:
            try:
                self._fmu.terminate()
            finally:
                self._fmu.freeInstance()
                self._instantiated = False
                self._fmu = None

    def close(self) -> None:
        """Terminate the FMU instance and remove extracted temporary files."""
        self._terminate()
        if self._unzipdir and Path(self._unzipdir).exists():
            shutil.rmtree(self._unzipdir, ignore_errors=True)
        logger.debug("Closed FMU '%s'", self.fmu_path.name)

    def __enter__(self) -> "FMUSimulator":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # -- simulation ------------------------------------------------------

    def set_inputs(self, values: dict[str, float]) -> None:
        """Set one or more FMU input variables by name."""
        if self._fmu is None:
            raise FMUError("FMU is not instantiated; call inside a running session.")
        for name, value in values.items():
            self._fmu.setReal([self._value_reference(name)], [float(value)])

    def get_outputs(self, names: Iterable[str] | None = None) -> dict[str, float]:
        """Read one or more FMU output variables by name."""
        if self._fmu is None:
            raise FMUError("FMU is not instantiated; call inside a running session.")
        names = list(names) if names is not None else self.output_names
        refs = [self._value_reference(n) for n in names]
        values = self._fmu.getReal(refs)
        return dict(zip(names, values))

    def advance(self, current_time: float, step_size: float) -> None:
        """Advance the FMU by one communication step."""
        if self._fmu is None:
            raise FMUError("FMU is not instantiated; call inside a running session.")
        self._fmu.doStep(
            currentCommunicationPoint=current_time,
            communicationStepSize=step_size,
        )

    def simulate_batch(
        self,
        inputs: pd.DataFrame,
        step_size: float,
        output_column: str = "temperature",
        time_column: str = "time",
    ) -> pd.DataFrame:
        """Run the FMU over a full input trajectory for dataset generation.

        Args:
            inputs: DataFrame with a time column and one column per
                declared input variable name.
            step_size: Fixed communication step size [s]. The FMU's
                internal solver integrates between communication points;
                Python only observes state at these discrete steps.
            output_column: Name to give the resulting output column
                (typically ``temperature_sim``).
            time_column: Name of the time column in ``inputs``.

        Returns:
            A copy of ``inputs`` with an added output column.
        """
        missing_cols = [n for n in self.input_names if n not in inputs.columns]
        if missing_cols:
            raise FMUError(f"Input DataFrame is missing columns: {missing_cols}")

        times = inputs[time_column].to_numpy()
        start_time = float(times[0])

        self._instantiate(start_time)
        try:
            outputs = np.empty(len(inputs), dtype=float)
            for i in range(len(inputs)):
                t = float(times[i])
                row_inputs = {name: float(inputs.iloc[i][name]) for name in self.input_names}
                self.set_inputs(row_inputs)
                if i > 0:
                    self.advance(float(times[i - 1]), step_size)
                result = self.get_outputs(self.output_names)
                outputs[i] = result[self.output_names[0]]
        finally:
            self._terminate()

        result_df = inputs.copy()
        result_df[output_column] = outputs

        if not np.all(np.isfinite(outputs)):
            raise FMUError("FMU produced non-finite output values during batch simulation.")

        logger.info("Simulated FMU over %d steps", len(inputs))
        return result_df

    # -- step-wise online use --------------------------------------------

    def start_session(self, start_time: float) -> None:
        """Instantiate the FMU for step-wise (online) execution."""
        self._instantiate(start_time)

    def step(
        self,
        current_time: float,
        step_size: float,
        inputs: dict[str, float],
    ) -> dict[str, float]:
        """Advance the FMU by one step and return output values.

        Intended for the online hybrid inference loop, where each step is
        driven interactively rather than from a pre-built batch.
        """
        self.set_inputs(inputs)
        self.advance(current_time, step_size)
        return self.get_outputs(self.output_names)

    def end_session(self) -> None:
        """Terminate a step-wise session started with :meth:`start_session`."""
        self._terminate()
