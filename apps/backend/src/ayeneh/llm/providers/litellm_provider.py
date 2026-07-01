"""LiteLLM provider — universal gateway via litellm library."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator

import structlog

from ayeneh.llm.providers.base import BaseProvider
from ayeneh.llm.types import (
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMUsage,
    StreamChunk,
    ToolCall,
    ToolDefinition,
)

logger = structlog.get_logger(__name__)


class LiteLLMProvider(BaseProvider):
    """Production provider using litellm as the universal LLM gateway.

    Supports OpenAI, Anthropic, Gemini, and many others through litellm.
    """

    provider_name: str = "litellm"

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = "", **kwargs: Any) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self.default_config = LLMConfig(model=model)

    async def chat(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
        *,
        request_id: str | None = None,
    ) -> LLMResponse:
        cfg = self._make_config(config)
        rid = request_id or ""

        for attempt in range(self.max_retries + 1):
            start = time.monotonic()
            try:
                import litellm
                litellm.api_key = self.api_key or None

                kwargs: dict[str, Any] = {
                    "model": cfg.model or self.model,
                    "messages": [m.to_dict() for m in messages],
                    "temperature": cfg.temperature,
                    "max_tokens": cfg.max_tokens,
                    "timeout": cfg.timeout_seconds,
                }
                if cfg.stop:
                    kwargs["stop"] = cfg.stop
                if cfg.response_format == "json":
                    kwargs["response_format"] = {"type": "json_object"}
                if cfg.tools:
                    kwargs["tools"] = [t.to_dict() for t in cfg.tools]
                    kwargs["tool_choice"] = cfg.tool_choice

                result = await asyncio.wait_for(
                    asyncio.to_thread(litellm.completion, **kwargs),
                    timeout=cfg.timeout_seconds,
                )

                latency = (time.monotonic() - start) * 1000
                choice = result.choices[0]
                content = choice.message.content or ""
                finish = choice.finish_reason or "stop"

                tool_calls = []
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        tool_calls.append(ToolCall(
                            id=tc.id or "",
                            name=tc.function.name,
                            arguments=tc.function.arguments or "{}",
                        ))

                usage_data = getattr(result, "usage", None)
                prompt_toks = getattr(usage_data, "prompt_tokens", 0) if usage_data else 0
                comp_toks = getattr(usage_data, "completion_tokens", 0) if usage_data else 0
                cached = getattr(usage_data, "prompt_tokens_cached", 0) if usage_data else 0

                usage = LLMUsage(
                    prompt_tokens=prompt_toks,
                    completion_tokens=comp_toks,
                    total_tokens=prompt_toks + comp_toks,
                    cached_tokens=cached,
                )
                usage.estimated_cost_usd = self._estimate_cost(
                    cfg.model or self.model, prompt_toks, comp_toks,
                )
                self._record_cost(
                    cfg.model or self.model, prompt_toks, comp_toks,
                    latency, self.provider_name,
                )

                return LLMResponse(
                    content=content, tool_calls=tool_calls,
                    finish_reason=finish, usage=usage,
                    model=cfg.model or self.model,
                    provider=self.provider_name,
                    latency_ms=latency, retries=attempt,
                    request_id=rid,
                )

            except asyncio.TimeoutError:
                logger.warning("llm_timeout", model=cfg.model, attempt=attempt)
                if attempt >= self.max_retries:
                    raise
            except Exception as exc:
                logger.warning("llm_error", error=str(exc), attempt=attempt)
                if attempt >= self.max_retries:
                    raise
                delay = self.retry_base_delay_ms * (2 ** attempt) / 1000
                await asyncio.sleep(delay)

        raise RuntimeError("LLM retry exhausted")

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
        *,
        request_id: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        cfg = self._make_config(config)

        try:
            import litellm
            litellm.api_key = self.api_key or None

            kwargs: dict[str, Any] = {
                "model": cfg.model or self.model,
                "messages": [m.to_dict() for m in messages],
                "temperature": cfg.temperature,
                "max_tokens": cfg.max_tokens,
                "timeout": cfg.timeout_seconds,
                "stream": True,
            }
            if cfg.tools:
                kwargs["tools"] = [t.to_dict() for t in cfg.tools]

            response = await asyncio.to_thread(litellm.completion, **kwargs)

            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta:
                    content = getattr(delta, "content", None) or ""
                    if content:
                        yield StreamChunk(delta=content)

                    finish = getattr(chunk.choices[0], "finish_reason", None)
                    if finish:
                        yield StreamChunk(finish_reason=finish)

                usage_data = getattr(chunk, "usage", None)
                if usage_data:
                    yield StreamChunk(usage=LLMUsage(
                        prompt_tokens=getattr(usage_data, "prompt_tokens", 0),
                        completion_tokens=getattr(usage_data, "completion_tokens", 0),
                        total_tokens=getattr(usage_data, "total_tokens", 0),
                    ))

        except Exception as exc:
            logger.exception("llm_stream_error", error=str(exc))
            yield StreamChunk(finish_reason="error")

    async def embed(self, texts: list[str], model: str = "") -> list[list[float]]:
        import litellm
        litellm.api_key = self.api_key or None
        emb_model = model or "text-embedding-3-small"
        result = await asyncio.to_thread(
            litellm.embedding, model=emb_model, input=texts,
        )
        return [item["embedding"] for item in result.data]

    def supports_structured_output(self) -> bool:
        return True

    def supports_tool_calling(self) -> bool:
        return True

    def get_model_info(self, model: str | None = None) -> dict[str, Any]:
        m = model or self.model
        rates = self._estimate_cost.__code__.co_consts
        return {
            "model": m, "provider": self.provider_name,
            "max_tokens": 128000,
        }
