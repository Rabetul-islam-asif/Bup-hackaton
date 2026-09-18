"""Unit tests for deterministic guardrail validation of directive interpretations."""

import copy
import pytest

from app.guardrails import DirectiveValidationError, validate_interpretations

VALID_SOLAR = {
    "directive_interpretation": [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [11, 12, 13], "factor": 0.2},
            "explanation": "An 80 percent reduction leaves 20 percent usable solar.",
        }
    ]
}


def test_accepts_valid_solar():
    res = validate_interpretations(copy.deepcopy(VALID_SOLAR), note_count=1, battery_capacity=200.0)
    assert len(res) == 1
    assert res[0]["note_index"] == 0
    assert res[0]["directive_type"] == "solar_reduction"
    assert res[0]["structured_adjustment"]["factor"] == 0.2


def test_accepts_valid_no_op():
    payload = {
        "directive_interpretation": [
            {
                "note_index": 0,
                "applies": False,
                "directive_type": "no_op",
                "structured_adjustment": None,
                "explanation": "Note is unrelated to the current schedule.",
            }
        ]
    }
    res = validate_interpretations(payload, note_count=1, battery_capacity=200.0)
    assert res[0]["applies"] is False
    assert res[0]["structured_adjustment"] is None


def test_accepts_valid_reserve():
    payload = {
        "directive_interpretation": [
            {
                "note_index": 0,
                "applies": True,
                "directive_type": "minimum_battery_reserve",
                "structured_adjustment": {"hours": [18, 19, 20], "minimum_energy_kwh": 100.0},
                "explanation": "Keep at least 100 kWh in reserve during evening hours.",
            }
        ]
    }
    res = validate_interpretations(payload, note_count=1, battery_capacity=200.0)
    assert res[0]["structured_adjustment"]["minimum_energy_kwh"] == 100.0


def test_accepts_valid_windows():
    payload = {
        "directive_interpretation": [
            {
                "note_index": 0,
                "applies": True,
                "directive_type": "no_charge_window",
                "structured_adjustment": {"hours": [1, 2, 3]},
                "explanation": "No charging allowed.",
            },
            {
                "note_index": 1,
                "applies": True,
                "directive_type": "no_discharge_window",
                "structured_adjustment": {"hours": [4, 5]},
                "explanation": "No discharging allowed.",
            },
            {
                "note_index": 2,
                "applies": True,
                "directive_type": "max_grid_window",
                "structured_adjustment": {"hours": [14, 15], "max_grid_kwh": 50.0},
                "explanation": "Grid cap active.",
            },
        ]
    }
    res = validate_interpretations(payload, note_count=3, battery_capacity=200.0)
    assert len(res) == 3


def test_rejects_unsupported_directive():
    payload = copy.deepcopy(VALID_SOLAR)
    payload["directive_interpretation"][0]["directive_type"] = "shutdown_generator"
    with pytest.raises(DirectiveValidationError):
        validate_interpretations(payload, note_count=1, battery_capacity=200.0)


def test_rejects_wrong_note_index():
    payload = copy.deepcopy(VALID_SOLAR)
    payload["directive_interpretation"][0]["note_index"] = 1
    with pytest.raises(DirectiveValidationError):
        validate_interpretations(payload, note_count=1, battery_capacity=200.0)


def test_rejects_boolean_as_note_index():
    payload = copy.deepcopy(VALID_SOLAR)
    payload["directive_interpretation"][0]["note_index"] = False
    with pytest.raises(DirectiveValidationError):
        validate_interpretations(payload, note_count=1, battery_capacity=200.0)


def test_rejects_factor_out_of_range():
    for bad_factor in [-0.1, 1.05]:
        payload = copy.deepcopy(VALID_SOLAR)
        payload["directive_interpretation"][0]["structured_adjustment"]["factor"] = bad_factor
        with pytest.raises(DirectiveValidationError):
            validate_interpretations(payload, note_count=1, battery_capacity=200.0)


def test_rejects_reserve_above_capacity():
    payload = {
        "directive_interpretation": [
            {
                "note_index": 0,
                "applies": True,
                "directive_type": "minimum_battery_reserve",
                "structured_adjustment": {"hours": [18, 19], "minimum_energy_kwh": 250.0},
                "explanation": "Reserve exceeds capacity.",
            }
        ]
    }
    with pytest.raises(DirectiveValidationError):
        validate_interpretations(payload, note_count=1, battery_capacity=200.0)


def test_rejects_negative_grid_cap():
    payload = {
        "directive_interpretation": [
            {
                "note_index": 0,
                "applies": True,
                "directive_type": "max_grid_window",
                "structured_adjustment": {"hours": [14], "max_grid_kwh": -10.0},
                "explanation": "Negative cap.",
            }
        ]
    }
    with pytest.raises(DirectiveValidationError):
        validate_interpretations(payload, note_count=1, battery_capacity=200.0)


def test_rejects_unsorted_or_duplicate_hours():
    for bad_hours in ([12, 11], [11, 11], [0, 24], [-1, 5], []):
        payload = copy.deepcopy(VALID_SOLAR)
        payload["directive_interpretation"][0]["structured_adjustment"]["hours"] = bad_hours
        with pytest.raises(DirectiveValidationError):
            validate_interpretations(payload, note_count=1, battery_capacity=200.0)


def test_rejects_extra_fields():
    payload = copy.deepcopy(VALID_SOLAR)
    payload["directive_interpretation"][0]["confidence"] = 0.99
    with pytest.raises(DirectiveValidationError):
        validate_interpretations(payload, note_count=1, battery_capacity=200.0)


def test_rejects_active_with_applies_false():
    payload = copy.deepcopy(VALID_SOLAR)
    payload["directive_interpretation"][0]["applies"] = False
    with pytest.raises(DirectiveValidationError):
        validate_interpretations(payload, note_count=1, battery_capacity=200.0)


def test_rejects_no_op_with_applies_true():
    payload = {
        "directive_interpretation": [
            {
                "note_index": 0,
                "applies": True,
                "directive_type": "no_op",
                "structured_adjustment": None,
                "explanation": "no_op cannot have applies=true.",
            }
        ]
    }
    with pytest.raises(DirectiveValidationError):
        validate_interpretations(payload, note_count=1, battery_capacity=200.0)


def test_rejects_no_op_with_adjustment():
    payload = {
        "directive_interpretation": [
            {
                "note_index": 0,
                "applies": False,
                "directive_type": "no_op",
                "structured_adjustment": {"hours": [1]},
                "explanation": "no_op cannot have adjustment.",
            }
        ]
    }
    with pytest.raises(DirectiveValidationError):
        validate_interpretations(payload, note_count=1, battery_capacity=200.0)
