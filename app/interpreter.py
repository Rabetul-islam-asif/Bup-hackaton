"""Client adapter for NVIDIA LLM operator-notes interpretation with guardrails and repair retry."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import settings
from app.guardrails import (
    DirectiveValidationError,
    validate_interpretations,
)

logger = logging.getLogger("gridwise.interpreter")

PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "operator_notes.txt"


class LLMProviderError(Exception):
    """Raised when the LLM provider call fails or returns unparseable content."""
    pass


class LLMInterpreter:
    def __init__(self, api_key: str | None = None, model: str | None = None, api_url: str | None = None) -> None:
        self.api_key = settings.nvidia_api_key if api_key is None else api_key
        self.model = model or settings.nvidia_model
        self.api_url = api_url or settings.nvidia_api_url

        # Reusable HTTP session with pool and bounded socket retries
        self.session = requests.Session()
        retries = Retry(
            total=2,
            connect=1,
            read=1,
            backoff_factor=0.5,
            status_forcelist=[429, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _get_system_prompt(self) -> str:
        return PROMPT_FILE.read_text(encoding="utf-8").strip()

    def _call_api(self, messages: list[dict[str, str]], timeout: float) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 900,
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
                timeout=timeout,
            )
        except requests.Timeout as exc:
            raise LLMProviderError(f"LLM request timed out after {timeout:.1f}s") from exc
        except requests.RequestException as exc:
            raise LLMProviderError("Failed to reach LLM provider") from exc

        if response.status_code != 200:
            logger.error("LLM request failed with status %d: %s", response.status_code, response.text[:200])
            raise LLMProviderError(f"LLM provider error (status {response.status_code})")

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

        Supports one automated repair retry if the first attempt fails guardrails.
        """
        if not self.api_key or not self.api_key.strip():
            raise LLMProviderError("NVIDIA_API_KEY is not configured on the service.")

        total_deadline = timeout or settings.total_request_deadline_seconds
        start_time = time.perf_counter()
        first_call_timeout = min(settings.llm_timeout_seconds, total_deadline - 3.0)

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

        # First attempt
        raw_content = self._call_api(messages, timeout=first_call_timeout)
        elapsed_first = time.perf_counter() - start_time
        logger.info("[%s] LLM first attempt completed in %.2fs", scenario_id, elapsed_first)

        try:
            parsed_data = json.loads(raw_content)
            validated = validate_interpretations(
                parsed_data,
                note_count=len(operator_notes),
                battery_capacity=battery_capacity_kwh,
                operator_notes=operator_notes,
            )
            return validated
        except (json.JSONDecodeError, DirectiveValidationError) as first_err:
            logger.warning("[%s] First interpretation attempt failed validation: %s", scenario_id, first_err)

            # Check remaining time for repair attempt
            remaining_time = total_deadline - (time.perf_counter() - start_time) - 2.0
            if remaining_time < 3.0:
                raise LLMProviderError(f"LLM output violated guardrails and time budget exhausted: {first_err}") from first_err

            # Repair attempt
            logger.info("[%s] Attempting LLM repair call with %.1fs remaining budget...", scenario_id, remaining_time)
            repair_messages = list(messages)
            repair_messages.append({"role": "assistant", "content": raw_content})
            repair_messages.append({
                "role": "user",
                "content": (
                    f"Your response failed validation: {first_err}. "
                    "Remember: start-inclusive and strictly end-exclusive hours! "
                    "no_charge_window and no_discharge_window MUST have ONLY 'hours' in structured_adjustment. "
                    "Return ONLY the corrected JSON object strictly."
                ),
            })

            repaired_content = self._call_api(repair_messages, timeout=remaining_time)
            elapsed_repair = time.perf_counter() - start_time
            logger.info("[%s] LLM repair call completed at %.2fs", scenario_id, elapsed_repair)

            try:
                repaired_data = json.loads(repaired_content)
                validated = validate_interpretations(
                    repaired_data,
                    note_count=len(operator_notes),
                    battery_capacity=battery_capacity_kwh,
                    operator_notes=operator_notes,
                )
                return validated
            except (json.JSONDecodeError, DirectiveValidationError) as repair_err:
                logger.error("[%s] Repair attempt also failed: %s", scenario_id, repair_err)
                raise LLMProviderError(f"LLM output violated guardrails after repair: {repair_err}") from repair_err


# Module singleton instance
interpreter = LLMInterpreter()
