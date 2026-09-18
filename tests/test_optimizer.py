"""Unit and reference-case tests for the LP optimizer and replay checker."""

import json
from pathlib import Path
import pytest

from app.constraints import compile_hourly_constraints
from app.optimizer import solve_energy_schedule
from app.replay import replay_schedule
from app.response import assemble_optimization_response
from app.schemas import OptimizeEnergyRequest
from tools.check_nvidia_model import find_sample_pack


@pytest.fixture(scope="module")
def sample_pack():
    root = Path(__file__).resolve().parents[1]
    pack_path = find_sample_pack(root)
    return json.loads(pack_path.read_text(encoding="utf-8-sig"))


def test_all_10_reference_cases_optimal_cost_and_replay(sample_pack):
    """Verify that all 10 sample cases with ground-truth directives produce

    the exact reference cost within 0.01 BDT tolerance and pass independent replay.
    """
    for case in sample_pack["cases"]:
        case_id = case["id"]
        expected_output = case["expected_output"]
        expected_cost = float(expected_output["total_cost_bdt"])

        # Validate input with schema
        req = OptimizeEnergyRequest.model_validate(case["input"])
        directives = expected_output["directive_interpretation"]

        # Compile constraints
        constraints = compile_hourly_constraints(req.hours, req.battery, directives)

        # Solve
        opt_res = solve_energy_schedule(constraints)

        # Assemble and recalculate response
        resp = assemble_optimization_response(req.scenario_id, req.hours, directives, opt_res)

        # Replay validation
        replay_schedule(req.hours, req.battery, directives, resp.hourly_plan)

        # Compare cost
        cost_diff = abs(resp.total_cost_bdt - expected_cost)
        assert cost_diff <= 0.01, (
            f"Case {case_id} cost mismatch: got {resp.total_cost_bdt:.2f} BDT, "
            f"expected {expected_cost:.2f} BDT (delta: {cost_diff:.4f} BDT)"
        )


def test_zero_solar_all_day_passes_replay():
    """Verify optimizer and replay when solar generation is 0.0 across all 24 hours."""
    from app.schemas import BatteryParameters, HourlyForecast

    hours = [
        HourlyForecast(
            hour=h,
            demand_kwh=80.0,
            solar_kwh=0.0,
            tariff_bdt_per_kwh=5.0 if h < 6 else (15.0 if 17 <= h <= 22 else 10.0),
        )
        for h in range(24)
    ]
    battery = BatteryParameters(
        capacity_kwh=200.0,
        initial_energy_kwh=100.0,
        minimum_energy_kwh=20.0,
        max_charge_kwh_per_hour=50.0,
        max_discharge_kwh_per_hour=50.0,
    )
    directives = []
    constraints = compile_hourly_constraints(hours, battery, directives)
    opt_res = solve_energy_schedule(constraints)
    resp = assemble_optimization_response("ZERO_SOLAR", hours, directives, opt_res)

    # Replay must pass without error
    replay_schedule(hours, battery, directives, resp.hourly_plan)
    assert resp.total_cost_bdt > 0.0
    assert abs(resp.hourly_plan[23].battery_energy_after_kwh - 100.0) < 1e-4


def test_battery_at_minimum_initial_energy():
    """Verify optimizer and replay when battery starts at minimum allowed reserve."""
    from app.schemas import BatteryParameters, HourlyForecast

    hours = [
        HourlyForecast(
            hour=h,
            demand_kwh=100.0,
            solar_kwh=60.0 if 9 <= h <= 15 else 0.0,
            tariff_bdt_per_kwh=4.0 if h < 8 else (12.0 if 16 <= h <= 21 else 8.0),
        )
        for h in range(24)
    ]
    battery = BatteryParameters(
        capacity_kwh=150.0,
        initial_energy_kwh=30.0,
        minimum_energy_kwh=30.0,
        max_charge_kwh_per_hour=40.0,
        max_discharge_kwh_per_hour=40.0,
    )
    directives = []
    constraints = compile_hourly_constraints(hours, battery, directives)
    opt_res = solve_energy_schedule(constraints)
    resp = assemble_optimization_response("MIN_INITIAL", hours, directives, opt_res)

    replay_schedule(hours, battery, directives, resp.hourly_plan)
    # Final state must restore to initial (30.0)
    assert abs(resp.hourly_plan[23].battery_energy_after_kwh - 30.0) < 1e-4


def test_zero_capacity_battery_solve_and_replay():
    """Verify optimizer and replay when battery capacity and all rates are 0.0."""
    from app.schemas import BatteryParameters, HourlyForecast

    hours = [
        HourlyForecast(
            hour=h,
            demand_kwh=50.0,
            solar_kwh=20.0 if 10 <= h <= 14 else 0.0,
            tariff_bdt_per_kwh=10.0,
        )
        for h in range(24)
    ]
    battery = BatteryParameters(
        capacity_kwh=0.0,
        initial_energy_kwh=0.0,
        minimum_energy_kwh=0.0,
        max_charge_kwh_per_hour=0.0,
        max_discharge_kwh_per_hour=0.0,
    )
    directives = []
    constraints = compile_hourly_constraints(hours, battery, directives)
    opt_res = solve_energy_schedule(constraints)
    resp = assemble_optimization_response("ZERO_BATTERY", hours, directives, opt_res)

    replay_schedule(hours, battery, directives, resp.hourly_plan)
    # All battery actions must be idle, 0 kwh
    for p in resp.hourly_plan:
        assert p.battery_action == "idle"
        assert p.battery_kwh == 0.0
        assert p.battery_energy_after_kwh == 0.0
