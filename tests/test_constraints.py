"""Unit tests for constraint compilation from directives."""

import math
from app.constraints import compile_hourly_constraints
from app.schemas import BatteryParameters, HourlyForecast


def make_sample_forecasts():
    return [
        HourlyForecast(
            hour=h,
            demand_kwh=100.0,
            solar_kwh=50.0 if 8 <= h <= 16 else 0.0,
            tariff_bdt_per_kwh=10.0,
        )
        for h in range(24)
    ]


def make_sample_battery():
    return BatteryParameters(
        capacity_kwh=200.0,
        initial_energy_kwh=100.0,
        minimum_energy_kwh=20.0,
        max_charge_kwh_per_hour=50.0,
        max_discharge_kwh_per_hour=50.0,
    )


def test_no_directives_returns_base_constraints():
    hours = make_sample_forecasts()
    battery = make_sample_battery()
    c = compile_hourly_constraints(hours, battery, [])

    assert c.effective_solar[12] == 50.0
    assert c.min_reserve[12] == 20.0
    assert math.isinf(c.grid_cap[12])
    assert c.max_charge[12] == 50.0
    assert c.max_discharge[12] == 50.0


def test_solar_reduction_applied_to_target_hours_only():
    hours = make_sample_forecasts()
    battery = make_sample_battery()
    directives = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12, 13], "factor": 0.5},
            "explanation": "Solar cut by half",
        }
    ]
    c = compile_hourly_constraints(hours, battery, directives)

    assert c.effective_solar[12] == 25.0
    assert c.effective_solar[13] == 25.0
    assert c.effective_solar[11] == 50.0  # untouched
    assert c.effective_solar[14] == 50.0  # untouched


def test_minimum_reserve_and_overlapping_reserves():
    hours = make_sample_forecasts()
    battery = make_sample_battery()
    directives = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [18, 19, 20], "minimum_energy_kwh": 60.0},
            "explanation": "First reserve",
        },
        {
            "note_index": 1,
            "applies": True,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [19, 20, 21], "minimum_energy_kwh": 80.0},
            "explanation": "Second higher reserve",
        },
    ]
    c = compile_hourly_constraints(hours, battery, directives)

    assert c.min_reserve[18] == 60.0
    assert c.min_reserve[19] == 80.0  # max(60, 80)
    assert c.min_reserve[20] == 80.0  # max(60, 80)
    assert c.min_reserve[21] == 80.0
    assert c.min_reserve[22] == 20.0  # base reserve


def test_no_charge_and_discharge_windows():
    hours = make_sample_forecasts()
    battery = make_sample_battery()
    directives = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [10, 11]},
            "explanation": "No charge",
        },
        {
            "note_index": 1,
            "applies": True,
            "directive_type": "no_discharge_window",
            "structured_adjustment": {"hours": [11, 12]},
            "explanation": "No discharge",
        },
    ]
    c = compile_hourly_constraints(hours, battery, directives)

    # Hour 10: no charge
    assert c.max_charge[10] == 0.0
    assert c.max_discharge[10] == 50.0

    # Hour 11: both no charge and no discharge -> battery must be idle
    assert c.max_charge[11] == 0.0
    assert c.max_discharge[11] == 0.0

    # Hour 12: no discharge
    assert c.max_charge[12] == 50.0
    assert c.max_discharge[12] == 0.0


def test_grid_cap_window():
    hours = make_sample_forecasts()
    battery = make_sample_battery()
    directives = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": [14, 15], "max_grid_kwh": 30.0},
            "explanation": "Grid cap",
        }
    ]
    c = compile_hourly_constraints(hours, battery, directives)

    assert c.grid_cap[14] == 30.0
    assert c.grid_cap[15] == 30.0
    assert math.isinf(c.grid_cap[13])
