"""Base provider — common logic for all LLM providers."""

from __future__ import annotations

import time
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from ayeneh.llm.gateway import LLMGateway
from ayeneh.llm.types import (
    CostEntry,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMUsage,
    StreamChunk,
    ToolDefinition,
)

import structlog

logger = structlog.get_logger(__name__)

COST_TABLE: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15 / 1000, 0.60 / 1000),
    "gpt-4o": (2.50 / 1000, 10.00 / 1000),
    "gpt-4-turbo": (10.00 / 1000, 30.00 / 1000),
    "gpt-3.5-turbo": (0.50 / 1000, 1.50 / 1000),
    "claude-3-5-sonnet-20241022": (3.00 / 1000, 15.00 / 1000),
    "claude-3-haiku-20240307": (0.25 / 1000, 1.25 / 1000),
    "claude-3-opus-20240229": (15.00 / 1000, 75.00 / 1000),
    "gemini-1.5-flash": (0.075 / 1000, 0.30 / 1000),
    "gemini-1.5-pro": (1.25 / 1000, 5.00 / 1000),
}


@dataclass
class BaseProvider(LLMGateway):
    """Base class with common provider logic: retry, timeout, cost tracking."""

    model: str = ""
    api_key: str = ""
    base_url: str = ""
    default_config: LLMConfig = field(default_factory=LLMConfig)
    max_retries: int = 3
    retry_base_delay_ms: float = 500.0
    cost_entries: list[CostEntry] = field(default_factory=list)
    _active_requests: dict[str, Any] = field(default_factory=dict)

    def _make_config(self, config: LLMConfig | None) -> LLMConfig:
        if config is None:
            return self.default_config
        return config

    def _estimate_cost(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        rates = COST_TABLE.get(model, COST_TABLE.get("gpt-4o-mini"))
        if rates is None:
            return 0.0
        return prompt_tokens * rates[0] + completion_tokens * rates[1]

    def _record_cost(
        self, model: str, prompt_tokens: int, completion_tokens: int,
        latency_ms: float, provider: str,
    ) -> float:
        cost = self._estimate_cost(model, prompt_tokens, completion_tokens)
        self.cost_entries.append(CostEntry(
            provider=provider, model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost, latency_ms=latency_ms,
            timestamp=time.time(),
        ))
        return cost

    def get_cost_summary(self) -> dict[str, Any]:
        total_prompt = sum(e.prompt_tokens for e in self.cost_entries)
        total_completion = sum(e.completion_tokens for e in self.cost_entries)
        total_cost = sum(e.cost_usd for e in self.cost_entries)
        total_latency = sum(e.latency_ms for e in self.cost_entries)
        return {
            "total_requests": len(self.cost_entries),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(total_latency / max(len(self.cost_entries), 1), 2),
        }

    async def cancel(self, request_id: str) -> bool:
        if request_id in self._active_requests:
            task = self._active_requests.pop(request_id)
            if hasattr(task, "cancel"):
                task.cancel()
            return True
        return False
