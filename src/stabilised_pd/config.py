"""Configuration objects for the elastic stabilised NOSB-PD model."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SimulationConfig:
    """Validated input parameters for a rectangular plane-strain model.

    SI units are used throughout: metre, pascal, and second.  ``nx`` and
    ``ny`` count material points along the horizontal and vertical axes.
    """

    nx: int = 50
    ny: int = 100
    width: float = 0.36
    height: float = 0.72
    horizon_ratio: float = 3.015
    young_modulus: float = 30.0e6
    poisson_ratio: float = 0.25
    traction_y: float = -200.0e3
    time_step: float = 1.0
    steps: int = 20_000
    sample_index: tuple[int, int] = (25, 78)
    architecture: str = "cpu"
    default_fp: str = "f64"
    output_interval: int = 100

    @property
    def spacing(self) -> float:
        """Uniform material-point spacing."""

        return self.width / self.nx

    @property
    def horizon(self) -> float:
        """Peridynamic horizon radius."""

        return self.horizon_ratio * self.spacing

    def validate(self) -> SimulationConfig:
        """Raise ``ValueError`` when parameters are inconsistent."""

        if self.nx < 3 or self.ny < 3:
            raise ValueError("nx and ny must both be at least 3")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        expected_height = self.spacing * self.ny
        if abs(expected_height - self.height) > 1.0e-12 * self.height:
            raise ValueError(
                "the current uniform-grid implementation requires "
                "height/ny == width/nx"
            )
        if self.horizon_ratio <= 1.0:
            raise ValueError("horizon_ratio must exceed 1")
        if self.young_modulus <= 0:
            raise ValueError("young_modulus must be positive")
        if not (-1.0 < self.poisson_ratio < 0.5):
            raise ValueError("poisson_ratio must lie between -1 and 0.5")
        if self.time_step <= 0 or self.steps < 1:
            raise ValueError("time_step and steps must be positive")
        ix, iy = self.sample_index
        if not (0 <= ix < self.nx and 0 <= iy < self.ny):
            raise ValueError("sample_index lies outside the material-point grid")
        if self.architecture not in {"cpu", "gpu"}:
            raise ValueError("architecture must be 'cpu' or 'gpu'")
        if self.default_fp not in {"f32", "f64"}:
            raise ValueError("default_fp must be 'f32' or 'f64'")
        return self

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable configuration mapping."""

        result = asdict(self)
        result["sample_index"] = list(self.sample_index)
        return result

    @classmethod
    def from_json(cls, path: str | Path) -> SimulationConfig:
        """Load and validate a configuration from a JSON file."""

        with Path(path).open(encoding="utf-8") as stream:
            raw = json.load(stream)
        known = {item.name for item in fields(cls)}
        unknown = sorted(set(raw) - known)
        if unknown:
            raise ValueError(f"unknown configuration keys: {', '.join(unknown)}")
        if "sample_index" in raw:
            raw["sample_index"] = tuple(raw["sample_index"])
        return cls(**raw).validate()
