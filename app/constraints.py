"""Compile effective hourly constraints from base scenario and validated directives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas import BatteryParameters, HourlyForecast


@dataclass(frozen=True)
class CompiledConstraints:
    """Compiled effective bounds for the 24-hour horizon."""
    demand: list[float]
    tariffs: list[float]
    effective_solar: list[float]
    min_reserve: list[float]
    grid_cap: list[float]  # math.inf indicates no cap
    max_charge: list[float]
    max_discharge: list[float]
    capacity: float
    initial_energy: float


def compile_hourly_constraints(
    hours: list[HourlyForecast],
    battery: BatteryParameters,
    validated_directives: list[dict[str, Any]],
) -> CompiledConstraints:
    """Compile derived constraints without mutating input data.

    Preserves original demand, solar, tariffs, and battery parameters while
    deriving:
    - effective_solar[h]
    - min_reserve[h]
    - grid_cap[h]
    - max_charge[h]
    - max_discharge[h]
    """
    sorted_hours = sorted(hours, key=lambda x: x.hour)

    demand = [h.demand_kwh for h in sorted_hours]
    tariffs = [h.tariff_bdt_per_kwh for h in sorted_hours]
    effective_solar = [h.solar_kwh for h in sorted_hours]

    min_reserve = [battery.minimum_energy_kwh] * 24
    grid_cap = [float("inf")] * 24
    max_charge = [battery.max_charge_kwh_per_hour] * 24
    max_discharge = [battery.max_discharge_kwh_per_hour] * 24

    for directive in validated_directives:
        if not directive.get("applies"):
            continue

        kind = directive.get("directive_type")
        adj = directive.get("structured_adjustment")
        if not adj or "hours" not in adj:
            continue

        target_hours = adj["hours"]

        if kind == "solar_reduction":
            factor = float(adj["factor"])
            for h in target_hours:
                # If multiple solar reductions target the same hour, take the most restrictive
                effective_solar[h] = min(effective_solar[h], sorted_hours[h].solar_kwh * factor)

        elif kind == "minimum_battery_reserve":
            reserve = float(adj["minimum_energy_kwh"])
            for h in target_hours:
                min_reserve[h] = max(min_reserve[h], reserve)

        elif kind == "max_grid_window":
            cap = float(adj["max_grid_kwh"])
            for h in target_hours:
                grid_cap[h] = min(grid_cap[h], cap)

        elif kind == "no_charge_window":
            for h in target_hours:
                max_charge[h] = 0.0

        elif kind == "no_discharge_window":
            for h in target_hours:
                max_discharge[h] = 0.0

    return CompiledConstraints(
        demand=demand,
        tariffs=tariffs,
        effective_solar=effective_solar,
        min_reserve=min_reserve,
        grid_cap=grid_cap,
        max_charge=max_charge,
        max_discharge=max_discharge,
        capacity=battery.capacity_kwh,
        initial_energy=battery.initial_energy_kwh,
    )
