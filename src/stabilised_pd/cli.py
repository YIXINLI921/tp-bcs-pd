"""Command-line entry point for reproducible benchmark runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .config import SimulationConfig
from .model import ElasticStabilisedPD, initialise_taichi
from .plotting import save_summary_figure


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tp-bcs-pd",
        description=(
            "Run the elastic stabilised NOSB-PD plate benchmark with direct "
            "traction and displacement boundary conditions."
        ),
    )
    parser.add_argument("--config", type=Path, required=True, help="JSON configuration")
    parser.add_argument("--steps", type=int, help="override the configured ADR steps")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/latest"),
        help="directory for fields, diagnostics, and figure",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = SimulationConfig.from_json(args.config)
    steps = config.steps if args.steps is None else args.steps
    if steps < 1:
        raise SystemExit("--steps must be positive")

    initialise_taichi(config)
    model = ElasticStabilisedPD(config)
    result = model.run(steps=steps)

    args.output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output / "fields.npz",
        coordinates=result.coordinates,
        displacement=result.displacement,
        stress=result.stress,
        internal_force=result.internal_force,
    )
    sample_x, sample_y = config.sample_index
    summary = {
        "configuration": config.to_dict(),
        "completed_steps": result.steps,
        "adaptive_damping": result.damping,
        "max_displacement_m": result.max_displacement,
        "max_internal_force": result.max_force,
        "sample": {
            "index": [sample_x, sample_y],
            "coordinate_m": result.coordinates[sample_x, sample_y].tolist(),
            "displacement_m": result.displacement[sample_x, sample_y].tolist(),
            "stress_pa": result.stress[sample_x, sample_y].tolist(),
        },
    }
    with (args.output / "summary.json").open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2)
        stream.write("\n")
    save_summary_figure(
        result,
        config.poisson_ratio,
        args.output / "field-summary.png",
    )

    print(f"Completed {steps} ADR steps")
    print(f"Maximum displacement: {result.max_displacement:.6e} m")
    print(f"Results written to: {args.output.resolve()}")
    return 0
