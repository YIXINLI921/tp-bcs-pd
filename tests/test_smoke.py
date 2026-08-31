from __future__ import annotations

import numpy as np
import pytest
import taichi as ti

from stabilised_pd import ElasticStabilisedPD, SimulationConfig


@pytest.fixture(scope="module")
def result_and_config():
    ti.init(arch=ti.cpu, default_fp=ti.f64, offline_cache=False)
    config = SimulationConfig(
        nx=8,
        ny=16,
        width=0.08,
        height=0.16,
        steps=3,
        sample_index=(4, 12),
    ).validate()
    result = ElasticStabilisedPD(config).run()
    return result, config


def test_numerical_fields_are_finite(result_and_config) -> None:
    result, config = result_and_config
    assert result.displacement.shape == (config.nx, config.ny, 2)
    assert result.stress.shape == (config.nx, config.ny, 2, 2)
    assert np.isfinite(result.displacement).all()
    assert np.isfinite(result.stress).all()
    assert np.isfinite(result.internal_force).all()


def test_fixed_bottom_has_no_displacement(result_and_config) -> None:
    result, _ = result_and_config
    assert result.displacement[:, 0, :] == pytest.approx(0.0, abs=1.0e-15)


def test_compressive_traction_moves_top_downward(result_and_config) -> None:
    result, _ = result_and_config
    assert float(result.displacement[:, -1, 1].mean()) < 0.0
