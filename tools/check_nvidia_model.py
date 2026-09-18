"""Check the production NVIDIA interpreter against official sample semantics."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.guardrails import DirectiveValidationError, validate_interpretations as _validate
from app.interpreter import LLMInterpreter, LLMProviderError

DEFAULT_MODEL = "meta/llama-3.2-11b-vision-instruct"
ValidationError = DirectiveValidationError


def validate_interpretations(
    value: Any, note_count: int, battery_capacity: float
) -> list[dict[str, Any]]:
    """Compatibility wrapper around the production guardrail implementation."""
    return _validate(value, note_count=note_count, battery_capacity=battery_capacity)


def compare_ground_truth(
    actual: list[dict[str, Any]], expected: list[dict[str, Any]], tolerance: float = 0.01
) -> list[str]:
    """Compare all machine-readable directive semantics; explanations are free text."""
    differences: list[str] = []
    if len(actual) != len(expected):
        return [f"entry count={len(actual)}, expected {len(expected)}"]

    for index, (got, want) in enumerate(zip(actual, expected)):
        for field in ("note_index", "applies", "directive_type"):
            if got.get(field) != want.get(field):
                differences.append(
                    f"note {index}: {field}={got.get(field)!r}, expected {want.get(field)!r}"
                )
        got_adjustment = got.get("structured_adjustment")
        want_adjustment = want.get("structured_adjustment")
        if got_adjustment is None or want_adjustment is None:
            if got_adjustment != want_adjustment:
                differences.append(f"note {index}: structured_adjustment mismatch")
            continue
        if set(got_adjustment) != set(want_adjustment):
            differences.append(f"note {index}: adjustment fields differ")
            continue
        for field, wanted_value in want_adjustment.items():
            actual_value = got_adjustment[field]
            if isinstance(wanted_value, list):
                if actual_value != wanted_value:
                    differences.append(
                        f"note {index}: {field}={actual_value!r}, expected {wanted_value!r}"
                    )
            else:
                field_tolerance = 1e-9 if field == "factor" else tolerance
                if not math.isclose(
                    float(actual_value), float(wanted_value), rel_tol=0.0, abs_tol=field_tolerance
                ):
                    differences.append(
                        f"note {index}: {field}={actual_value!r}, expected {wanted_value!r}"
                    )
    return differences


def request_interpretation(
    api_key: str, model: str, case_input: dict[str, Any], timeout: float
) -> tuple[dict[str, Any], float]:
    """Invoke exactly the same interpreter and guardrails used by the API."""
    client = LLMInterpreter(api_key=api_key, model=model)
    started = time.perf_counter()
    entries = client.interpret(
        scenario_id=case_input["scenario_id"],
        operator_notes=case_input["operator_notes"],
        battery_capacity_kwh=float(case_input["battery"]["capacity_kwh"]),
        timeout=timeout,
    )
    return {"directive_interpretation": entries}, time.perf_counter() - started


def find_sample_pack(root: Path) -> Path:
    matches = sorted(root.glob("*Public_Sample_Cases*.json"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one public sample pack in {root}, found {len(matches)}")
    return matches[0]


def _load_local_env(root: Path) -> None:
    env_file = root / ".env"
    if not env_file.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file)
    except ImportError:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", help="case ID to run; may be repeated")
    parser.add_argument("--offline", action="store_true", help="validate references only")
    parser.add_argument("--timeout", type=float, default=27.0)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    pack = json.loads(find_sample_pack(root).read_text(encoding="utf-8-sig"))
    selected = [case for case in pack["cases"] if not args.case or case["id"] in args.case]
    if not selected:
        print("No matching cases selected.", file=sys.stderr)
        return 2

    _load_local_env(root)
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    model = os.environ.get("NVIDIA_MODEL", DEFAULT_MODEL)
    if not args.offline and not api_key:
        print("NVIDIA_API_KEY is not configured.", file=sys.stderr)
        return 2

    failures = 0
    timings: list[float] = []
    for case in selected:
        expected = case["expected_output"]["directive_interpretation"]
        try:
            if args.offline:
                value, elapsed = {"directive_interpretation": expected}, 0.0
            else:
                value, elapsed = request_interpretation(api_key, model, case["input"], args.timeout)
            actual = _validate(
                value,
                note_count=len(case["input"]["operator_notes"]),
                battery_capacity=float(case["input"]["battery"]["capacity_kwh"]),
                operator_notes=case["input"]["operator_notes"],
            )
            differences = compare_ground_truth(actual, expected)
            if differences:
                failures += 1
                print(f"FAIL {case['id']} ({elapsed:.2f}s)")
                for difference in differences:
                    print(f"  - {difference}")
            else:
                timings.append(elapsed)
                print(f"PASS {case['id']} ({elapsed:.2f}s)")
        except (LLMProviderError, DirectiveValidationError, ValueError) as exc:
            failures += 1
            print(f"FAIL {case['id']}: {exc}")

    passed = len(selected) - failures
    print(f"\nResult: {passed}/{len(selected)} passed")
    if timings and not args.offline:
        ordered = sorted(timings)
        p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
        print(f"Successful-call p95: {ordered[p95_index]:.2f}s")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
