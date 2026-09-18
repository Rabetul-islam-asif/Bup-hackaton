"""Independent replay validator for 24-hour campus energy schedules."""

from __future__ import annotations

import math
from typing import Any

from app.schemas import BatteryParameters, HourlyForecast, HourlyPlan

TOLERANCE_KWH = 0.01


class ReplayValidationError(ValueError):
    """Raised when an hourly schedule fails independent replay validation."""
    pass


def replay_schedule(
    hours: list[HourlyForecast],
    battery: BatteryParameters,
    validated_directives: list[dict[str, Any]],
    hourly_plan: list[HourlyPlan],
    tolerance: float = TOLERANCE_KWH,
) -> None:
    """Independently verify all physical, operational, and directive constraints.

    Checks:
    - 24 ordered hours 0..23
    - Exact energy balance per hour: grid + solar_used + discharge = demand + charge
    - Battery continuity: E[h] = E[h-1] + charge - discharge
    - Battery capacity and active minimum reserve bounds
    - Battery charge/discharge rate bounds and directive windows
    - Solar utilization does not exceed effective solar
    - Grid import does not exceed active grid caps
    - Terminal battery neutrality: E[23] == E_initial
    """
    if len(hourly_plan) != 24:
        raise ReplayValidationError(f"hourly_plan must contain exactly 24 entries, got {len(hourly_plan)}")

    sorted_forecasts = sorted(hours, key=lambda x: x.hour)
    sorted_plan = sorted(hourly_plan, key=lambda x: x.hour)

    for expected_h, plan_entry in enumerate(sorted_plan):
        if plan_entry.hour != expected_h:
            raise ReplayValidationError(f"hourly_plan hour mismatch: expected {expected_h}, got {plan_entry.hour}")

    # Derive directive constraints independently
    effective_solar = [f.solar_kwh for f in sorted_forecasts]
    min_reserve = [battery.minimum_energy_kwh] * 24
    grid_cap = [float("inf")] * 24
    no_charge_hours: set[int] = set()
    no_discharge_hours: set[int] = set()

    for directive in validated_directives:
        if not directive.get("applies"):
            continue
        kind = directive.get("directive_type")
        adj = directive.get("structured_adjustment") or {}
        d_hours = adj.get("hours", [])

        if kind == "solar_reduction":
            factor = float(adj["factor"])
            for h in d_hours:
                effective_solar[h] = min(effective_solar[h], sorted_forecasts[h].solar_kwh * factor)
        elif kind == "minimum_battery_reserve":
            reserve = float(adj["minimum_energy_kwh"])
            for h in d_hours:
                min_reserve[h] = max(min_reserve[h], reserve)
        elif kind == "max_grid_window":
            cap = float(adj["max_grid_kwh"])
            for h in d_hours:
                grid_cap[h] = min(grid_cap[h], cap)
        elif kind == "no_charge_window":
            no_charge_hours.update(d_hours)
        elif kind == "no_discharge_window":
            no_discharge_hours.update(d_hours)

    prev_energy = battery.initial_energy_kwh

    for h in range(24):
        fc = sorted_forecasts[h]
        p = sorted_plan[h]

        # 1. Finite and non-negative
        for field, val in [
            ("grid_kwh", p.grid_kwh),
            ("solar_used_kwh", p.solar_used_kwh),
            ("battery_kwh", p.battery_kwh),
            ("battery_energy_after_kwh", p.battery_energy_after_kwh),
        ]:
            if not math.isfinite(val) or val < -1e-9:
                raise ReplayValidationError(f"hour {h}: {field} must be finite and non-negative, got {val}")

        # 2. Battery action consistency & limits
        if p.battery_action == "idle":
            if abs(p.battery_kwh) > tolerance:
                raise ReplayValidationError(f"hour {h}: battery_kwh must be 0 for idle action, got {p.battery_kwh}")
            signed_b = 0.0
        elif p.battery_action == "charge":
            if h in no_charge_hours:
                raise ReplayValidationError(f"hour {h}: charging attempted during no_charge_window")
            if p.battery_kwh > battery.max_charge_kwh_per_hour + tolerance:
                raise ReplayValidationError(f"hour {h}: charge {p.battery_kwh} exceeds max charge {battery.max_charge_kwh_per_hour}")
            signed_b = p.battery_kwh
        elif p.battery_action == "discharge":
            if h in no_discharge_hours:
                raise ReplayValidationError(f"hour {h}: discharging attempted during no_discharge_window")
            if p.battery_kwh > battery.max_discharge_kwh_per_hour + tolerance:
                raise ReplayValidationError(f"hour {h}: discharge {p.battery_kwh} exceeds max discharge {battery.max_discharge_kwh_per_hour}")
            signed_b = -p.battery_kwh
        else:
            raise ReplayValidationError(f"hour {h}: invalid battery_action {p.battery_action}")

        # 3. Energy continuity
        expected_energy = prev_energy + signed_b
        if abs(p.battery_energy_after_kwh - expected_energy) > tolerance:
            raise ReplayValidationError(
                f"hour {h}: battery continuity broken: expected {expected_energy:.4f}, got {p.battery_energy_after_kwh:.4f}"
            )

        # 4. Capacity & reserve limits
        if p.battery_energy_after_kwh > battery.capacity_kwh + tolerance:
            raise ReplayValidationError(
                f"hour {h}: battery energy {p.battery_energy_after_kwh} exceeds capacity {battery.capacity_kwh}"
            )
        if p.battery_energy_after_kwh < min_reserve[h] - tolerance:
            raise ReplayValidationError(
                f"hour {h}: battery energy {p.battery_energy_after_kwh} below minimum reserve {min_reserve[h]}"
            )

        # 5. Solar limits
        if p.solar_used_kwh > effective_solar[h] + tolerance:
            raise ReplayValidationError(
                f"hour {h}: solar used {p.solar_used_kwh} exceeds available solar {effective_solar[h]}"
            )

        # 6. Grid cap limits
        if p.grid_kwh > grid_cap[h] + tolerance:
            raise ReplayValidationError(
                f"hour {h}: grid import {p.grid_kwh} exceeds grid cap {grid_cap[h]}"
            )

        # 7. Demand balance: grid + solar_used - signed_b == demand
        balance_residual = abs((p.grid_kwh + p.solar_used_kwh - signed_b) - fc.demand_kwh)
        if balance_residual > tolerance:
            raise ReplayValidationError(
                f"hour {h}: demand balance violation (residual={balance_residual:.4f}): "
                f"grid={p.grid_kwh}, solar={p.solar_used_kwh}, battery_movement={signed_b}, demand={fc.demand_kwh}"
            )

        prev_energy = p.battery_energy_after_kwh

    # 8. Terminal neutrality
    final_delta = abs(prev_energy - battery.initial_energy_kwh)
    if final_delta > tolerance:
        raise ReplayValidationError(
            f"Terminal battery state neutrality violated: final {prev_energy:.4f} != initial {battery.initial_energy_kwh:.4f} (delta={final_delta:.4f})"
        )
