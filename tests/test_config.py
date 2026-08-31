from __future__ import annotations

import json

import pytest

from stabilised_pd import SimulationConfig


def test_default_configuration_matches_plate_geometry() -> None:
    config = SimulationConfig().validate()
    assert config.spacing == pytest.approx(0.0072)
    assert config.horizon == pytest.approx(3.015 * 0.0072)
    assert config.sample_index == (25, 78)


def test_configuration_round_trip(tmp_path) -> None:
    path = tmp_path / "configuration.json"
    config = SimulationConfig(
        nx=8,
        ny=16,
        width=0.08,
        height=0.16,
        sample_index=(4, 12),
    )
    path.write_text(json.dumps(config.to_dict()), encoding="utf-8")
    loaded = SimulationConfig.from_json(path)
    assert loaded == config


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"sample_index": (50, 2)}, "outside"),
        ({"height": 0.70}, "uniform-grid"),
        ({"poisson_ratio": 0.5}, "poisson_ratio"),
        ({"architecture": "quantum"}, "architecture"),
    ],
)
def test_invalid_configurations_are_rejected(changes, message) -> None:
    values = SimulationConfig().to_dict()
    values.update(changes)
    with pytest.raises(ValueError, match=message):
        SimulationConfig(**values).validate()
