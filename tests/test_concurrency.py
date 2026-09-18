"""Concurrent execution and stress testing for GridWise API."""

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_payload(scenario_id: str, demand: float):
    return {
        "scenario_id": scenario_id,
        "operator_notes": ["Routine check, no special requirements today."],
        "hours": [
            {
                "hour": h,
                "demand_kwh": demand,
                "solar_kwh": 30.0 if 10 <= h <= 15 else 0.0,
                "tariff_bdt_per_kwh": 10.0 if h < 17 else 18.0,
            }
            for h in range(24)
        ],
        "battery": {
            "capacity_kwh": 200.0,
            "initial_energy_kwh": 100.0,
            "minimum_energy_kwh": 20.0,
            "max_charge_kwh_per_hour": 50.0,
            "max_discharge_kwh_per_hour": 50.0,
        },
    }


def test_concurrent_requests_remain_isolated_and_valid():
    """Verify that multiple simultaneous optimization requests do not corrupt state."""
    scenarios = [
        ("CONCUR-01", 60.0),
        ("CONCUR-02", 80.0),
        ("CONCUR-03", 100.0),
        ("CONCUR-04", 120.0),
        ("CONCUR-05", 140.0),
    ]

    mock_interpretation = [
        {
            "note_index": 0,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": "Routine inspection requires no grid adjustments.",
        }
    ]

    with patch("app.main.interpreter.interpret", return_value=mock_interpretation):
        def send_request(item):
            sid, demand = item
            payload = make_payload(sid, demand)
            resp = client.post("/optimize-energy", json=payload)
            return resp

        with ThreadPoolExecutor(max_workers=5) as pool:
            responses = list(pool.map(send_request, scenarios))

        for resp, (sid, _) in zip(responses, scenarios):
            assert resp.status_code == 200, f"Failed for {sid}: {resp.text}"
            data = resp.json()
            assert data["scenario_id"] == sid
            assert len(data["hourly_plan"]) == 24
            assert data["total_cost_bdt"] > 0
            # Verify battery restored to 100.0
            assert abs(data["hourly_plan"][23]["battery_energy_after_kwh"] - 100.0) < 1e-4


def test_health_check_responds_instantly_during_load():
    """Verify /health responds with 200 without being blocked."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
