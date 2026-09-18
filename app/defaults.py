"""Default campus energy data and OpenAPI examples."""

from __future__ import annotations

DEFAULT_CAMPUS_HOURS_DATA: list[dict[str, float | int]] = [
    {"hour": 0, "demand_kwh": 90.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 6.0},
    {"hour": 1, "demand_kwh": 85.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 6.0},
    {"hour": 2, "demand_kwh": 80.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 5.0},
    {"hour": 3, "demand_kwh": 80.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 5.0},
    {"hour": 4, "demand_kwh": 85.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 5.0},
    {"hour": 5, "demand_kwh": 95.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 6.0},
    {"hour": 6, "demand_kwh": 110.0, "solar_kwh": 5.0, "tariff_bdt_per_kwh": 8.0},
    {"hour": 7, "demand_kwh": 130.0, "solar_kwh": 20.0, "tariff_bdt_per_kwh": 10.0},
    {"hour": 8, "demand_kwh": 150.0, "solar_kwh": 50.0, "tariff_bdt_per_kwh": 12.0},
    {"hour": 9, "demand_kwh": 165.0, "solar_kwh": 90.0, "tariff_bdt_per_kwh": 14.0},
    {"hour": 10, "demand_kwh": 175.0, "solar_kwh": 130.0, "tariff_bdt_per_kwh": 16.0},
    {"hour": 11, "demand_kwh": 180.0, "solar_kwh": 160.0, "tariff_bdt_per_kwh": 16.0},
    {"hour": 12, "demand_kwh": 185.0, "solar_kwh": 180.0, "tariff_bdt_per_kwh": 15.0},
    {"hour": 13, "demand_kwh": 180.0, "solar_kwh": 170.0, "tariff_bdt_per_kwh": 14.0},
    {"hour": 14, "demand_kwh": 170.0, "solar_kwh": 140.0, "tariff_bdt_per_kwh": 13.0},
    {"hour": 15, "demand_kwh": 165.0, "solar_kwh": 90.0, "tariff_bdt_per_kwh": 14.0},
    {"hour": 16, "demand_kwh": 170.0, "solar_kwh": 45.0, "tariff_bdt_per_kwh": 18.0},
    {"hour": 17, "demand_kwh": 185.0, "solar_kwh": 10.0, "tariff_bdt_per_kwh": 22.0},
    {"hour": 18, "demand_kwh": 205.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 28.0},
    {"hour": 19, "demand_kwh": 215.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 30.0},
    {"hour": 20, "demand_kwh": 205.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 26.0},
    {"hour": 21, "demand_kwh": 175.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 18.0},
    {"hour": 22, "demand_kwh": 135.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 10.0},
    {"hour": 23, "demand_kwh": 105.0, "solar_kwh": 0.0, "tariff_bdt_per_kwh": 7.0},
]

DEFAULT_CAMPUS_BATTERY_DATA: dict[str, float] = {
    "capacity_kwh": 220.0,
    "initial_energy_kwh": 110.0,
    "minimum_energy_kwh": 40.0,
    "max_charge_kwh_per_hour": 50.0,
    "max_discharge_kwh_per_hour": 50.0,
}

SAMPLE_OPTIMIZE_REQUEST_EXAMPLE = {
    "scenario_id": "CAMPUS-DEMO-01",
    "operator_notes": [
        "Do not charge the battery between 6 PM and 9 PM."
    ],
    "hours": DEFAULT_CAMPUS_HOURS_DATA,
    "battery": DEFAULT_CAMPUS_BATTERY_DATA,
}
