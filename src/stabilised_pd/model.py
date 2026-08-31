"""Taichi implementation of the elastic stabilised NOSB-PD formulation."""

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import taichi as ti

from .config import SimulationConfig


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Material-point fields returned after a simulation."""

    coordinates: np.ndarray
    displacement: np.ndarray
    stress: np.ndarray
    internal_force: np.ndarray
    steps: int
    damping: float

    @property
    def max_displacement(self) -> float:
        return float(np.linalg.norm(self.displacement, axis=-1).max())

    @property
    def max_force(self) -> float:
        return float(np.linalg.norm(self.internal_force, axis=-1).max())


@ti.data_oriented
class ElasticStabilisedPD:
    """Small-strain elastic, stabilised non-ordinary state-based PD model.

    The conventional correspondence force is used where both horizons are
    complete, while a stress-divergence form is used in the boundary layer.
    The outermost layer additionally receives the prescribed traction and the
    stress-normal term obtained from the principle of virtual work.

    Taichi must be initialised before constructing this class.  Use
    :func:`initialise_taichi` for command-line and library workflows.
    """

    def __init__(self, config: SimulationConfig):
        self.config = config.validate()
        self.completed_steps = 0
        self.nx = config.nx
        self.ny = config.ny
        self.dx = config.spacing
        self.delta = config.horizon
        self.dt = config.time_step
        self.real = ti.f64 if config.default_fp == "f64" else ti.f32

        self.volume = self.dx**3
        self.bulk_factor = config.young_modulus / (
            (1.0 + config.poisson_ratio) * (1.0 - 2.0 * config.poisson_ratio)
        )
        self.stabilisation_constant = (
            12.0 * config.young_modulus / (math.pi * self.delta**4)
        )
        self.mass_diagonal = (
            0.25
            * self.dt**2
            * math.pi
            * self.delta**2
            * self.dx
            * self.stabilisation_constant
            / self.dx
            * 5.0
        )

        shape = (self.nx, self.ny)
        self.coordinates = ti.Vector.field(2, dtype=self.real, shape=shape)
        self.current_coordinates = ti.Vector.field(2, dtype=self.real, shape=shape)
        self.displacement = ti.Vector.field(2, dtype=self.real, shape=shape)
        self.velocity = ti.Vector.field(2, dtype=self.real, shape=shape)
        self.velocity_half = ti.Vector.field(2, dtype=self.real, shape=shape)
        self.velocity_half_old = ti.Vector.field(2, dtype=self.real, shape=shape)
        self.body_force = ti.Vector.field(2, dtype=self.real, shape=shape)
        self.traction = ti.Vector.field(2, dtype=self.real, shape=shape)
        self.normal = ti.Vector.field(2, dtype=self.real, shape=shape)

        self.shape_tensor = ti.Matrix.field(2, 2, dtype=self.real, shape=shape)
        self.inverse_shape_tensor = ti.Matrix.field(2, 2, dtype=self.real, shape=shape)
        self.deformation_gradient = ti.Matrix.field(2, 2, dtype=self.real, shape=shape)
        self.strain = ti.Matrix.field(2, 2, dtype=self.real, shape=shape)
        self.stress = ti.Matrix.field(2, 2, dtype=self.real, shape=shape)

        self.correspondence_force = ti.Vector.field(2, dtype=self.real, shape=shape)
        self.stabilisation_force = ti.Vector.field(2, dtype=self.real, shape=shape)
        self.internal_force = ti.Vector.field(2, dtype=self.real, shape=shape)
        self.internal_force_old = ti.Vector.field(2, dtype=self.real, shape=shape)

        offsets = self._make_offsets()
        self.number_of_offsets = len(offsets)
        self.offsets = ti.Vector.field(2, dtype=ti.i32, shape=self.number_of_offsets)
        self.offsets.from_numpy(offsets)

        self.damping_numerator = ti.field(dtype=self.real, shape=())
        self.damping_denominator = ti.field(dtype=self.real, shape=())
        self.damping = ti.field(dtype=self.real, shape=())

        self._initialise_geometry()
        self._compute_shape_tensors()
        self._apply_boundary_data()

    def _make_offsets(self) -> np.ndarray:
        radius = math.floor(self.config.horizon_ratio)
        offsets = [
            (ix, iy)
            for ix in range(-radius, radius + 1)
            for iy in range(-radius, radius + 1)
            if (ix != 0 or iy != 0)
            and math.hypot(ix, iy) < self.config.horizon_ratio
        ]
        return np.asarray(offsets, dtype=np.int32)

    @ti.func
    def _dyadic(self, first, second):
        return ti.Matrix(
            [
                [first[0] * second[0], first[0] * second[1]],
                [first[1] * second[0], first[1] * second[1]],
            ]
        )

    @ti.func
    def _inside_grid(self, ix, iy):
        return 0 <= ix < self.nx and 0 <= iy < self.ny

    @ti.kernel
    def _initialise_geometry(self):
        for ix, iy in self.coordinates:
            x = (ti.cast(ix, self.real) + 0.5) * self.dx
            y = (ti.cast(iy, self.real) + 0.5) * self.dx
            self.coordinates[ix, iy] = ti.Vector([x, y])
            outward = ti.Vector.zero(self.real, 2)
            if ix == 0:
                outward[0] -= 1.0
            if ix == self.nx - 1:
                outward[0] += 1.0
            if iy == 0:
                outward[1] -= 1.0
            if iy == self.ny - 1:
                outward[1] += 1.0
            self.normal[ix, iy] = outward

    @ti.kernel
    def _compute_shape_tensors(self):
        for ix, iy in self.shape_tensor:
            tensor = ti.Matrix.zero(self.real, 2, 2)
            origin = self.coordinates[ix, iy]
            for neighbour in range(self.number_of_offsets):
                jx = ix + self.offsets[neighbour][0]
                jy = iy + self.offsets[neighbour][1]
                if self._inside_grid(jx, jy):
                    bond = self.coordinates[jx, jy] - origin
                    distance = bond.norm()
                    weight = self.delta**3 / distance**3
                    tensor += weight * self._dyadic(bond, bond) * self.volume
            self.shape_tensor[ix, iy] = tensor
            self.inverse_shape_tensor[ix, iy] = tensor.inverse()

    @ti.kernel
    def _apply_boundary_data(self):
        for ix, iy in self.coordinates:
            self.body_force[ix, iy] = ti.Vector.zero(self.real, 2)
            self.traction[ix, iy] = ti.Vector.zero(self.real, 2)
            if iy == self.ny - 1:
                self.traction[ix, iy][1] = self.config.traction_y
            if iy == 0:
                self.displacement[ix, iy] = ti.Vector.zero(self.real, 2)
                self.velocity[ix, iy] = ti.Vector.zero(self.real, 2)
                self.velocity_half[ix, iy] = ti.Vector.zero(self.real, 2)
                self.velocity_half_old[ix, iy] = ti.Vector.zero(self.real, 2)

    @ti.kernel
    def _update_current_coordinates(self):
        for ix, iy in self.current_coordinates:
            self.current_coordinates[ix, iy] = (
                self.coordinates[ix, iy] + self.displacement[ix, iy]
            )

    @ti.kernel
    def _compute_deformation_gradient(self):
        for ix, iy in self.deformation_gradient:
            numerator = ti.Matrix.zero(self.real, 2, 2)
            reference_origin = self.coordinates[ix, iy]
            current_origin = self.current_coordinates[ix, iy]
            for neighbour in range(self.number_of_offsets):
                jx = ix + self.offsets[neighbour][0]
                jy = iy + self.offsets[neighbour][1]
                if self._inside_grid(jx, jy):
                    reference_bond = self.coordinates[jx, jy] - reference_origin
                    current_bond = self.current_coordinates[jx, jy] - current_origin
                    distance = reference_bond.norm()
                    weight = self.delta**3 / distance**3
                    numerator += (
                        weight
                        * self._dyadic(current_bond, reference_bond)
                        * self.volume
                    )
            self.deformation_gradient[ix, iy] = (
                numerator @ self.inverse_shape_tensor[ix, iy]
            )

    @ti.kernel
    def _compute_linear_elastic_stress(self):
        identity = ti.Matrix.identity(self.real, 2)
        poisson = self.config.poisson_ratio
        shear_twice = self.config.young_modulus / (1.0 + poisson)
        lame = (
            self.config.young_modulus
            * poisson
            / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
        )
        for ix, iy in self.stress:
            deformation = self.deformation_gradient[ix, iy]
            epsilon = 0.5 * (deformation + deformation.transpose()) - identity
            self.strain[ix, iy] = epsilon
            self.stress[ix, iy] = (
                lame * epsilon.trace() * identity + shear_twice * epsilon
            )

    @ti.kernel
    def _compute_correspondence_force(self):
        for ix, iy in self.correspondence_force:
            force = ti.Vector.zero(self.real, 2)
            position = self.coordinates[ix, iy]
            stress_i = self.stress[ix, iy]
            inverse_i = self.inverse_shape_tensor[ix, iy]
            boundary_width = 2.0 * self.delta
            interior = (
                position[0] > boundary_width
                and position[0] < self.config.width - boundary_width
                and position[1] > boundary_width
                and position[1] < self.config.height - boundary_width
            )
            for neighbour in range(self.number_of_offsets):
                jx = ix + self.offsets[neighbour][0]
                jy = iy + self.offsets[neighbour][1]
                if self._inside_grid(jx, jy):
                    bond = self.coordinates[jx, jy] - position
                    distance = bond.norm()
                    weight = self.delta**3 / distance**3
                    stress_j = self.stress[jx, jy]
                    if interior:
                        inverse_j = self.inverse_shape_tensor[jx, jy]
                        force += (
                            weight
                            * (stress_i @ inverse_i + stress_j @ inverse_j)
                            @ bond
                            * self.volume
                        )
                    else:
                        force += (
                            weight
                            * (stress_j - stress_i)
                            @ inverse_i
                            @ bond
                            * self.volume
                        )
            if not interior:
                force += (
                    self.traction[ix, iy] - stress_i @ self.normal[ix, iy]
                ) / self.dx
            self.correspondence_force[ix, iy] = force

    @ti.kernel
    def _compute_stabilisation_force(self):
        for ix, iy in self.stabilisation_force:
            force = ti.Vector.zero(self.real, 2)
            reference_origin = self.coordinates[ix, iy]
            current_origin = self.current_coordinates[ix, iy]
            deformation_i = self.deformation_gradient[ix, iy]
            for neighbour in range(self.number_of_offsets):
                jx = ix + self.offsets[neighbour][0]
                jy = iy + self.offsets[neighbour][1]
                if self._inside_grid(jx, jy):
                    reference_bond = self.coordinates[jx, jy] - reference_origin
                    current_bond = self.current_coordinates[jx, jy] - current_origin
                    distance = reference_bond.norm()
                    reverse_reference = -reference_bond
                    reverse_current = -current_bond
                    residual_i = current_bond - deformation_i @ reference_bond
                    residual_j = (
                        reverse_current
                        - self.deformation_gradient[jx, jy] @ reverse_reference
                    )
                    matrix_i = (
                        self.stabilisation_constant
                        * self._dyadic(reference_bond, reference_bond)
                        / distance**3
                    )
                    matrix_j = (
                        self.stabilisation_constant
                        * self._dyadic(reverse_reference, reverse_reference)
                        / distance**3
                    )
                    weight = self.delta**3 / distance**3
                    force += (
                        0.5
                        * weight
                        * self.volume
                        * (matrix_i @ residual_i - matrix_j @ residual_j)
                    )
            self.stabilisation_force[ix, iy] = force

    @ti.kernel
    def _sum_internal_force(self):
        for ix, iy in self.internal_force:
            self.internal_force[ix, iy] = (
                self.correspondence_force[ix, iy]
                + self.stabilisation_force[ix, iy]
            )

    @ti.kernel
    def _update_adaptive_damping(self):
        self.damping_numerator[None] = 0.0
        self.damping_denominator[None] = 0.0
        for ix, iy in self.displacement:
            for component in ti.static(range(2)):
                old_velocity = self.velocity_half_old[ix, iy][component]
                if ti.abs(old_velocity) > 1.0e-12:
                    force_change = (
                        self.internal_force[ix, iy][component]
                        - self.internal_force_old[ix, iy][component]
                    ) / self.mass_diagonal
                    ti.atomic_add(
                        self.damping_numerator[None],
                        -self.displacement[ix, iy][component] ** 2
                        * force_change
                        / (self.dt * old_velocity),
                    )
                ti.atomic_add(
                    self.damping_denominator[None],
                    self.displacement[ix, iy][component] ** 2,
                )

        coefficient = 0.0
        if self.damping_denominator[None] > 1.0e-12:
            quotient = (
                self.damping_numerator[None] / self.damping_denominator[None]
            )
            if quotient > 0.0:
                coefficient = 2.0 * ti.sqrt(quotient)
        if coefficient > 2.0:
            coefficient = 1.9
        self.damping[None] = coefficient

    @ti.kernel
    def _integrate(self, step: ti.i32):
        for ix, iy in self.displacement:
            total_force = self.internal_force[ix, iy] + self.body_force[ix, iy]
            if step == 0:
                self.velocity_half[ix, iy] = (
                    0.5 * self.dt * total_force / self.mass_diagonal
                )
            else:
                damping_dt = self.damping[None] * self.dt
                self.velocity_half[ix, iy] = (
                    (2.0 - damping_dt) * self.velocity_half_old[ix, iy]
                    + 2.0 * self.dt * total_force / self.mass_diagonal
                ) / (2.0 + damping_dt)
            self.velocity[ix, iy] = 0.5 * (
                self.velocity_half_old[ix, iy] + self.velocity_half[ix, iy]
            )
            self.displacement[ix, iy] += self.velocity_half[ix, iy] * self.dt
            self.velocity_half_old[ix, iy] = self.velocity_half[ix, iy]
            self.internal_force_old[ix, iy] = self.internal_force[ix, iy]

            # Essential boundary conditions constrain both displacement and
            # velocity, preventing hidden momentum at fixed material points.
            if iy == 0:
                self.displacement[ix, iy] = ti.Vector.zero(self.real, 2)
                self.velocity[ix, iy] = ti.Vector.zero(self.real, 2)
                self.velocity_half[ix, iy] = ti.Vector.zero(self.real, 2)
                self.velocity_half_old[ix, iy] = ti.Vector.zero(self.real, 2)

    def _refresh_mechanical_state(self) -> None:
        """Recompute kinematics, stress, and forces for the current displacement."""

        self._apply_boundary_data()
        self._update_current_coordinates()
        self._compute_deformation_gradient()
        self._compute_linear_elastic_stress()
        self._compute_correspondence_force()
        self._compute_stabilisation_force()
        self._sum_internal_force()

    def step(self) -> None:
        """Advance the ADR solution by one virtual-time step."""

        self._refresh_mechanical_state()
        self._update_adaptive_damping()
        self._integrate(self.completed_steps)
        self.completed_steps += 1

    def run(
        self,
        steps: int | None = None,
        callback: Callable[[int, "ElasticStabilisedPD"], None] | None = None,
    ) -> SimulationResult:
        """Run the requested number of ADR steps and return NumPy fields."""

        total = self.config.steps if steps is None else steps
        if total < 1:
            raise ValueError("steps must be positive")
        for _ in range(total):
            self.step()
            if callback is not None:
                callback(self.completed_steps, self)
        self._refresh_mechanical_state()
        return self.result()

    def result(self) -> SimulationResult:
        """Copy the current Taichi fields into a result object."""

        return SimulationResult(
            coordinates=self.coordinates.to_numpy(),
            displacement=self.displacement.to_numpy(),
            stress=self.stress.to_numpy(),
            internal_force=self.internal_force.to_numpy(),
            steps=self.completed_steps,
            damping=float(self.damping[None]),
        )


def initialise_taichi(config: SimulationConfig) -> None:
    """Initialise Taichi using the architecture and precision in ``config``."""

    architecture = ti.cpu if config.architecture == "cpu" else ti.gpu
    precision = ti.f64 if config.default_fp == "f64" else ti.f32
    ti.init(arch=architecture, default_fp=precision)
