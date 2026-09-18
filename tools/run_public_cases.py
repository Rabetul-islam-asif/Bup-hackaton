"""End-to-end regression runner for GridWise across all public sample cases.

Supports both:
- Offline mode: uses reference directive interpretations to benchmark optimizer,
  recalculation, and independent replay against reference costs.
- Live mode: sends operator notes through the real LLM interpreter before solving.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.constraints import compile_hourly_constraints
from app.guardrails import validate_interpretations
from app.interpreter import interpreter
from app.optimizer import solve_energy_schedule
from app.replay import replay_schedule, verify_response_aggregates
from app.response import assemble_optimization_response
from app.schemas import OptimizeEnergyRequest
from tools.check_nvidia_model import compare_ground_truth, find_sample_pack


def run_cases(
    selected_cases: list[dict],
    offline: bool = False,
    timeout: float = 25.0,
) -> int:
    print(f"Running {'OFFLINE' if offline else 'LIVE'} regression on {len(selected_cases)} case(s)...\n")

    failures = 0
    timings: list[float] = []

    for case in selected_cases:
        case_id = case["id"]
        expected_output = case["expected_output"]
        expected_cost = float(expected_output["total_cost_bdt"])
        expected_directives = expected_output["directive_interpretation"]

        start_time = time.perf_counter()
        try:
            req = OptimizeEnergyRequest.model_validate(case["input"])

            # Validate and solve the organizer reference independently. This
            # proves the deterministic pipeline can reproduce the expected
            # result even when live extraction is also under test.
            reference_directives = validate_interpretations(
                {"directive_interpretation": expected_directives},
                note_count=len(req.operator_notes),
                battery_capacity=req.battery.capacity_kwh,
                operator_notes=req.operator_notes,
            )
            reference_constraints = compile_hourly_constraints(
                req.hours, req.battery, reference_directives
            )
            reference_result = solve_energy_schedule(reference_constraints)
            reference_response = assemble_optimization_response(
                req.scenario_id, req.hours, reference_directives, reference_result
            )
            replay_schedule(
                req.hours, req.battery, reference_directives, reference_response.hourly_plan
            )
            verify_response_aggregates(
                req.hours,
                reference_response.hourly_plan,
                reference_response.total_grid_kwh,
                reference_response.total_cost_bdt,
                reference_response.peak_grid_kwh,
            )
            reference_delta = abs(reference_response.total_cost_bdt - expected_cost)
            if reference_delta > 0.01:
                raise AssertionError(
                    f"reference pipeline cost delta {reference_delta:.4f} exceeds 0.01"
                )

            # Step 1: Directive Interpretation
            if offline:
                validated_directives = reference_directives
            else:
                validated_directives = interpreter.interpret(
                    scenario_id=req.scenario_id,
                    operator_notes=req.operator_notes,
                    battery_capacity_kwh=req.battery.capacity_kwh,
                    timeout=timeout,
                )
                # Check semantic alignment with expected directives
                semantic_diffs = compare_ground_truth(validated_directives, expected_directives)
                if semantic_diffs:
                    raise AssertionError(
                        "directive semantic mismatch: " + "; ".join(semantic_diffs)
                    )

            # Step 2: Compile Constraints
            constraints = compile_hourly_constraints(req.hours, req.battery, validated_directives)

            # Step 3: Solve LP
            opt_res = solve_energy_schedule(constraints)

            # Step 4: Assemble Response
            resp = assemble_optimization_response(req.scenario_id, req.hours, validated_directives, opt_res)

            # Step 5: Independent Replay
            replay_schedule(req.hours, req.battery, validated_directives, resp.hourly_plan)
            verify_response_aggregates(
                req.hours,
                resp.hourly_plan,
                resp.total_grid_kwh,
                resp.total_cost_bdt,
                resp.peak_grid_kwh,
            )

            elapsed = time.perf_counter() - start_time
            timings.append(elapsed)

            cost_delta = abs(resp.total_cost_bdt - expected_cost)
            status_str = "PASS" if cost_delta <= 0.01 else "FAIL (cost delta)"
            if cost_delta > 0.01:
                failures += 1

            print(
                f"{status_str} {case_id} ({elapsed:.2f}s) | "
                f"Cost: {resp.total_cost_bdt:,.2f} BDT (exp: {expected_cost:,.2f}, delta: {cost_delta:.4f}) | "
                f"Grid: {resp.total_grid_kwh:,.2f} kWh | Peak: {resp.peak_grid_kwh:,.2f} kWh"
            )

        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            failures += 1
            print(f"FAIL {case_id} ({elapsed:.2f}s) -> ERROR: {exc}")

    passed = len(selected_cases) - failures
    print(f"\nSummary: {passed}/{len(selected_cases)} passed.")
    if timings:
        ordered = sorted(timings)
        p50 = ordered[len(ordered) // 2]
        p95_idx = max(0, math.ceil(0.95 * len(ordered)) - 1)
        p95 = ordered[p95_idx]
        print(f"Latency: p50={p50:.2f}s, p95={p95:.2f}s, max={ordered[-1]:.2f}s")

    return 1 if failures > 0 else 0


def main():
    parser = argparse.ArgumentParser(description="GridWise Public Cases Regression Runner")
    parser.add_argument("--case", action="append", help="Specific case ID(s) to run")
    parser.add_argument("--offline", action="store_true", help="Run offline using reference directives")
    parser.add_argument("--timeout", type=float, default=25.0, help="Per-request timeout in seconds")
    args = parser.parse_args()

    pack = json.loads(find_sample_pack(root_dir).read_text(encoding="utf-8-sig"))
    selected = [c for c in pack["cases"] if not args.case or c["id"] in args.case]

    if not selected:
        print("No matching cases found.", file=sys.stderr)
        return 2

    return run_cases(selected, offline=args.offline, timeout=args.timeout)


if __name__ == "__main__":
    sys.exit(main())
