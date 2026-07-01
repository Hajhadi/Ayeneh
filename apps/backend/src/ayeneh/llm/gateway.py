"""Unified LLM Gateway — single interface for all LLM operations."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from ayeneh.llm.types import (
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMUsage,
    SafetyConfig,
    StreamChunk,
    ToolDefinition,
)


class LLMGateway(ABC):
    """Unified interface for all LLM operations.

    No agent may call any LLM provider directly.
    All LLM access goes through this gateway.
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
        *,
        request_id: str | None = None,
    ) -> LLMResponse:
        """Send a chat completion request."""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
        *,
        request_id: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion response token by token."""
        ...

    @abstractmethod
    async def embed(self, texts: list[str], model: str = "") -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...

    @abstractmethod
    def supports_structured_output(self) -> bool:
        """Whether the underlying provider supports JSON mode."""
        ...

    @abstractmethod
    def supports_tool_calling(self) -> bool:
        """Whether the underlying provider supports tool calling."""
        ...

    @abstractmethod
    def get_model_info(self, model: str | None = None) -> dict[str, Any]:
        """Return metadata about the current or specified model."""
        ...

    @abstractmethod
    async def cancel(self, request_id: str) -> bool:
        """Cancel an in-progress request. Returns True if cancelled."""
        ...

    async def __aenter__(self) -> LLMGateway:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


@dataclass
class LLMUsageTracker:
    """Tracks cumulative usage across all requests."""

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    request_count: int = 0

    def record(self, usage: LLMUsage) -> None:
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.total_tokens += usage.total_tokens
        self.total_cost_usd += usage.estimated_cost_usd
        self.request_count += 1

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "request_count": self.request_count,
            "avg_tokens_per_request": (
                self.total_tokens // max(self.request_count, 1)
            ),
        }


def generate_request_id() -> str:
    return str(uuid.uuid4())[:12]
