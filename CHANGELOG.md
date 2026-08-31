# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned

- Independent reference-solution verification and automated convergence study.

### Added

- Five-group simulation gallery with compressed MP4 animations, poster frames,
  and an inline spider-web GIF illustrating nonlocal interaction.
- Elastic-plate benchmark figures comparing FEM, classical NOSB-PD, and improved
  NOSB-PD stress fields and upper-boundary stress profiles.

## [0.1.0] - 2026-08-31

### Added

- Installable `src`-layout Python package and command-line interface.
- Validated JSON configurations for the reference elastic plate and smoke test.
- Parallel Taichi kernels for elastic NOSB-PD kinematics, correspondence force,
  boundary-layer stress divergence, traction balance, stabilisation, and ADR.
- Compressed field output, JSON run summary, and publication-style contour plot.
- Unit and numerical smoke tests.
- Theory, model-scope, verification, citation, contribution, conduct, security,
  licence, and continuous-integration files.
- Original project banner and method schematic.

### Changed

- Refactored the monolithic research script into configuration, model, plotting,
  and command-line modules.
- Linear elastic stress is evaluated directly from total small strain.
- Fixed boundary points now constrain velocity states as well as displacement.

### Preserved

- The original `debug.py` remains as a provenance reference, with only its
  previously out-of-range output index corrected.
