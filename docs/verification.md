# Verification and reproducibility

## Verification levels

The repository distinguishes three levels of evidence:

1. **Software smoke tests** check configuration validation, finite numerical
   fields, boundary enforcement, output shape, and expected loading direction.
2. **Implementation verification** should compare selected fields against an
   independent analytical or FEM solution and quantify numerical error.
3. **Method validation** compares predictions with independently documented
   numerical benchmarks or experimental observations.

Automated tests in version 0.1.0 cover level 1. The benchmark figures provide
comparison context but are not yet encoded as regression tests. Levels 2 and 3
remain open tasks.

## Reproducible run record

Every reported run should archive:

- the exact Git commit and software version;
- the JSON configuration file;
- Python, NumPy, and Taichi versions;
- operating system and CPU/GPU backend;
- `summary.json` and `fields.npz`;
- convergence history or the completed ADR step count; and
- any post-processing script used to generate a figure.

Preserve archived configurations under unique names. Generated results are
excluded from Git by default; long-term datasets should be deposited in a
research-data repository and linked to a tagged release.

## Required benchmark extensions

Before calling the elastic plate quantitatively verified in this public code,
add automated checks for:

- reaction equilibrium against the applied 200 kPa traction;
- displacement and stress along a documented centreline sampling path;
- error relative to a documented FEM or analytical reference;
- `m`-convergence at constant horizon radius;
- `δ`-convergence at constant horizon ratio;
- invariance under rigid translation and small rigid rotation; and
- sensitivity to precision and parallel backend.

Each comparison should define the norm, reference field, sampling locations,
and acceptance tolerance before results are inspected.
