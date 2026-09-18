"""Linear programming optimizer for 24-hour campus energy scheduling using SciPy HiGHS."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.optimize import linprog

from app.constraints import CompiledConstraints

logger = logging.getLogger("gridwise.optimizer")

NUMERICAL_TOLERANCE = 1e-6


class OptimizationInfeasibleError(Exception):
    """Raised when the schedule is mathematically infeasible."""
    pass


@dataclass
class RawHourlyResult:
    hour: int
    grid_kwh: float
    solar_used_kwh: float
    battery_action: Literal["charge", "discharge", "idle"]
    battery_kwh: float
    battery_energy_after_kwh: float


@dataclass
class OptimizationResult:
    hourly_results: list[RawHourlyResult]
    total_cost_bdt: float
    total_grid_kwh: float
    peak_grid_kwh: float


def solve_energy_schedule(constraints: CompiledConstraints) -> OptimizationResult:
    """Solve the 24-hour linear program using SciPy HiGHS.

    Variables per hour h (0..23):
      G[h] = 4*h + 0 : Grid import (kWh)
      S[h] = 4*h + 1 : Solar used (kWh)
      B[h] = 4*h + 2 : Signed battery movement (kWh, + for charge, - for discharge)
      E[h] = 4*h + 3 : End-of-hour battery energy (kWh)
    Total variables: 96
    """
    n_vars = 24 * 4

    # Objective: minimize sum(tariff[h] * G[h])
    c = np.zeros(n_vars, dtype=np.float64)
    for h in range(24):
        c[4 * h + 0] = constraints.tariffs[h]

    # Bounds
    bounds: list[tuple[float | None, float | None]] = []
    for h in range(24):
        # G[h] >= 0, G[h] <= cap
        cap = None if np.isinf(constraints.grid_cap[h]) else float(constraints.grid_cap[h])
        bounds.append((0.0, cap))

        # 0 <= S[h] <= effective_solar[h]
        bounds.append((0.0, float(constraints.effective_solar[h])))

        # -max_discharge <= B[h] <= max_charge
        bounds.append((-float(constraints.max_discharge[h]), float(constraints.max_charge[h])))

        # min_reserve <= E[h] <= capacity
        bounds.append((float(constraints.min_reserve[h]), float(constraints.capacity)))

    # Equality constraints
    # 1. Demand balance (24 rows): G[h] + S[h] - B[h] = demand[h]
    # 2. Battery state transitions (24 rows):
    #    h=0: E[0] - B[0] = E_init
    #    h>0: E[h] - E[h-1] - B[h] = 0
    # 3. Neutrality equality (1 row): E[23] = E_init
    n_eq = 24 + 24 + 1
    A_eq = np.zeros((n_eq, n_vars), dtype=np.float64)
    b_eq = np.zeros(n_eq, dtype=np.float64)

    row_idx = 0

    # 1. Demand balance
    for h in range(24):
        A_eq[row_idx, 4 * h + 0] = 1.0   # G[h]
        A_eq[row_idx, 4 * h + 1] = 1.0   # S[h]
        A_eq[row_idx, 4 * h + 2] = -1.0  # -B[h]
        b_eq[row_idx] = constraints.demand[h]
        row_idx += 1

    # 2. Battery transitions
    # h = 0: E[0] - B[0] = E_initial
    A_eq[row_idx, 4 * 0 + 3] = 1.0   # E[0]
    A_eq[row_idx, 4 * 0 + 2] = -1.0  # -B[0]
    b_eq[row_idx] = constraints.initial_energy
    row_idx += 1

    # h = 1..23: E[h] - E[h-1] - B[h] = 0
    for h in range(1, 24):
        A_eq[row_idx, 4 * h + 3] = 1.0        # E[h]
        A_eq[row_idx, 4 * (h - 1) + 3] = -1.0  # -E[h-1]
        A_eq[row_idx, 4 * h + 2] = -1.0       # -B[h]
        b_eq[row_idx] = 0.0
        row_idx += 1

    # 3. Neutrality at hour 23
    A_eq[row_idx, 4 * 23 + 3] = 1.0  # E[23]
    b_eq[row_idx] = constraints.initial_energy
    row_idx += 1

    # Solve with HiGHS
    res = linprog(
        c=c,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
        options={"presolve": True},
    )

    if not res.success:
        logger.error("Linear programming failed: status=%d, message=%s", res.status, res.message)
        raise OptimizationInfeasibleError(f"Optimization failed: {res.message} (status {res.status})")

    x = res.x
    hourly_results: list[RawHourlyResult] = []
    total_grid = 0.0
    total_cost = 0.0
    peak_grid = 0.0

    for h in range(24):
        g = float(x[4 * h + 0])
        s = float(x[4 * h + 1])
        b = float(x[4 * h + 2])
        e = float(x[4 * h + 3])

        # Clean numerical residuals
        if abs(g) < NUMERICAL_TOLERANCE:
            g = 0.0
        if abs(s) < NUMERICAL_TOLERANCE:
            s = 0.0

        if b > NUMERICAL_TOLERANCE:
            action: Literal["charge", "discharge", "idle"] = "charge"
            b_mag = b
        elif b < -NUMERICAL_TOLERANCE:
            action = "discharge"
            b_mag = -b
        else:
            action = "idle"
            b_mag = 0.0

        total_grid += g
        total_cost += g * constraints.tariffs[h]
        if g > peak_grid:
            peak_grid = g

        hourly_results.append(
            RawHourlyResult(
                hour=h,
                grid_kwh=g,
                solar_used_kwh=s,
                battery_action=action,
                battery_kwh=b_mag,
                battery_energy_after_kwh=e,
            )
        )

    return OptimizationResult(
        hourly_results=hourly_results,
        total_cost_bdt=total_cost,
        total_grid_kwh=total_grid,
        peak_grid_kwh=peak_grid,
    )
