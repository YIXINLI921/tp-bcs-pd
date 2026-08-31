"""Minimal library-level run of the elastic plate model."""

from pathlib import Path

from stabilised_pd import ElasticStabilisedPD, SimulationConfig, initialise_taichi

project_root = Path(__file__).resolve().parents[1]
config = SimulationConfig.from_json(project_root / "configs" / "smoke_test.json")
initialise_taichi(config)

result = ElasticStabilisedPD(config).run()
point = config.sample_index

print(f"maximum displacement = {result.max_displacement:.6e} m")
print(f"sample displacement  = {result.displacement[point]} m")
print(f"sample stress        =\n{result.stress[point]} Pa")
