"""Elastic stabilised peridynamics implemented with Taichi."""

from .config import SimulationConfig
from .model import ElasticStabilisedPD, SimulationResult, initialise_taichi

__all__ = [
    "ElasticStabilisedPD",
    "SimulationConfig",
    "SimulationResult",
    "initialise_taichi",
]

__version__ = "0.1.0"
