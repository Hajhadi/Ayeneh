"""Structured output — Pydantic validation, JSON repair, schema-driven extraction."""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

import structlog

from ayeneh.llm.types import LLMConfig, LLMMessage, LLMResponse

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class StructuredOutputError(Exception):
    def __init__(self, message: str, raw_output: str = "", errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.raw_output = raw_output
        self.errors = errors or []


class StructuredOutputParser:
    """Parses LLM output into validated Pydantic models.

    Handles: JSON extraction from markdown, repair retries, schema validation.
    """

    def __init__(self, max_repair_attempts: int = 2) -> None:
        self._max_repairs = max_repair_attempts

    def extract_json(self, text: str) -> dict[str, Any] | list[Any]:
        """Extract JSON from potentially markdown-wrapped text."""
        text = text.strip()

        json_block = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if json_block:
            text = json_block.group(1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        brace_start = text.find("{")
        bracket_start = text.find("[")
        if brace_start >= 0:
            try:
                return json.loads(text[brace_start:])
            except json.JSONDecodeError:
                pass
        if bracket_start >= 0:
            try:
                return json.loads(text[bracket_start:])
            except json.JSONDecodeError:
                pass

        raise StructuredOutputError("No valid JSON found", raw_output=text)

    def validate_with_pydantic(self, data: dict[str, Any], schema: type) -> Any:
        """Validate data against a Pydantic model, returning typed instance."""
        try:
            return schema.model_validate(data)
        except Exception as exc:
            raise StructuredOutputError(
                f"Validation failed: {exc}", errors=[str(exc)],
            )

    async def parse_and_validate(
        self,
        response: LLMResponse,
        schema: type,
        gateway: Any | None = None,
        original_messages: list[LLMMessage] | None = None,
        config: LLMConfig | None = None,
    ) -> Any:
        """Parse LLM response into a validated Pydantic model.

        If parsing fails and a gateway is available, attempts repair
        by sending the error back to the LLM for correction.
        """
        raw = response.content
        last_error: StructuredOutputError | None = None

        for attempt in range(self._max_repairs + 1):
            try:
                data = self.extract_json(raw)
                if isinstance(data, dict):
                    return self.validate_with_pydantic(data, schema)
                if isinstance(data, list):
                    return [self.validate_with_pydantic(item, schema) for item in data]
            except StructuredOutputError as exc:
                last_error = exc
                if attempt < self._max_repairs and gateway and original_messages:
                    raw = await self._repair(
                        gateway, original_messages, config, raw, str(exc), attempt,
                    )

        raise last_error or StructuredOutputError("Parse failed after repairs")

    async def _repair(
        self,
        gateway: Any,
        messages: list[LLMMessage],
        config: LLMConfig | None,
        raw: str,
        error_msg: str,
        attempt: int,
    ) -> str:
        repair_messages = list(messages) + [
            LLMMessage(role="user", content=(
                f"Your previous output was invalid JSON.\n"
                f"Error: {error_msg}\n"
                f"Your output was:\n{raw[:500]}\n\n"
                f"Please output ONLY valid JSON matching the required schema. No markdown, no explanation."
            )),
        ]
        repair_config = LLMConfig(
            model=config.model if config else "",
            temperature=0.0,
            max_tokens=config.max_tokens if config else 2048,
        )
        try:
            result = await gateway.chat(repair_messages, repair_config)
            return result.content
        except Exception:
            return raw


async def extract_structured(
    gateway: Any,
    messages: list[LLMMessage],
    schema: type,
    config: LLMConfig | None = None,
    max_repairs: int = 2,
) -> Any:
    """Convenience function: send messages, parse, validate with repair."""
    parser = StructuredOutputParser(max_repair_attempts=max_repairs)
    json_config = LLMConfig(
        model=config.model if config else "",
        temperature=config.temperature if config else 0.0,
        max_tokens=config.max_tokens if config else 2048,
        response_format="json",
    ) if config else LLMConfig(response_format="json", temperature=0.0)

    response = await gateway.chat(messages, json_config)
    return await parser.parse_and_validate(response, schema, gateway, messages, config)
