# Numerical formulation

This note records the concepts and equations implemented by the solver.

## Kinematics and shape tensor

For material point `i`, the reference bond to family point `j` is

```text
ξᵢⱼ = xⱼ − xᵢ,
```

and its deformed counterpart is `Yᵢⱼ = yⱼ − yᵢ`. With influence function
`ωᵢⱼ = δ³ / |ξᵢⱼ|³` and representative volume `Vⱼ`, the discrete shape tensor
and deformation gradient are

```text
Kᵢ = Σⱼ ωᵢⱼ (ξᵢⱼ ⊗ ξᵢⱼ) Vⱼ,
Fᵢ = [Σⱼ ωᵢⱼ (Yᵢⱼ ⊗ ξᵢⱼ) Vⱼ] Kᵢ⁻¹.
```

The small-strain tensor is `εᵢ = sym(Fᵢ) − I`. For constant isotropic plane-
strain elasticity, the in-plane Cauchy stress is evaluated as

```text
σᵢ = λ tr(εᵢ) I + 2G εᵢ,
```

where `λ = Eν / [(1+ν)(1−2ν)]` and `2G = E/(1+ν)`.

## Interior correspondence force

For points with complete horizons, the internal force density is

```text
Lᵢ = Σⱼ ωᵢⱼ (PᵢKᵢ⁻¹ + PⱼKⱼ⁻¹) ξᵢⱼ Vⱼ.
```

At small strain the implementation identifies the first Piola–Kirchhoff stress
with the Cauchy stress.

## Boundary-layer stress divergence

Incomplete horizons make shape tensors spatially nonuniform and may introduce
residual forces. Within `2δ` of the boundary, the force density is

```text
Lᵢ = Σⱼ ωᵢⱼ (Pⱼ − Pᵢ) Kᵢ⁻¹ ξᵢⱼ Vⱼ
     + (T_ext − Pᵢ nᵢ) / Δx.
```

`T_ext` and the outward normal `n` are nonzero only on an outermost material-
point layer. On a traction-free surface, `T_ext = 0`; the stress-normal term is
still retained. Corner normals are obtained by summing the normals of the two
intersecting surfaces, matching the force contribution of both faces.

## Zero-energy-mode stabilisation

The nodal deformation gradient does not uniquely constrain every bond-level
deformation. The residual deformation state is

```text
zᵢⱼ = Yᵢⱼ − Fᵢ ξᵢⱼ.
```

The stabilisation force acts on this residual through a bond-aligned matrix
proportional to Young's modulus. Antisymmetric assembly from both bond ends
suppresses nonphysical oscillations without a fitted penalty coefficient.

## Adaptive dynamic relaxation

ADR introduces fictitious diagonal inertia and an adaptive damping coefficient
estimated from a Rayleigh quotient. Displacement and half-step velocity are
advanced explicitly. The current release uses a fixed number of virtual-time
steps; a residual-based stopping condition is part of the roadmap.

Essential constraints are applied to displacement, full-step velocity, and both
half-step velocity states. This avoids retained momentum at a fixed point.
