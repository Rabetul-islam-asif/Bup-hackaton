"""Unit tests for independent schedule replay validator and error detection."""

import copy
import pytest

from app.constraints import compile_hourly_constraints
from app.optimizer import solve_energy_schedule
from app.replay import ReplayValidationError, replay_schedule
from app.response import assemble_optimization_response
from app.schemas import BatteryParameters, HourlyForecast, HourlyPlan


def make_valid_schedule():
    hours = [
        HourlyForecast(
            hour=h,
            demand_kwh=100.0,
            solar_kwh=60.0 if 10 <= h <= 15 else 0.0,
            tariff_bdt_per_kwh=15.0 if 17 <= h <= 21 else 5.0,
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
    directives = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [17, 18, 19]},
            "explanation": "No charging during peak.",
        }
    ]
    constraints = compile_hourly_constraints(hours, battery, directives)
    opt_res = solve_energy_schedule(constraints)
    resp = assemble_optimization_response("TEST-01", hours, directives, opt_res)
    return hours, battery, directives, resp.hourly_plan


def test_valid_schedule_passes_replay():
    hours, battery, directives, plan = make_valid_schedule()
    # Should not raise
    replay_schedule(hours, battery, directives, plan)


def test_replay_rejects_energy_balance_corruption():
    hours, battery, directives, plan = make_valid_schedule()
    corrupted_plan = copy.deepcopy(plan)
    # Tamper with hour 5 grid import
    corrupted_plan[5].grid_kwh += 10.0
    with pytest.raises(ReplayValidationError, match="demand balance violation"):
        replay_schedule(hours, battery, directives, corrupted_plan)


def test_replay_rejects_battery_continuity_corruption():
    hours, battery, directives, plan = make_valid_schedule()
    corrupted_plan = copy.deepcopy(plan)
    # Tamper with hour 4 energy state
    corrupted_plan[4].battery_energy_after_kwh += 15.0
    with pytest.raises(ReplayValidationError, match="battery continuity broken"):
        replay_schedule(hours, battery, directives, corrupted_plan)


def test_replay_rejects_idle_with_nonzero_kwh():
    hours, battery, directives, plan = make_valid_schedule()
    corrupted_plan = copy.deepcopy(plan)
    for p in corrupted_plan:
        if p.battery_action == "idle":
            p.battery_kwh = 5.0
            break
    with pytest.raises(ReplayValidationError, match="battery_kwh must be 0 for idle"):
        replay_schedule(hours, battery, directives, corrupted_plan)


def test_replay_rejects_charge_in_forbidden_window():
    hours, battery, directives, plan = make_valid_schedule()
    corrupted_plan = copy.deepcopy(plan)
    # Force charge in hour 17 (no_charge_window)
    corrupted_plan[17].battery_action = "charge"
    corrupted_plan[17].battery_kwh = 10.0
    with pytest.raises(ReplayValidationError, match="no_charge_window"):
        replay_schedule(hours, battery, directives, corrupted_plan)


def test_replay_rejects_solar_excess():
    hours, battery, directives, plan = make_valid_schedule()
    corrupted_plan = copy.deepcopy(plan)
    corrupted_plan[12].solar_used_kwh += 50.0  # exceeds available solar
    with pytest.raises(ReplayValidationError, match="exceeds available solar"):
        replay_schedule(hours, battery, directives, corrupted_plan)


def test_replay_rejects_terminal_neutrality_violation():
    hours, battery, directives, plan = make_valid_schedule()
    # Change initial battery energy so that continuity holds throughout,
    # but the final hour does not equal the initial state
    bad_battery = copy.deepcopy(battery)
    bad_battery.initial_energy_kwh += 10.0
    # Also adjust hour 0 demand/balance to keep hour 0 continuous with new initial_energy
    with pytest.raises(ReplayValidationError):
        replay_schedule(hours, bad_battery, directives, plan)

