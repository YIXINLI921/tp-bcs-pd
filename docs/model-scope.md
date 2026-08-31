# Model scope

## Implemented in version 0.1.0

The code represents a two-dimensional rectangular body using uniformly spaced
material points and a total-Lagrangian neighbourhood. It implements:

1. the NOSB-PD approximation of the deformation gradient;
2. small-strain isotropic elasticity under plane-strain kinematics;
3. conventional symmetrised correspondence forces in the complete-horizon
   interior;
4. a stress-difference nonlocal divergence in the `2δ` boundary layer;
5. direct zero and non-zero traction treatment on the outermost point layer;
6. bond-level stabilisation of zero-energy deformation modes; and
7. explicit adaptive dynamic relaxation for quasi-static equilibrium.

The shape tensor is recomputed from the reference configuration and inverted at
each material point during model construction. The neighbourhood contains
integer lattice offsets whose Euclidean distance is strictly smaller than the
configured horizon ratio.

## Extension boundary

The solver is structured for later extension to computational plasticity,
fracture, fluids, and fluid–structure interaction. Each extension requires a
defined state model, configuration schema, and independent verification cases.

## Differences from the legacy script

The legacy `debug.py` is retained unchanged apart from its corrected sample
index. The package separates the formulation into configuration, kernels,
results, and command-line modules. It also constrains displacement and all
velocity states at fixed points after every ADR update; the legacy script reset
only displacement.

Linear elastic stress is computed from total small strain. For constant moduli,
this is equivalent to accumulating elastic increments without history drift.

## Units and dimensional convention

All inputs use SI units. The implementation preserves the original script's
representative volume `Δx³`, even though the geometry is visualised in 2-D.
This corresponds to an implicit out-of-plane thickness of one point spacing.
Changing that convention requires a consistent re-derivation of force density,
boundary area, inertia, and stabilisation terms; it should not be altered as a
single isolated parameter.
