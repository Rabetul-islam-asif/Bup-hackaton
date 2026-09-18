"""Check NVIDIA model interpretations against the official GridWise samples.

The script never prints the API key. It asks the model only to interpret operator
notes; deterministic code validates the result and compares it with organizer
ground truth. It does not test the energy optimizer.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests


API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODEL = "meta/llama-3.2-11b-vision-instruct"
DIRECTIVE_TYPES = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}
ADJUSTMENT_KEYS = {
    "solar_reduction": {"hours", "factor"},
    "minimum_battery_reserve": {"hours", "minimum_energy_kwh"},
    "no_charge_window": {"hours"},
    "no_discharge_window": {"hours"},
    "max_grid_window": {"hours", "max_grid_kwh"},
}

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "directive_interpretation": {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "note_index": {"type": "integer", "minimum": 0, "maximum": 2},
                    "applies": {"type": "boolean"},
                    "directive_type": {
                        "type": "string",
                        "enum": sorted(DIRECTIVE_TYPES),
                    },
                    "structured_adjustment": {
                        "anyOf": [
                            {"type": "null"},
                            {
                                "type": "object",
                                "properties": {
                                    "hours": {
                                        "type": "array",
                                        "items": {
                                            "type": "integer",
                                            "minimum": 0,
                                            "maximum": 23,
                                        },
                                    },
                                    "factor": {"type": "number"},
                                    "minimum_energy_kwh": {"type": "number"},
                                    "max_grid_kwh": {"type": "number"},
                                },
                                "additionalProperties": False,
                            },
                        ]
                    },
                    "explanation": {"type": "string", "minLength": 1},
                },
                "required": [
                    "note_index",
                    "applies",
                    "directive_type",
                    "structured_adjustment",
                    "explanation",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["directive_interpretation"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are the operator-note interpreter for GridWise.
Return only the requested JSON. Create exactly one directive_interpretation entry
for each note, in note_index order.

Allowed directive types and exact adjustment shapes:
- solar_reduction: {"hours": [...], "factor": number}
- minimum_battery_reserve: {"hours": [...], "minimum_energy_kwh": number}
- no_charge_window: {"hours": [...]}
- no_discharge_window: {"hours": [...]}
- max_grid_window: {"hours": [...], "max_grid_kwh": number}
- no_op: null

Rules:
- Relevant notes use applies=true. Only no_op uses applies=false and null adjustment.
- Hours are unique integers 0..23 in ascending order.
- Time windows include the start hour and exclude the end hour.
- Convert AM/PM to 24-hour integers. Noon is 12 and midnight is 0.
- For solar_reduction, factor is the usable fraction REMAINING. An 80 percent
  reduction means factor=0.2; reduced to 80 percent means factor=0.8.
- Convert a battery reserve percentage using the supplied battery capacity.
- Notes unrelated to the current 24-hour energy schedule are no_op.
- Never invent another directive type, hour, numeric value, or energy rule.
"""


class ValidationError(ValueError):
    pass


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValidationError(f"{name} must be finite")
    return number


