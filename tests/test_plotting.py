from __future__ import annotations

import numpy as np
import pytest

from stabilised_pd.plotting import von_mises_plane_strain


def test_von_mises_for_uniaxial_stress_without_poisson_coupling() -> None:
    stress = np.zeros((2, 3, 2, 2))
    stress[..., 0, 0] = 125.0
    equivalent = von_mises_plane_strain(stress, poisson_ratio=0.0)
    assert equivalent == pytest.approx(np.full((2, 3), 125.0))


def test_von_mises_is_zero_for_zero_stress() -> None:
    stress = np.zeros((1, 1, 2, 2))
    assert von_mises_plane_strain(stress, 0.25)[0, 0] == 0.0
