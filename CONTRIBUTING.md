# Contributing

Contributions should preserve scientific traceability and match claims to the
available verification evidence.

## Before opening an issue

Search existing issues and confirm the behaviour using the latest main branch.
A useful numerical bug report includes:

- operating system, Python, Taichi, and NumPy versions;
- CPU/GPU architecture and floating-point precision;
- the smallest JSON configuration that reproduces the problem;
- the complete error message or an objective description of the unexpected
  field; and
- whether the legacy script exhibits the same behaviour.

Do not attach confidential models, unpublished third-party data, or files you
do not have permission to redistribute.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test,dev]"
pytest
ruff check .
```

## Pull requests

Keep each pull request focused. Describe the governing equation or behaviour
being changed and any difference from the documented formulation or legacy
script. Numerical changes should include:

1. a minimal automated test;
2. an independent reference, invariant, or convergence argument;
3. the configuration required to reproduce the result; and
4. updated scope and theory documentation.

Do not present a new physics module as validated solely because it runs without
error. Validation cases and acceptance tolerances must be stated explicitly.

Use clear scientific names and SI units. Format code with the project settings,
add docstrings to public interfaces, and avoid embedding machine-specific paths
or generated results in source files.

## Review criteria

Review considers numerical correctness, dimensional consistency,
reproducibility, performance, tests, documentation, and compatibility with
Taichi's parallel execution model. Discuss changes to documented equations in
an issue first.