def validate_interpretations(
    value: Any, note_count: int, battery_capacity: float
) -> list[dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != {"directive_interpretation"}:
        raise ValidationError("top level must contain only directive_interpretation")
    entries = value["directive_interpretation"]
    if not isinstance(entries, list) or len(entries) != note_count:
        raise ValidationError(f"expected exactly {note_count} interpretation entries")

    required_entry_keys = {
        "note_index",
        "applies",
        "directive_type",
        "structured_adjustment",
        "explanation",
    }
    for expected_index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != required_entry_keys:
            raise ValidationError(f"entry {expected_index} has incorrect fields")
        if entry["note_index"] != expected_index:
            raise ValidationError(f"entry {expected_index} has wrong note_index")
        if not isinstance(entry["applies"], bool):
            raise ValidationError(f"entry {expected_index} applies must be boolean")
        if not isinstance(entry["explanation"], str) or not entry["explanation"].strip():
            raise ValidationError(f"entry {expected_index} explanation is empty")

        kind = entry["directive_type"]
        adjustment = entry["structured_adjustment"]
        if kind not in DIRECTIVE_TYPES:
            raise ValidationError(f"entry {expected_index} uses unsupported type {kind!r}")
        if kind == "no_op":
            if entry["applies"] is not False or adjustment is not None:
                raise ValidationError("no_op requires applies=false and null adjustment")
            continue
        if entry["applies"] is not True:
            raise ValidationError(f"{kind} requires applies=true")
        if not isinstance(adjustment, dict) or set(adjustment) != ADJUSTMENT_KEYS[kind]:
            raise ValidationError(f"{kind} has incorrect adjustment fields")

        hours = adjustment["hours"]
        if (
            not isinstance(hours, list)
            or not hours
            or any(isinstance(hour, bool) or not isinstance(hour, int) for hour in hours)
            or hours != sorted(set(hours))
            or any(hour < 0 or hour > 23 for hour in hours)
        ):
            raise ValidationError(f"{kind} hours must be unique sorted integers 0..23")

        if kind == "solar_reduction":
            factor = _number(adjustment["factor"], "factor")
            if not 0 <= factor <= 1:
                raise ValidationError("solar factor must be between 0 and 1")
        elif kind == "minimum_battery_reserve":
            reserve = _number(adjustment["minimum_energy_kwh"], "minimum_energy_kwh")
            if not 0 <= reserve <= battery_capacity:
                raise ValidationError("minimum reserve must be between 0 and capacity")
        elif kind == "max_grid_window":
            if _number(adjustment["max_grid_kwh"], "max_grid_kwh") < 0:
                raise ValidationError("grid cap must be non-negative")
    return entries


def compare_ground_truth(
    actual: list[dict[str, Any]], expected: list[dict[str, Any]], tolerance: float = 0.01
) -> list[str]:
    differences: list[str] = []
    for index, (got, want) in enumerate(zip(actual, expected)):
        for field in ("note_index", "applies", "directive_type"):
            if got[field] != want[field]:
                differences.append(f"note {index}: {field}={got[field]!r}, expected {want[field]!r}")
        got_adjustment = got["structured_adjustment"]
        want_adjustment = want["structured_adjustment"]
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
            elif abs(float(actual_value) - float(wanted_value)) > tolerance:
                differences.append(
                    f"note {index}: {field}={actual_value!r}, expected {wanted_value!r}"
                )
    return differences


def request_interpretation(
    api_key: str, model: str, case_input: dict[str, Any], timeout: float
) -> tuple[dict[str, Any], float]:
    user_content = json.dumps(
        {
            "scenario_id": case_input["scenario_id"],
            "operator_notes": case_input["operator_notes"],
            "battery_capacity_kwh": case_input["battery"]["capacity_kwh"],
        },
        ensure_ascii=False,
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 900,
        "stream": False,
        "nvext": {"guided_json": OUTPUT_SCHEMA},
    }
    started = time.perf_counter()
    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    elapsed = time.perf_counter() - started
    response.raise_for_status()
    body = response.json()
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValidationError("NVIDIA response is missing choices[0].message.content") from exc
    if not isinstance(content, str):
        raise ValidationError("model message content is not text")
    try:
        return json.loads(content), elapsed
    except json.JSONDecodeError as exc:
        raise ValidationError(f"model returned invalid JSON: {exc.msg}") from exc


def find_sample_pack(root: Path) -> Path:
    matches = sorted(root.glob("*Public_Sample_Cases*.json"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one public sample pack in {root}, found {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", help="case ID to run; may be repeated")
    parser.add_argument("--offline", action="store_true", help="validate the checker using references")
    parser.add_argument("--timeout", type=float, default=25.0)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    pack = json.loads(find_sample_pack(root).read_text(encoding="utf-8-sig"))
    selected = [case for case in pack["cases"] if not args.case or case["id"] in args.case]
    if not selected:
        print("No matching cases selected.", file=sys.stderr)
        return 2

    env_file = root / ".env"
    if env_file.is_file():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_file)
        except ImportError:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))

    api_key = os.environ.get("NVIDIA_API_KEY")
    model = os.environ.get("NVIDIA_MODEL", DEFAULT_MODEL)
    if not args.offline and not api_key:
        print(
            "NVIDIA_API_KEY is not configured. Revoke the exposed key, create a fresh key, "
            "and set it in this terminal before running the live check.",
            file=sys.stderr,
        )
        return 2

    failures = 0
    timings: list[float] = []
    for case in selected:
        expected_value = {"directive_interpretation": case["expected_output"]["directive_interpretation"]}
        try:
            if args.offline:
                value, elapsed = expected_value, 0.0
            else:
                value, elapsed = request_interpretation(api_key, model, case["input"], args.timeout)
            actual = validate_interpretations(
                value,
                len(case["input"]["operator_notes"]),
                float(case["input"]["battery"]["capacity_kwh"]),
            )
            differences = compare_ground_truth(actual, expected_value["directive_interpretation"])
            if differences:
                failures += 1
                print(f"FAIL {case['id']} ({elapsed:.2f}s)")
                for difference in differences:
                    print(f"  - {difference}")
            else:
                timings.append(elapsed)
                print(f"PASS {case['id']} ({elapsed:.2f}s)")
        except (requests.RequestException, ValidationError, ValueError) as exc:
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

