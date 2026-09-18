"""Pydantic schemas for the GridWise API."""

from __future__ import annotations

import math
from typing import Annotated, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DIRECTIVE_TYPE_LITERAL = Literal[
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
]

BATTERY_ACTION_LITERAL = Literal["charge", "discharge", "idle"]


def _ensure_finite_non_bool_float(v: Any, field_name: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{field_name} must be a number, got {type(v).__name__}")
    val = float(v)
    if not math.isfinite(val):
        raise ValueError(f"{field_name} must be finite")
    return val


def _ensure_non_negative_float(v: Any, field_name: str) -> float:
    val = _ensure_finite_non_bool_float(v, field_name)
    if val < 0.0:
        raise ValueError(f"{field_name} must be non-negative, got {val}")
    return val


def _ensure_strict_int(v: Any, field_name: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(f"{field_name} must be an integer, got {type(v).__name__}")
    return v


# --- Request Schemas ---


class HourlyForecast(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hour: int
    demand_kwh: float
    solar_kwh: float
    tariff_bdt_per_kwh: float

    @field_validator("hour", mode="before")
    @classmethod
    def validate_hour(cls, v: Any) -> int:
        val = _ensure_strict_int(v, "hour")
        if not (0 <= val <= 23):
            raise ValueError(f"hour must be between 0 and 23, got {val}")
        return val

    @field_validator("demand_kwh", mode="before")
    @classmethod
    def validate_demand(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "demand_kwh")

    @field_validator("solar_kwh", mode="before")
    @classmethod
    def validate_solar(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "solar_kwh")

    @field_validator("tariff_bdt_per_kwh", mode="before")
    @classmethod
    def validate_tariff(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "tariff_bdt_per_kwh")


class BatteryParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capacity_kwh: float
    initial_energy_kwh: float
    minimum_energy_kwh: float
    max_charge_kwh_per_hour: float
    max_discharge_kwh_per_hour: float

    @field_validator("capacity_kwh", mode="before")
    @classmethod
    def validate_capacity(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "capacity_kwh")

    @field_validator("initial_energy_kwh", mode="before")
    @classmethod
    def validate_initial(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "initial_energy_kwh")

    @field_validator("minimum_energy_kwh", mode="before")
    @classmethod
    def validate_minimum(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "minimum_energy_kwh")

    @field_validator("max_charge_kwh_per_hour", mode="before")
    @classmethod
    def validate_max_charge(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "max_charge_kwh_per_hour")

    @field_validator("max_discharge_kwh_per_hour", mode="before")
    @classmethod
    def validate_max_discharge(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "max_discharge_kwh_per_hour")

    @model_validator(mode="after")
    def validate_battery_coherence(self) -> BatteryParameters:
        if self.minimum_energy_kwh > self.capacity_kwh:
            raise ValueError(
                f"minimum_energy_kwh ({self.minimum_energy_kwh}) cannot exceed capacity_kwh ({self.capacity_kwh})"
            )
        if self.initial_energy_kwh > self.capacity_kwh:
            raise ValueError(
                f"initial_energy_kwh ({self.initial_energy_kwh}) cannot exceed capacity_kwh ({self.capacity_kwh})"
            )
        if self.initial_energy_kwh < self.minimum_energy_kwh:
            raise ValueError(
                f"initial_energy_kwh ({self.initial_energy_kwh}) cannot be less than minimum_energy_kwh ({self.minimum_energy_kwh})"
            )
        return self


from app.defaults import SAMPLE_OPTIMIZE_REQUEST_EXAMPLE


class OptimizeEnergyRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [SAMPLE_OPTIMIZE_REQUEST_EXAMPLE]
        },
    )

    scenario_id: str
    operator_notes: list[str]
    hours: list[HourlyForecast]
    battery: BatteryParameters

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("scenario_id must be a non-empty string")
        return v

    @field_validator("operator_notes")
    @classmethod
    def validate_operator_notes(cls, v: list[str]) -> list[str]:
        if not (1 <= len(v) <= 3):
            raise ValueError(f"operator_notes must contain between 1 and 3 items, got {len(v)}")
        for idx, note in enumerate(v):
            if not isinstance(note, str) or not note.strip():
                raise ValueError(f"operator_notes[{idx}] must be a non-empty string")
        return v

    @field_validator("hours")
    @classmethod
    def validate_hours_completeness(cls, v: list[HourlyForecast]) -> list[HourlyForecast]:
        if len(v) != 24:
            raise ValueError(f"hours must contain exactly 24 items, got {len(v)}")
        seen_hours = set()
        for item in v:
            if item.hour in seen_hours:
                raise ValueError(f"duplicate hour {item.hour} found in hours list")
            seen_hours.add(item.hour)
        if seen_hours != set(range(24)):
            missing = sorted(set(range(24)) - seen_hours)
            raise ValueError(f"hours must cover all hours 0..23, missing: {missing}")
        return sorted(v, key=lambda x: x.hour)


class QuickOptimizeRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "operator_notes": [
                        "Do not charge the battery between 6 PM and 9 PM."
                    ],
                    "scenario_id": "QUICK-DEMO",
                }
            ]
        },
    )

    operator_notes: list[str] = Field(
        default_factory=lambda: ["Do not charge the battery between 6 PM and 9 PM."],
        description="List of 1 to 3 operator notes/directives in natural language, or a single note string.",
    )
    scenario_id: str = Field(
        default="QUICK-DEMO",
        description="Optional scenario identifier.",
    )

    @field_validator("operator_notes", mode="before")
    @classmethod
    def validate_quick_notes(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, list):
            raise ValueError("operator_notes must be a list of strings or a single string")
        cleaned = [str(x).strip() for x in v if str(x).strip()]
        if not (1 <= len(cleaned) <= 3):
            raise ValueError(f"operator_notes must contain between 1 and 3 items, got {len(cleaned)}")
        return cleaned

    @field_validator("scenario_id")
    @classmethod
    def validate_quick_scenario_id(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            return "QUICK-DEMO"
        return v.strip()


# --- Response Schemas ---


class DirectiveInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_index: int
    applies: bool
    directive_type: DIRECTIVE_TYPE_LITERAL
    structured_adjustment: dict[str, Any] | None = None
    explanation: str

    @field_validator("note_index", mode="before")
    @classmethod
    def validate_note_index(cls, v: Any) -> int:
        val = _ensure_strict_int(v, "note_index")
        if not (0 <= val <= 2):
            raise ValueError(f"note_index must be between 0 and 2, got {val}")
        return val

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("explanation must be a non-empty string")
        return v


class HourlyPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hour: int
    grid_kwh: float
    solar_used_kwh: float
    battery_action: BATTERY_ACTION_LITERAL
    battery_kwh: float
    battery_energy_after_kwh: float

    @field_validator("hour", mode="before")
    @classmethod
    def validate_hour(cls, v: Any) -> int:
        val = _ensure_strict_int(v, "hour")
        if not (0 <= val <= 23):
            raise ValueError(f"hour must be 0..23, got {val}")
        return val

    @field_validator("grid_kwh", mode="before")
    @classmethod
    def validate_grid(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "grid_kwh")

    @field_validator("solar_used_kwh", mode="before")
    @classmethod
    def validate_solar_used(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "solar_used_kwh")

    @field_validator("battery_kwh", mode="before")
    @classmethod
    def validate_battery_kwh(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "battery_kwh")

    @field_validator("battery_energy_after_kwh", mode="before")
    @classmethod
    def validate_battery_energy_after(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "battery_energy_after_kwh")

    @model_validator(mode="after")
    def validate_action_consistency(self) -> HourlyPlan:
        if self.battery_action == "idle" and abs(self.battery_kwh) > 1e-6:
            raise ValueError("battery_kwh must be 0 when battery_action is idle")
        return self


class OptimizeEnergyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    directive_interpretation: list[DirectiveInterpretation]
    hourly_plan: list[HourlyPlan]
    total_grid_kwh: float
    total_cost_bdt: float
    peak_grid_kwh: float
    plan_summary: str

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("scenario_id must be a non-empty string")
        return v

    @field_validator("total_grid_kwh", mode="before")
    @classmethod
    def validate_total_grid(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "total_grid_kwh")

    @field_validator("total_cost_bdt", mode="before")
    @classmethod
    def validate_total_cost(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "total_cost_bdt")

    @field_validator("peak_grid_kwh", mode="before")
    @classmethod
    def validate_peak_grid(cls, v: Any) -> float:
        return _ensure_non_negative_float(v, "peak_grid_kwh")

    @field_validator("plan_summary")
    @classmethod
    def validate_summary(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("plan_summary must be a non-empty string")
        return v


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
