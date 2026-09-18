"""End-to-end integration tests for the GridWise FastAPI service."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tools.check_nvidia_model import find_sample_pack

client = TestClient(app)


@pytest.fixture(scope="module")
def sample_pack():
    root = Path(__file__).resolve().parents[1]
    return json.loads(find_sample_pack(root).read_text(encoding="utf-8-sig"))


def test_e2e_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.live
def test_e2e_optimize_sample_01(sample_pack):
    case = sample_pack["cases"][0]
    payload = case["input"]
    expected_cost = float(case["expected_output"]["total_cost_bdt"])

    resp = client.post("/optimize-energy", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    data = resp.json()

    # 1. Check top-level keys
    required_keys = {
        "scenario_id",
        "directive_interpretation",
        "hourly_plan",
        "total_grid_kwh",
        "total_cost_bdt",
        "peak_grid_kwh",
        "plan_summary",
    }
    assert set(data.keys()) == required_keys

    # 2. Check echo of scenario_id
    assert data["scenario_id"] == payload["scenario_id"]

    # 3. Check directive count
    assert len(data["directive_interpretation"]) == len(payload["operator_notes"])

    # 4. Check hourly plan length and ordering
    assert len(data["hourly_plan"]) == 24
    for h, p in enumerate(data["hourly_plan"]):
        assert p["hour"] == h
        assert p["battery_action"] in ("charge", "discharge", "idle")
        if p["battery_action"] == "idle":
            assert p["battery_kwh"] == 0.0

    # 5. Check cost delta against reference within 0.01 BDT
    cost_delta = abs(data["total_cost_bdt"] - expected_cost)
    assert cost_delta <= 0.01, f"Cost delta {cost_delta:.4f} exceeds tolerance 0.01 BDT"

    # 6. Verify plan summary is non-empty string
    assert isinstance(data["plan_summary"], str) and len(data["plan_summary"]) > 20
