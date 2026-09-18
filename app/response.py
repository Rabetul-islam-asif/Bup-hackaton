"""Response assembly and deterministic aggregate calculation for GridWise."""

from __future__ import annotations

from typing import Any

from app.optimizer import OptimizationResult
from app.schemas import (
    DirectiveInterpretation,
    HourlyForecast,
    HourlyPlan,
    OptimizeEnergyResponse,
)


def build_plan_summary(
    hourly_plan: list[HourlyPlan],
    validated_directives: list[dict[str, Any]],
    total_cost_bdt: float,
    total_grid_kwh: float,
    peak_grid_kwh: float,
) -> str:
    """Generate a concise, factual summary of the optimal 24-hour dispatch."""
    charge_hours = sum(1 for p in hourly_plan if p.battery_action == "charge")
    discharge_hours = sum(1 for p in hourly_plan if p.battery_action == "discharge")
    total_solar_used = sum(p.solar_used_kwh for p in hourly_plan)
    total_charge_kwh = sum(p.battery_kwh for p in hourly_plan if p.battery_action == "charge")
    total_discharge_kwh = sum(p.battery_kwh for p in hourly_plan if p.battery_action == "discharge")

    active_directives = [d["directive_type"] for d in validated_directives if d.get("applies")]

    parts = [
        f"24-hour cost-optimized schedule achieved at {total_cost_bdt:,.2f} BDT total electricity cost.",
        f"Grid import totals {total_grid_kwh:,.2f} kWh with peak demand of {peak_grid_kwh:,.2f} kWh.",
        f"Solar self-consumption supplied {total_solar_used:,.2f} kWh.",
        f"Battery operated across {charge_hours} charge hours ({total_charge_kwh:,.1f} kWh) and {discharge_hours} discharge hours ({total_discharge_kwh:,.1f} kWh), returning to initial state.",
    ]

    if active_directives:
        unique_active = sorted(set(active_directives))
        parts.append(f"Successfully enforced {len(active_directives)} active directive(s): {', '.join(unique_active)}.")

    return " ".join(parts)


def assemble_optimization_response(
    scenario_id: str,
    hours: list[HourlyForecast],
    validated_directives: list[dict[str, Any]],
    opt_result: OptimizationResult,
) -> OptimizeEnergyResponse:
    """Serialize hourly plans, recalculate exact aggregates, and build final response."""
    sorted_forecasts = sorted(hours, key=lambda x: x.hour)

    hourly_plan: list[HourlyPlan] = []
    recalculated_grid = 0.0
    recalculated_cost = 0.0
    peak_grid = 0.0

    for raw in opt_result.hourly_results:
        h = raw.hour
        tariff = sorted_forecasts[h].tariff_bdt_per_kwh
        g = raw.grid_kwh

        recalculated_grid += g
        recalculated_cost += g * tariff
        if g > peak_grid:
            peak_grid = g

        plan_entry = HourlyPlan(
            hour=h,
            grid_kwh=round(g, 6),
            solar_used_kwh=round(raw.solar_used_kwh, 6),
            battery_action=raw.battery_action,
            battery_kwh=round(raw.battery_kwh, 6),
            battery_energy_after_kwh=round(raw.battery_energy_after_kwh, 6),
        )
        hourly_plan.append(plan_entry)

    directive_objects = [
        DirectiveInterpretation(
            note_index=d["note_index"],
            applies=d["applies"],
            directive_type=d["directive_type"],
            structured_adjustment=d["structured_adjustment"],
            explanation=d["explanation"],
        )
        for d in validated_directives
    ]

    summary = build_plan_summary(
        hourly_plan=hourly_plan,
        validated_directives=validated_directives,
        total_cost_bdt=recalculated_cost,
        total_grid_kwh=recalculated_grid,
        peak_grid_kwh=peak_grid,
    )

    return OptimizeEnergyResponse(
        scenario_id=scenario_id,
        directive_interpretation=directive_objects,
        hourly_plan=hourly_plan,
        total_grid_kwh=round(recalculated_grid, 4),
        total_cost_bdt=round(recalculated_cost, 2),
        peak_grid_kwh=round(peak_grid, 4),
        plan_summary=summary,
    )
