"""Deterministic guardrails and validation for model-extracted directive interpretations."""

from __future__ import annotations

import math
import re
from typing import Any

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


class DirectiveValidationError(ValueError):
    """Raised when an LLM directive interpretation fails guardrails."""
    pass


def _strict_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DirectiveValidationError(f"{name} must be a number, got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise DirectiveValidationError(f"{name} must be finite")
    return number


def _strict_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DirectiveValidationError(f"{name} must be an integer, got {type(value).__name__}")
    return value


def parse_hour_token(token: str, default_period: str | None = None) -> int | None:
    token = token.strip().lower()
    if token == "noon":
        return 12
    if token == "midnight":
        return 0
    m = re.match(r"(\d{1,2})(?::00)?\s*(am|pm)?", token)
    if not m:
        return None
    hr = int(m.group(1))
    period = m.group(2) or default_period
    if period == "pm" and hr != 12:
        hr += 12
    elif period == "am" and hr == 12:
        hr = 0
    return hr


def extract_window_range(text: str) -> list[int] | None:
    """Extract strictly start-inclusive, end-exclusive hour range [S, E) from text."""
    text_lower = text.lower()
    # 1. Duration pattern: e.g. 'starting at 2 PM for 3 hours' or 'from 10:00 for 2 hrs'
    dur_m = re.search(
        r"(?:starting|beginning|at|from)\s+(\d{1,2}(?::00)?\s*(?:am|pm)?|noon|midnight)\s+(?:for|lasting)\s+(\d+)\s*(?:hours?|hrs?)",
        text,
        re.IGNORECASE,
    )
    if dur_m:
        st_tok = dur_m.group(1).strip()
        dur = int(dur_m.group(2))
        st_p = "pm" if "pm" in text_lower else ("am" if "am" in text_lower else None)
        st_h = parse_hour_token(st_tok, st_p)
        if st_h is not None and 0 <= st_h < 24 and 0 < dur <= 24 and st_h + dur <= 24:
            return list(range(st_h, st_h + dur))

    # 2. Window range pattern: e.g. 'between 18:00 and 20:00', 'from 10 PM until midnight'
    pattern = r"(?:from|between)\s+(\d{1,2}(?::00)?\s*(?:am|pm)?|noon|midnight)\s+(?:until|to|and|-)\s+(\d{1,2}(?::00)?\s*(?:am|pm)?|noon|midnight)"
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    start_tok = m.group(1).strip()
    end_tok = m.group(2).strip()

    default_period = "pm" if "pm" in text_lower else ("am" if "am" in text_lower else None)
    end_period = "pm" if "pm" in end_tok.lower() else ("am" if "am" in end_tok.lower() else default_period)
    start_period = "pm" if "pm" in start_tok.lower() else ("am" if "am" in start_tok.lower() else end_period)

    start_h = parse_hour_token(start_tok, start_period)
    end_h = parse_hour_token(end_tok, end_period)

    if start_h is not None and end_h is not None:
        if (end_tok.lower() in ("midnight", "12 am", "12:00 am") or end_h == 0) and start_h > 0:
            end_h = 24
        elif end_tok.lower() in ("12 pm", "12:00 pm") and start_h >= 12:
            # Common user typo: writing 12 PM intending midnight after an evening hour
            end_h = 24
        if 0 <= start_h < end_h <= 24:
            return list(range(start_h, end_h))
    return None


def _extract_end_hour(text: str) -> int | None:
    """Extract explicit end-hour integer 0..23 from natural language text if present."""
    text_lower = text.lower()
    m = re.search(
        r'(?:until|to|and|-)\s+(\d{1,2}(?::00)?\s*(?:am|pm)?|noon|midnight)',
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    token = m.group(1).strip().lower()
    default_period = "pm" if "pm" in text_lower else ("am" if "am" in text_lower else None)
    return parse_hour_token(token, default_period)


def validate_interpretations(
    raw_response: Any,
    note_count: int,
    battery_capacity: float,
    operator_notes: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Strictly validate and normalize LLM directive interpretations.

    Ensures:
    - Top level is a dict with only 'directive_interpretation'
    - Exactly note_count items
    - Ordered indices 0..note_count-1
    - applies=False and structured_adjustment=None for no_op
    - applies=True and exact keys for active directives
    - Valid hours list: non-empty, sorted, unique ints in 0..23
    - Enforces start-inclusive, end-exclusive rule against end-hour inclusion
    - Correct value ranges for factor, reserve, and grid caps
    """
    if not isinstance(raw_response, dict) or set(raw_response.keys()) != {"directive_interpretation"}:
        raise DirectiveValidationError("top level must contain only 'directive_interpretation'")

    entries = raw_response["directive_interpretation"]
    if not isinstance(entries, list) or len(entries) != note_count:
        raise DirectiveValidationError(f"expected exactly {note_count} interpretation entries, got {len(entries) if isinstance(entries, list) else type(entries).__name__}")

    required_keys = {
        "note_index",
        "applies",
        "directive_type",
        "structured_adjustment",
        "explanation",
    }

    validated_entries: list[dict[str, Any]] = []

    for expected_index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry.keys()) != required_keys:
            raise DirectiveValidationError(f"entry {expected_index} has incorrect fields: {set(entry.keys()) if isinstance(entry, dict) else type(entry).__name__}")

        note_idx = _strict_int(entry["note_index"], f"entry {expected_index} note_index")
        if note_idx != expected_index:
            raise DirectiveValidationError(f"entry {expected_index} has wrong note_index: {note_idx}")

        if not isinstance(entry["applies"], bool):
            raise DirectiveValidationError(f"entry {expected_index} applies must be boolean")

        explanation = entry["explanation"]
        if not isinstance(explanation, str) or not explanation.strip():
            raise DirectiveValidationError(f"entry {expected_index} explanation must be a non-empty string")

        directive_type = entry["directive_type"]
        if not isinstance(directive_type, str) or directive_type not in DIRECTIVE_TYPES:
            raise DirectiveValidationError(f"entry {expected_index} uses unsupported directive_type {directive_type!r}")

        adjustment = entry["structured_adjustment"]

        if directive_type == "no_op":
            if entry["applies"] is not False or adjustment is not None:
                raise DirectiveValidationError("no_op requires applies=false and structured_adjustment=null")
            validated_entries.append({
                "note_index": note_idx,
                "applies": False,
                "directive_type": "no_op",
                "structured_adjustment": None,
                "explanation": explanation.strip(),
            })
            continue

        if entry["applies"] is not True:
            raise DirectiveValidationError(f"{directive_type} requires applies=true")

        if not isinstance(adjustment, dict) or set(adjustment.keys()) != ADJUSTMENT_KEYS[directive_type]:
            raise DirectiveValidationError(
                f"{directive_type} has incorrect adjustment fields: "
                f"{set(adjustment.keys()) if isinstance(adjustment, dict) else type(adjustment).__name__}"
            )

        raw_hours = adjustment["hours"]
        if not isinstance(raw_hours, list) or len(raw_hours) == 0:
            raise DirectiveValidationError(f"{directive_type} hours must be a non-empty list")

        # Deterministic start-inclusive, end-exclusive window enforcement from note text:
        if operator_notes and expected_index < len(operator_notes):
            note_text = operator_notes[expected_index]
            window_h = extract_window_range(note_text)
            if window_h is not None:
                raw_hours = window_h
            else:
                end_h = _extract_end_hour(note_text)
                if end_h is not None and len(raw_hours) > 1 and raw_hours[-1] == end_h:
                    raw_hours = raw_hours[:-1]

        for h in raw_hours:
            _strict_int(h, f"{directive_type} hour")
            if h < 0 or h > 23:
                raise DirectiveValidationError(f"{directive_type} hour out of bounds: {h}")

        if raw_hours != sorted(set(raw_hours)):
            raise DirectiveValidationError(f"{directive_type} hours must be unique sorted integers in 0..23")

        validated_adj: dict[str, Any] = {"hours": list(raw_hours)}

        if directive_type == "solar_reduction":
            factor = _strict_number(adjustment["factor"], "solar_reduction factor")
            if not (0.0 <= factor <= 1.0):
                raise DirectiveValidationError(f"solar factor must be between 0 and 1, got {factor}")
            validated_adj["factor"] = factor

        elif directive_type == "minimum_battery_reserve":
            reserve = _strict_number(adjustment["minimum_energy_kwh"], "minimum_battery_reserve minimum_energy_kwh")
            if not (0.0 <= reserve <= battery_capacity):
                raise DirectiveValidationError(f"minimum reserve must be between 0 and battery capacity ({battery_capacity}), got {reserve}")
            validated_adj["minimum_energy_kwh"] = reserve

        elif directive_type == "max_grid_window":
            grid_cap = _strict_number(adjustment["max_grid_kwh"], "max_grid_window max_grid_kwh")
            if grid_cap < 0.0:
                raise DirectiveValidationError(f"max_grid_kwh must be non-negative, got {grid_cap}")
            validated_adj["max_grid_kwh"] = grid_cap

        validated_entries.append({
            "note_index": note_idx,
            "applies": True,
            "directive_type": directive_type,
            "structured_adjustment": validated_adj,
            "explanation": explanation.strip(),
        })

    return validated_entries
