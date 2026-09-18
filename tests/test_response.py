"""Unit test for exact aggregate recalculation from serialized hourly plan."""

from app.optimizer import OptimizationResult, RawHourlyResult
from app.response import assemble_optimization_response
from app.schemas import HourlyForecast


def test_totals_match_serialized_hourly_plan_exactly():
    # Construct scenario with fractional numbers where raw vs rounded sums would drift
    hours = [
        HourlyForecast(hour=h, demand_kwh=100.0, solar_kwh=0.0, tariff_bdt_per_kwh=9.9999)
        for h in range(24)
    ]
    raw_results = [
        RawHourlyResult(
            hour=h,
            grid_kwh=100.00000049,  # rounds to 100.000000 at 6 decimals
            solar_used_kwh=0.0,
            battery_action="idle",
            battery_kwh=0.0,
            battery_energy_after_kwh=50.0,
        )
        for h in range(24)
    ]
    opt_res = OptimizationResult(
        hourly_results=raw_results,
        total_cost_bdt=0.0,
        total_grid_kwh=0.0,
        peak_grid_kwh=0.0,
    )
    resp = assemble_optimization_response("TEST_ROUND", hours, [], opt_res)

    # Calculate directly from the returned plan entries
    plan_grid = sum(p.grid_kwh for p in resp.hourly_plan)
    plan_cost = sum(p.grid_kwh * hours[p.hour].tariff_bdt_per_kwh for p in resp.hourly_plan)
    plan_peak = max(p.grid_kwh for p in resp.hourly_plan)

    assert abs(resp.total_grid_kwh - round(plan_grid, 4)) < 1e-6
    assert abs(resp.total_cost_bdt - round(plan_cost, 2)) < 1e-6
    assert abs(resp.peak_grid_kwh - round(plan_peak, 4)) < 1e-6
