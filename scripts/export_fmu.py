#!/usr/bin/env python3
"""Export ThermalPlant.mo as an FMI 2.0 Co-Simulation FMU using OpenModelica.

Two modes are supported:

  automatic : drive the OpenModelica Scripting API (OMPython/omc) to
              compile the FMU directly from this script.
  manual    : print step-by-step instructions for exporting the FMU
              through the OMEdit GUI, for platforms where automatic
              scripting is unreliable.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hybrid_model.config import load_config  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def export_automatic(model_path: Path, model_name: str, fmu_output_path: Path) -> None:
    """Export the FMU via the OpenModelica Python scripting interface (OMPython)."""
    try:
        from OMPython import OMCSessionZMQ
    except ImportError as exc:
        raise RuntimeError(
            "OMPython is required for automatic export. Install it with "
            "'pip install OMPython', or use --mode=manual instead."
        ) from exc

    omc = OMCSessionZMQ()

    load_result = omc.sendExpression(f'loadFile("{model_path.as_posix()}")')
    if load_result is not True:
        raise RuntimeError(f"Failed to load {model_path}: {omc.sendExpression('getErrorString()')}")

    fmu_path_result = omc.sendExpression(
        f'translateModelFMU({model_name}, version="2.0", fmuType="cs")'
    )
    if not fmu_path_result:
        raise RuntimeError(
            f"FMU export failed: {omc.sendExpression('getErrorString()')}"
        )

    generated_fmu = Path(fmu_path_result)
    if not generated_fmu.exists():
        # OMC sometimes reports a path relative to the working directory.
        generated_fmu = Path.cwd() / fmu_path_result

    fmu_output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(generated_fmu, fmu_output_path)
    logger.info("Exported FMU to %s", fmu_output_path)


def print_manual_instructions(model_path: Path, model_name: str, fmu_output_path: Path) -> None:
    print(
        f"""
Manual FMU export instructions (OMEdit)
========================================

1. Launch OMEdit (installed alongside OpenModelica).
2. File -> Open Model/Library File(s)...
   Select: {model_path}
3. In the Libraries Browser, right-click '{model_name}'.
4. Choose: Export FMU
   - FMI Version: 2.0
   - FMI Type: Co-Simulation
5. OMEdit writes '{model_name}.fmu' into your working directory
   (usually the OMEdit working directory shown in the status bar).
6. Copy the generated FMU to:
   {fmu_output_path}

   Example (Linux/macOS):
     cp {model_name}.fmu {fmu_output_path}
   Example (Windows PowerShell):
     Copy-Item {model_name}.fmu {fmu_output_path}

7. Re-run this script's automatic mode later, or continue directly with:
     python scripts/generate_data.py
"""
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default=str(PROJECT_ROOT / "configs" / "default.yaml")
    )
    parser.add_argument(
        "--mode",
        choices=["automatic", "manual"],
        default="automatic",
        help="Export mode. Use 'manual' if OMPython scripting is unreliable "
        "on your platform.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    model_path = PROJECT_ROOT / "modelica" / "ThermalPlant.mo"
    model_name = "ThermalPlant"
    fmu_output_path = config.simulation.fmu_path

    if not model_path.exists():
        logger.error("Modelica source file not found: %s", model_path)
        sys.exit(1)

    if args.mode == "manual":
        print_manual_instructions(model_path, model_name, fmu_output_path)
        return

    try:
        export_automatic(model_path, model_name, fmu_output_path)
    except RuntimeError as exc:
        logger.error("Automatic export failed: %s", exc)
        logger.error("Falling back to manual instructions:")
        print_manual_instructions(model_path, model_name, fmu_output_path)
        sys.exit(1)


if __name__ == "__main__":
    main()
