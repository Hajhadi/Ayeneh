"""Prompt execution pipeline — template → context → LLM → parse → validate → repair."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from ayeneh.llm.structured import StructuredOutputParser
from ayeneh.llm.types import LLMConfig, LLMMessage, LLMResponse

logger = structlog.get_logger(__name__)


@dataclass
class PromptTemplate:
    name: str
    system_prompt: str = ""
    user_template: str = ""
    response_schema: type | None = None
    config: LLMConfig = field(default_factory=LLMConfig)
    tools: list[Any] = field(default_factory=list)


@dataclass
class PipelineResult:
    response: LLMResponse
    parsed_output: Any = None
    validation_errors: list[str] = field(default_factory=list)
    repair_attempts: int = 0


class PromptPipeline:
    """Executes the full prompt pipeline:
    Template → Context Assembly → LLM → Structured Parse → Validate → Repair → Final Object
    """

    def __init__(self, gateway: Any, structured_parser: StructuredOutputParser | None = None) -> None:
        self._gateway = gateway
        self._parser = structured_parser or StructuredOutputParser()

    async def execute(
        self,
        template: PromptTemplate,
        context: dict[str, Any],
        response_schema: type | None = None,
    ) -> PipelineResult:
        schema = response_schema or template.response_schema

        messages = self._assemble_messages(template, context)
        config = template.config
        if schema:
            config.response_format = "json"

        response = await self._gateway.chat(messages, config)

        parsed_output = None
        validation_errors: list[str] = []
        repair_attempts = 0

        if schema:
            try:
                parsed_output = await self._parser.parse_and_validate(
                    response, schema, self._gateway, messages, config,
                )
            except Exception as exc:
                validation_errors.append(str(exc))
                logger.warning("structured_parse_failed", error=str(exc))

        return PipelineResult(
            response=response,
            parsed_output=parsed_output,
            validation_errors=validation_errors,
            repair_attempts=repair_attempts,
        )

    def _assemble_messages(
        self, template: PromptTemplate, context: dict[str, Any]
    ) -> list[LLMMessage]:
        messages: list[LLMMessage] = []

        if template.system_prompt:
            system_text = template.system_prompt
            for key, value in context.items():
                system_text = system_text.replace(f"{{{{{key}}}}}", str(value))
            messages.append(LLMMessage(role="system", content=system_text))

        if template.user_template:
            user_text = template.user_template
            for key, value in context.items():
                user_text = user_text.replace(f"{{{{{key}}}}}", str(value))
            messages.append(LLMMessage(role="user", content=user_text))

        return messages
