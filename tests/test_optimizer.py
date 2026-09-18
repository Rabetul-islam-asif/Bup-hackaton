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
