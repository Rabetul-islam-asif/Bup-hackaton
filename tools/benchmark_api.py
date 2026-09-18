"""Benchmark latency and reliability for GridWise API service."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import requests

root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.guardrails import validate_interpretations
from app.replay import replay_schedule, verify_response_aggregates
from app.schemas import OptimizeEnergyRequest, OptimizeEnergyResponse
from tools.check_nvidia_model import compare_ground_truth, find_sample_pack


def benchmark_endpoint(
    base_url: str,
    iterations: int = 3,
    case_ids: list[str] | None = None,
) -> int:
    base_url = base_url.rstrip("/")
    health_url = f"{base_url}/health"
    optimize_url = f"{base_url}/optimize-energy"

    print(f"=== Benchmarking GridWise at {base_url} ===")
    print(f"Iterations: {iterations}")

    # 1. Health check
    try:
        t0 = time.perf_counter()
        resp = requests.get(health_url, timeout=5.0)
        t_health = time.perf_counter() - t0
        resp.raise_for_status()
        print(f"Health check: OK ({t_health * 1000:.1f}ms)")
    except Exception as exc:
        print(f"Health check failed: {exc}", file=sys.stderr)
        return 1

    # 2. Optimization benchmarking
    pack = json.loads(find_sample_pack(root_dir).read_text(encoding="utf-8-sig"))
    cases = [c for c in pack["cases"] if not case_ids or c["id"] in case_ids]

    timings: list[float] = []
    failures = 0
    total_requests = len(cases) * iterations

    print(f"\nRunning {total_requests} optimization requests across {len(cases)} case(s)...")

    for i in range(iterations):
        print(f"\n--- Pass {i + 1}/{iterations} ---")
        for case in cases:
            cid = case["id"]
            payload = case["input"]
            expected_cost = float(case["expected_output"]["total_cost_bdt"])

            start = time.perf_counter()
            try:
                r = requests.post(optimize_url, json=payload, timeout=30.0)
                elapsed = time.perf_counter() - start
                r.raise_for_status()
                request_model = OptimizeEnergyRequest.model_validate(payload)
                response_model = OptimizeEnergyResponse.model_validate(r.json())
                actual_directives = [
                    directive.model_dump() for directive in response_model.directive_interpretation
                ]
                expected_directives = validate_interpretations(
                    {"directive_interpretation": case["expected_output"]["directive_interpretation"]},
                    note_count=len(request_model.operator_notes),
                    battery_capacity=request_model.battery.capacity_kwh,
                    operator_notes=request_model.operator_notes,
                )
                differences = compare_ground_truth(actual_directives, expected_directives)
                if differences:
                    raise AssertionError("directive semantic mismatch: " + "; ".join(differences))
                replay_schedule(
                    request_model.hours,
                    request_model.battery,
                    expected_directives,
                    response_model.hourly_plan,
                )
                verify_response_aggregates(
                    request_model.hours,
                    response_model.hourly_plan,
                    response_model.total_grid_kwh,
                    response_model.total_cost_bdt,
                    response_model.peak_grid_kwh,
                )

                cost = response_model.total_cost_bdt
                cost_delta = abs(cost - expected_cost)
                if cost_delta > 0.01:
                    failures += 1
                    print(f"FAIL {cid} ({elapsed:.2f}s) - Cost delta: {cost_delta:.2f} BDT")
                else:
                    timings.append(elapsed)
                    print(f"PASS {cid} ({elapsed:.2f}s) - Cost: {cost:,.2f} BDT (exact match)")
            except Exception as exc:
                elapsed = time.perf_counter() - start
                failures += 1
                print(f"ERROR {cid} ({elapsed:.2f}s) - {exc}")

    # Summary
    print(f"\n=== Benchmark Results ===")
    print(f"Total Requests: {total_requests}")
    print(f"Successful: {len(timings)}")
    print(f"Failed: {failures}")
    print(f"Success Rate: {(len(timings) / total_requests) * 100:.1f}%")

    if timings:
        ordered = sorted(timings)
        p50 = ordered[len(ordered) // 2]
        p95_idx = max(0, math.ceil(0.95 * len(ordered)) - 1)
        p95 = ordered[p95_idx]
        print(f"Latency p50: {p50:.2f}s")
        print(f"Latency p95: {p95:.2f}s")
        print(f"Latency Min: {ordered[0]:.2f}s")
        print(f"Latency Max: {ordered[-1]:.2f}s")

    return 1 if failures > 0 else 0


def main():
    parser = argparse.ArgumentParser(description="GridWise Benchmark Utility")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of GridWise service")
    parser.add_argument("--iterations", type=int, default=1, help="Number of passes over cases")
    parser.add_argument("--case", action="append", help="Specific case ID(s) to test")
    args = parser.parse_args()

    return benchmark_endpoint(args.url, iterations=args.iterations, case_ids=args.case)


if __name__ == "__main__":
    sys.exit(main())
