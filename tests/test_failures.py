"""Failure injection and error handling tests."""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.guardrails import DirectiveValidationError
from app.interpreter import LLMInterpreter, LLMProviderError
from app.main import app
from app.optimizer import OptimizationInfeasibleError, solve_energy_schedule
from app.constraints import CompiledConstraints

client = TestClient(app)


def test_missing_api_key_raises_provider_error():
    dummy_interpreter = LLMInterpreter(api_key="")
    with pytest.raises(LLMProviderError, match="NVIDIA_API_KEY is not configured"):
        dummy_interpreter.interpret("TEST", ["Some note"], 100.0)


def test_solver_infeasible_scenario_raises_error():
    # Construct impossible constraints: demand 1000, 0 solar, 0 grid cap, 0 battery movement
    infeasible_constraints = CompiledConstraints(
        demand=[1000.0] * 24,
        tariffs=[10.0] * 24,
        effective_solar=[0.0] * 24,
        min_reserve=[0.0] * 24,
        grid_cap=[0.0] * 24,  # zero grid allowed
        max_charge=[0.0] * 24,
        max_discharge=[0.0] * 24,  # zero battery discharge
        capacity=100.0,
        initial_energy=50.0,
    )
    with pytest.raises(OptimizationInfeasibleError):
        solve_energy_schedule(infeasible_constraints)


def test_llm_failure_returns_sanitized_500():
    with patch("app.main.interpreter.interpret", side_effect=LLMProviderError("Provider timeout")):
        # Valid payload
        payload = {
            "scenario_id": "ERR-01",
            "operator_notes": ["Wash panels noon to 2 PM"],
            "hours": [
                {"hour": h, "demand_kwh": 50.0, "solar_kwh": 10.0, "tariff_bdt_per_kwh": 10.0}
                for h in range(24)
            ],
            "battery": {
                "capacity_kwh": 100.0,
                "initial_energy_kwh": 50.0,
                "minimum_energy_kwh": 10.0,
                "max_charge_kwh_per_hour": 25.0,
                "max_discharge_kwh_per_hour": 25.0,
            },
        }
        response = client.post("/optimize-energy", json=payload)
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        # Ensure no secrets or trace leak
        assert "NVIDIA" not in str(data)
        assert "key" not in str(data).lower()


def test_guardrail_failure_returns_sanitized_500():
    with patch("app.main.interpreter.interpret", side_effect=DirectiveValidationError("Invalid directive")):
        payload = {
            "scenario_id": "ERR-02",
            "operator_notes": ["Wash panels noon to 2 PM"],
            "hours": [
                {"hour": h, "demand_kwh": 50.0, "solar_kwh": 10.0, "tariff_bdt_per_kwh": 10.0}
                for h in range(24)
            ],
            "battery": {
                "capacity_kwh": 100.0,
                "initial_energy_kwh": 50.0,
                "minimum_energy_kwh": 10.0,
                "max_charge_kwh_per_hour": 25.0,
                "max_discharge_kwh_per_hour": 25.0,
            },
        }
        response = client.post("/optimize-energy", json=payload)
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Failed to extract valid directives from notes"
