"""Response composer — assembles final response from agent outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ayeneh.agents.base import AgentOutput

logger = structlog.get_logger(__name__)


@dataclass
class RuntimeResponse:
    """Final response assembled by the Composer."""

    response_text: str = ""
    memories: list[dict[str, Any]] = field(default_factory=list)
    insights: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    knowledge_chunks: list[dict[str, Any]] = field(default_factory=list)
    patterns: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    skipped_steps: list[str] = field(default_factory=list)


class ResponseComposer:
    """Assembles the final response from agent outputs."""

    def compose(
        self,
        agent_outputs: dict[str, AgentOutput],
        skipped_steps: list[str] | None = None,
    ) -> RuntimeResponse:
        response = RuntimeResponse(skipped_steps=skipped_steps or [])

        for _step_id, output in agent_outputs.items():
            if output.status != "success":
                continue
            data = output.data
            if data.get("response_text"):
                response.response_text = data["response_text"]
            if "memories" in data:
                response.memories.extend(data["memories"] if isinstance(data["memories"], list) else [])
            if "insights" in data:
                response.insights.extend(data["insights"] if isinstance(data["insights"], list) else [])
            if "observations" in data:
                response.observations.extend(data["observations"] if isinstance(data["observations"], list) else [])
            if "book_chunks" in data:
                response.knowledge_chunks.extend(data["book_chunks"] if isinstance(data["book_chunks"], list) else [])
            if "patterns" in data:
                response.patterns.extend(data["patterns"] if isinstance(data["patterns"], list) else [])

        response.metadata = {
            "total_agent_outputs": len(agent_outputs),
            "successful_outputs": sum(1 for o in agent_outputs.values() if o.status == "success"),
            "skipped_steps": len(response.skipped_steps),
        }

        logger.info(
            "response_composed",
            text_length=len(response.response_text),
            memories=len(response.memories),
            insights=len(response.insights),
        )
        return response
