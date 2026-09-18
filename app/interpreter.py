"""Client adapter for NVIDIA LLM operator-notes interpretation with guardrails and repair retry."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

from app.config import settings
from app.guardrails import (
    DirectiveValidationError,
    validate_interpretations,
)

logger = logging.getLogger("gridwise.interpreter")

PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "operator_notes.txt"


class LLMProviderError(Exception):
    """Raised when the LLM provider call fails or returns unparseable content."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class LLMInterpreter:
    def __init__(self, api_key: str | None = None, model: str | None = None, api_url: str | None = None) -> None:
        self.api_key = settings.nvidia_api_key if api_key is None else api_key
        self.model = model or settings.nvidia_model
        self.api_url = api_url or settings.nvidia_api_url

        # Keep transport retries disabled. The interpreter owns the strict
        # two-call budget, including provider failures and JSON repair calls.
        self.session = requests.Session()

    def _get_system_prompt(self) -> str:
        return PROMPT_FILE.read_text(encoding="utf-8").strip()

    def _call_api(self, messages: list[dict[str, str]], timeout: float) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 800,
            "stream": False,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        try:
            response = self.session.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=max(2.0, timeout),
            )
        except requests.Timeout as exc:
            raise LLMProviderError(
                f"LLM request timed out after {timeout:.1f}s", retryable=True
            ) from exc
        except requests.RequestException as exc:
            raise LLMProviderError("Failed to reach LLM provider", retryable=True) from exc

        if response.status_code != 200:
            logger.error("LLM request failed with status %d", response.status_code)
            raise LLMProviderError(
                f"LLM provider error (status {response.status_code})",
                retryable=response.status_code == 429 or response.status_code >= 500,
            )

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMProviderError("Invalid or missing content structure from LLM response") from exc

        if not isinstance(content, str):
            raise LLMProviderError("LLM response content is not text")

        return content

    def interpret(
        self,
        scenario_id: str,
        operator_notes: list[str],
        battery_capacity_kwh: float,
        timeout: float | None = None,
    ) -> list[dict[str, Any]]:
        """Call the LLM to interpret operator notes and run deterministic guardrails.

        Makes at most two provider calls in total. The second call retries a
        transient provider failure or repairs one invalid interpretation.
        """
        if not self.api_key or not self.api_key.strip():
            raise LLMProviderError("NVIDIA_API_KEY is not configured on the service.")

        total_deadline = timeout or settings.total_request_deadline_seconds
        if total_deadline <= 0:
            raise LLMProviderError("LLM request deadline must be positive")
        start_time = time.perf_counter()

        system_prompt = self._get_system_prompt()
        user_content = json.dumps(
            {
                "scenario_id": scenario_id,
                "operator_notes": operator_notes,
                "battery_capacity_kwh": battery_capacity_kwh,
            },
            ensure_ascii=False,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        next_messages = messages
        last_error: Exception | None = None

        for attempt in range(2):
            remaining = total_deadline - (time.perf_counter() - start_time)
            calls_left = 2 - attempt
            if remaining < 0.5:
                raise LLMProviderError("LLM request deadline exhausted") from last_error

            # Leave a useful share of the deadline for the one allowed retry.
            if calls_left == 2:
                call_budget = min(settings.llm_timeout_seconds, max(0.5, remaining * 0.68))
            else:
                call_budget = min(settings.llm_timeout_seconds, remaining)

            try:
                raw_content = self._call_api(next_messages, timeout=call_budget)
            except LLMProviderError as exc:
                last_error = exc
                if attempt == 0 and exc.retryable:
                    logger.warning("[%s] transient provider failure; retrying once", scenario_id)
                    continue
                raise

            logger.info(
                "[%s] LLM attempt %d completed at %.2fs",
                scenario_id,
                attempt + 1,
                time.perf_counter() - start_time,
            )
            try:
                parsed_data = json.loads(raw_content)
                return validate_interpretations(
                    parsed_data,
                    note_count=len(operator_notes),
                    battery_capacity=battery_capacity_kwh,
                    operator_notes=operator_notes,
                )
            except (json.JSONDecodeError, DirectiveValidationError) as exc:
                last_error = exc
                if attempt == 1:
                    raise LLMProviderError(
                        f"LLM output violated guardrails after repair: {exc}"
                    ) from exc
                logger.warning("[%s] first interpretation failed validation", scenario_id)
                next_messages = list(messages)
                next_messages.append({"role": "assistant", "content": raw_content})
                next_messages.append({
                    "role": "user",
                    "content": (
                        f"Your response failed validation: {exc}. "
                        "Use start-inclusive and end-exclusive hours. "
                        "no_charge_window and no_discharge_window adjustments contain only hours. "
                        "Return only the corrected JSON object."
                    ),
                })

        raise LLMProviderError("LLM interpretation failed") from last_error


# Module singleton instance
interpreter = LLMInterpreter()
