"""Test interpreter on held-out paraphrases suite."""

import json
from pathlib import Path
import pytest

from app.interpreter import interpreter
from tools.check_nvidia_model import compare_ground_truth

FIXTURES_FILE = Path(__file__).resolve().parent / "fixtures" / "paraphrases.json"
CASES = json.loads(FIXTURES_FILE.read_text(encoding="utf-8"))["test_cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_held_out_paraphrase(case):
    """Verify that unseen wording and distractors are correctly interpreted."""
    cid = case["id"]
    notes = case["operator_notes"]
    cap = case["battery_capacity_kwh"]
    expected_directives = case["expected_directives"]

    validated = interpreter.interpret(
        scenario_id=cid,
        operator_notes=notes,
        battery_capacity_kwh=cap,
        timeout=25.0,
    )

    assert len(validated) == len(expected_directives), f"{cid}: length mismatch"
    diffs = compare_ground_truth(validated, expected_directives)
    assert not diffs, f"{cid} semantic differences: {diffs}"
