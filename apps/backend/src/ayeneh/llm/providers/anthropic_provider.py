"""Anthropic provider — direct Anthropic API integration."""

from __future__ import annotations

import asyncio
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
)

logger = structlog.get_logger(__name__)


class AnthropicProvider(BaseProvider):
    """Direct Anthropic API provider using httpx."""

    provider_name: str = "anthropic"

    def __init__(self, api_key: str = "", model: str = "claude-3-5-sonnet-20241022", **kwargs: Any) -> None:
        super().__init__(api_key=api_key, model=model, **kwargs)
        self.default_config = LLMConfig(model=model)

    async def chat(
        self, messages: list[LLMMessage], config: LLMConfig | None = None, *,
        request_id: str | None = None,
    ) -> LLMResponse:
        import httpx

        cfg = self._make_config(config)
        rid = request_id or ""
        model = cfg.model or self.model

        system_msg = ""
        anthropic_msgs = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content or ""
            else:
                anthropic_msgs.append({"role": m.role, "content": m.content or ""})

        for attempt in range(self.max_retries + 1):
            start = time.monotonic()
            try:
                payload: dict[str, Any] = {
                    "model": model,
                    "messages": anthropic_msgs,
                    "max_tokens": cfg.max_tokens,
                    "temperature": cfg.temperature,
                }
                if system_msg:
                    payload["system"] = system_msg
                if cfg.stop:
                    payload["stop_sequences"] = cfg.stop

                async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
                    resp = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": self.api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                latency = (time.monotonic() - start) * 1000
                content = ""
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        content += block.get("text", "")

                finish = data.get("stop_reason", "end_turn")
                if finish == "end_turn":
                    finish = "stop"

                usage_data = data.get("usage", {})
                prompt_t = usage_data.get("input_tokens", 0)
                comp_t = usage_data.get("output_tokens", 0)
                usage = LLMUsage(
                    prompt_tokens=prompt_t, completion_tokens=comp_t,
                    total_tokens=prompt_t + comp_t,
                )
                usage.estimated_cost_usd = self._estimate_cost(model, prompt_t, comp_t)
                self._record_cost(model, prompt_t, comp_t, latency, self.provider_name)

                return LLMResponse(
                    content=content, finish_reason=finish, usage=usage,
                    model=model, provider=self.provider_name,
                    latency_ms=latency, retries=attempt, request_id=rid,
                )

            except Exception as exc:
                logger.warning("anthropic_error", error=str(exc), attempt=attempt)
                if attempt >= self.max_retries:
                    raise
                await asyncio.sleep(self.retry_base_delay_ms * (2 ** attempt) / 1000)

        raise RuntimeError("Anthropic retry exhausted")

    async def chat_stream(
        self, messages: list[LLMMessage], config: LLMConfig | None = None, *,
        request_id: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        import httpx

        cfg = self._make_config(config)
        model = cfg.model or self.model

        system_msg = ""
        anthropic_msgs = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content or ""
            else:
                anthropic_msgs.append({"role": m.role, "content": m.content or ""})

        payload: dict[str, Any] = {
            "model": model, "messages": anthropic_msgs,
            "max_tokens": cfg.max_tokens, "temperature": cfg.temperature, "stream": True,
        }
        if system_msg:
            payload["system"] = system_msg

        try:
            async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
                async with client.stream(
                    "POST", "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                    json=payload,
                ) as resp:
                    resp.raise_for_status()
                    async for raw in resp.aiter_text():
                        for line in raw.strip().split("\n"):
                            if line.startswith("data: "):
                                import json
                                data = json.loads(line[6:])
                                etype = data.get("type", "")
                                if etype == "content_block_delta":
                                    delta = data.get("delta", {})
                                    text = delta.get("text", "")
                                    if text:
                                        yield StreamChunk(delta=text)
                                elif etype == "message_stop":
                                    yield StreamChunk(finish_reason="stop")
        except Exception as exc:
            logger.exception("anthropic_stream_error", error=str(exc))
            yield StreamChunk(finish_reason="error")

    async def embed(self, texts: list[str], model: str = "") -> list[list[float]]:
        raise NotImplementedError("Anthropic does not provide embeddings. Use a different provider.")

    def supports_structured_output(self) -> bool:
        return True

    def supports_tool_calling(self) -> bool:
        return True

    def get_model_info(self, model: str | None = None) -> dict[str, Any]:
        return {"model": model or self.model, "provider": self.provider_name, "max_tokens": 200000}
