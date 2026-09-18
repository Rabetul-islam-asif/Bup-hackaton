"""Failure injection and error handling tests."""

from unittest.mock import patch
import json
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


def _valid_no_op_content() -> str:
    return json.dumps({
        "directive_interpretation": [{
            "note_index": 0,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": "No scheduling instruction.",
        }]
    })


def test_interpreter_retries_one_transient_provider_failure():
    instance = LLMInterpreter(api_key="test")
    with patch.object(
        instance,
        "_call_api",
        side_effect=[LLMProviderError("temporary", retryable=True), _valid_no_op_content()],
    ) as call:
        result = instance.interpret("RETRY", ["Routine inspection."], 100.0, timeout=5.0)
    assert result[0]["directive_type"] == "no_op"
    assert call.call_count == 2


def test_interpreter_repairs_invalid_json_once():
    instance = LLMInterpreter(api_key="test")
    with patch.object(
        instance,
        "_call_api",
        side_effect=["not json", _valid_no_op_content()],
    ) as call:
        result = instance.interpret("REPAIR", ["Routine inspection."], 100.0, timeout=5.0)
    assert result[0]["directive_type"] == "no_op"
    assert call.call_count == 2


def test_interpreter_does_not_retry_permanent_provider_failure():
    instance = LLMInterpreter(api_key="test")
    with patch.object(
        instance,
        "_call_api",
        side_effect=LLMProviderError("bad request", retryable=False),
    ) as call:
        with pytest.raises(LLMProviderError, match="bad request"):
            instance.interpret("NO-RETRY", ["Routine inspection."], 100.0, timeout=5.0)
    assert call.call_count == 1


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


def test_api_handles_optimization_infeasible_sanitized():
    with patch("app.main.solve_energy_schedule", side_effect=OptimizationInfeasibleError("No feasible basis")):
        payload = {
            "scenario_id": "ERR-03",
            "operator_notes": ["Routine inspection completed."],
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
        with patch("app.main.interpreter.interpret", return_value=[{"note_index": 0, "applies": False, "directive_type": "no_op", "structured_adjustment": None, "explanation": "no op"}]):
            response = client.post("/optimize-energy", json=payload)
            assert response.status_code == 500
            assert response.json()["detail"] == "Energy schedule optimization infeasible"


def test_api_handles_replay_validation_failure_sanitized():
    from app.replay import ReplayValidationError

    with patch("app.main.replay_schedule", side_effect=ReplayValidationError("Balance violation")):
        payload = {
            "scenario_id": "ERR-04",
            "operator_notes": ["Routine inspection completed."],
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
        with patch("app.main.interpreter.interpret", return_value=[{"note_index": 0, "applies": False, "directive_type": "no_op", "structured_adjustment": None, "explanation": "no op"}]):
            response = client.post("/optimize-energy", json=payload)
            assert response.status_code == 500
            assert response.json()["detail"] == "Internal schedule verification failed"
