"""FastAPI application for GridWise campus energy scheduling."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.constraints import compile_hourly_constraints
from app.guardrails import DirectiveValidationError
from app.interpreter import LLMProviderError, interpreter
from app.optimizer import OptimizationInfeasibleError, solve_energy_schedule
from app.replay import ReplayValidationError, replay_schedule
from app.response import assemble_optimization_response
from app.schemas import (
    HealthResponse,
    OptimizeEnergyRequest,
    OptimizeEnergyResponse,
)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gridwise.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown logic."""
    logger.info("Starting GridWise API service...")
    logger.info("Configuration: %s", settings.sanitized_dict())
    if not settings.is_llm_configured():
        logger.warning("WARNING: NVIDIA_API_KEY is not set. Live LLM calls will fail.")
    yield
    logger.info("Shutting down GridWise API service.")


app = FastAPI(
    title="GridWise API",
    description="LLM-driven 24-Hour Campus Energy Scheduler with HiGHS LP Optimization",
    version="1.0.0",
    lifespan=lifespan,
)


# --- Custom Exception Handlers ---


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Contest Requirement: Return HTTP 400 for structural/schema validation errors."""
    logger.warning("Request validation failed: %s", exc)
    sanitized_errors = [
        {
            "loc": [str(x) for x in err.get("loc", [])],
            "msg": str(err.get("msg")),
            "type": str(err.get("type")),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Invalid request payload or schema violation", "errors": sanitized_errors},
    )


@app.exception_handler(DirectiveValidationError)
async def directive_validation_exception_handler(request: Request, exc: DirectiveValidationError):
    logger.error("Directive guardrails rejected interpretation: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Failed to extract valid directives from notes"},
    )


@app.exception_handler(LLMProviderError)
async def llm_provider_exception_handler(request: Request, exc: LLMProviderError):
    logger.error("LLM provider failure: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Language model interpretation service unavailable"},
    )


@app.exception_handler(OptimizationInfeasibleError)
async def optimization_exception_handler(request: Request, exc: OptimizationInfeasibleError):
    logger.error("Solver infeasibility: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Energy schedule optimization infeasible"},
    )


@app.exception_handler(ReplayValidationError)
async def replay_exception_handler(request: Request, exc: ReplayValidationError):
    logger.error("Replay verification rejected generated schedule: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal schedule verification failed"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# --- Endpoints ---


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def get_health() -> HealthResponse:
    """Return health status of the service."""
    return HealthResponse(status="ok")


@app.post("/optimize-energy", response_model=OptimizeEnergyResponse, tags=["Optimization"])
async def optimize_energy(payload: OptimizeEnergyRequest) -> OptimizeEnergyResponse:
    """Interpret operator notes with LLM, compile constraints, solve LP, and verify schedule."""
    logger.info("Processing optimization request for scenario '%s' with %d notes", payload.scenario_id, len(payload.operator_notes))

    # 1. LLM Interpretation with Guardrails
    validated_directives = interpreter.interpret(
        scenario_id=payload.scenario_id,
        operator_notes=payload.operator_notes,
        battery_capacity_kwh=payload.battery.capacity_kwh,
    )

    # 2. Compile Hourly Constraints
    constraints = compile_hourly_constraints(
        hours=payload.hours,
        battery=payload.battery,
        validated_directives=validated_directives,
    )

    # 3. Solve 24-Hour Schedule with HiGHS LP
    opt_result = solve_energy_schedule(constraints)

    # 4. Assemble Response and Recalculate Totals
    response = assemble_optimization_response(
        scenario_id=payload.scenario_id,
        hours=payload.hours,
        validated_directives=validated_directives,
        opt_result=opt_result,
    )

    # 5. Independent Replay Verification
    replay_schedule(
        hours=payload.hours,
        battery=payload.battery,
        validated_directives=validated_directives,
        hourly_plan=response.hourly_plan,
    )

    logger.info("Scenario '%s' optimized successfully: Cost=%.2f BDT, Grid=%.2f kWh", response.scenario_id, response.total_cost_bdt, response.total_grid_kwh)
    return response
