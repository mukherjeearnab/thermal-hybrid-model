#!/usr/bin/env python3
"""Generate synthetic measurements, run the FMU, and build the training dataset."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hybrid_model.config import load_config  # noqa: E402
from hybrid_model.dataset import build_dataset  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", default=str(PROJECT_ROOT / "configs" / "default.yaml")
    )
    args = parser.parse_args()

    config = load_config(args.config)

    if not config.simulation.fmu_path.exists():
        logger.error(
            "FMU not found at %s. Run 'python scripts/export_fmu.py' first.",
            config.simulation.fmu_path,
        )
        sys.exit(1)

    dataset = build_dataset(config)
    logger.info("Dataset generation complete: %d rows.", len(dataset))


if __name__ == "__main__":
    main()
