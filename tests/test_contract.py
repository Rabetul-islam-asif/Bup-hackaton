"""API contract and input validation tests."""

import copy
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.schemas import OptimizeEnergyRequest
from tools.check_nvidia_model import find_sample_pack

client = TestClient(app)


@pytest.fixture(scope="module")
def valid_payload():
    root = Path(__file__).resolve().parents[1]
    pack = json.loads(find_sample_pack(root).read_text(encoding="utf-8-sig"))
    return copy.deepcopy(pack["cases"][0]["input"])


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_malformed_json():
    response = client.post(
        "/optimize-energy",
        content="not valid json {{{",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


def test_missing_scenario_id(valid_payload):
    payload = copy.deepcopy(valid_payload)
    del payload["scenario_id"]
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_empty_scenario_id(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["scenario_id"] = "   "
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_invalid_note_count_zero(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["operator_notes"] = []
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_invalid_note_count_too_many(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["operator_notes"] = ["Note 1", "Note 2", "Note 3", "Note 4"]
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_empty_string_in_notes(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["operator_notes"] = ["Note 1", "   "]
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_missing_hour_in_24(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["hours"] = payload["hours"][:-1]  # 23 hours instead of 24
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_duplicate_hour(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["hours"][1]["hour"] = payload["hours"][0]["hour"]
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_hour_out_of_range(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["hours"][0]["hour"] = 24
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_boolean_in_numeric_field(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["hours"][0]["demand_kwh"] = True
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_negative_demand(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["hours"][0]["demand_kwh"] = -5.0
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_incoherent_battery_initial_greater_than_capacity(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["battery"]["initial_energy_kwh"] = payload["battery"]["capacity_kwh"] + 100
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_incoherent_battery_min_greater_than_initial(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["battery"]["minimum_energy_kwh"] = payload["battery"]["initial_energy_kwh"] + 50
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 400


def test_zero_capacity_battery_is_accepted(valid_payload):
    payload = copy.deepcopy(valid_payload)
    payload["battery"] = {
        "capacity_kwh": 0.0,
        "initial_energy_kwh": 0.0,
        "minimum_energy_kwh": 0.0,
        "max_charge_kwh_per_hour": 0.0,
        "max_discharge_kwh_per_hour": 0.0,
    }
    request = OptimizeEnergyRequest.model_validate(payload)
    assert request.battery.capacity_kwh == 0.0


def test_health_reports_unavailable_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_api_key", "")
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_quick_optimize_validation_rejects_empty():
    response = client.post("/quick-optimize", json={"operator_notes": []})
    assert response.status_code == 400


def test_quick_optimize_validation_rejects_too_many():
    response = client.post("/quick-optimize", json={"operator_notes": ["1", "2", "3", "4"]})
    assert response.status_code == 400


def test_quick_optimize_string_coercion():
    from app.schemas import QuickOptimizeRequest
    req = QuickOptimizeRequest.model_validate({"operator_notes": "Do not charge the battery between 6 PM and 9 PM."})
    assert len(req.operator_notes) == 1
    assert req.operator_notes[0] == "Do not charge the battery between 6 PM and 9 PM."


def test_openapi_schema_contains_examples():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    # Ensure OptimizeEnergyRequest schema includes examples
    req_schema = schema["components"]["schemas"]["OptimizeEnergyRequest"]
    assert "examples" in req_schema
    assert len(req_schema["examples"]) > 0
    assert "operator_notes" in req_schema["examples"][0]

