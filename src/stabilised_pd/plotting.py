"""Plot helpers kept separate from the numerical kernel implementation."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .model import SimulationResult


def von_mises_plane_strain(stress: np.ndarray, poisson_ratio: float) -> np.ndarray:
    """Return 3-D von Mises stress reconstructed from plane-strain stress."""

    sigma_x = stress[..., 0, 0]
    sigma_y = stress[..., 1, 1]
    tau_xy = stress[..., 0, 1]
    sigma_z = poisson_ratio * (sigma_x + sigma_y)
    return np.sqrt(
        0.5
        * (
            (sigma_x - sigma_y) ** 2
            + (sigma_y - sigma_z) ** 2
            + (sigma_z - sigma_x) ** 2
        )
        + 3.0 * tau_xy**2
    )


def save_summary_figure(
    result: SimulationResult,
    poisson_ratio: float,
    destination: str | Path,
) -> Path:
    """Save displacement and von Mises contours as a publication-style PNG."""

    import matplotlib.pyplot as plt

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    displacement_y = result.displacement[..., 1].T * 1.0e3
    von_mises = von_mises_plane_strain(result.stress, poisson_ratio).T / 1.0e3
    extent = [
        result.coordinates[..., 0].min(),
        result.coordinates[..., 0].max(),
        result.coordinates[..., 1].min(),
        result.coordinates[..., 1].max(),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(8.2, 5.0), constrained_layout=True)
    panels = (
        (displacement_y, "Vertical displacement", "mm", "coolwarm"),
        (von_mises, "von Mises stress", "kPa", "viridis"),
    )
    for label, (values, title, unit, colour_map) in zip("ab", panels, strict=False):
        axis = axes[0] if label == "a" else axes[1]
        image = axis.imshow(
            values,
            origin="lower",
            extent=extent,
            aspect="equal",
            cmap=colour_map,
        )
        axis.set_title(f"({label}) {title}")
        axis.set_xlabel("x (m)")
        axis.set_ylabel("y (m)")
        colour_bar = fig.colorbar(image, ax=axis, shrink=0.82)
        colour_bar.set_label(unit)
    fig.savefig(destination, dpi=240, bbox_inches="tight")
    plt.close(fig)
    return destination
