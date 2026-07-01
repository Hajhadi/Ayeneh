"""OpenAI provider — direct OpenAI API integration."""

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


class OpenAIProvider(BaseProvider):
    """Direct OpenAI API provider using httpx."""

    provider_name: str = "openai"

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini", **kwargs: Any) -> None:
        super().__init__(api_key=api_key, model=model, **kwargs)
        self.default_config = LLMConfig(model=model)

    async def chat(
        self,
        messages: list[LLMMessage],
        config: LLMConfig | None = None,
        *,
        request_id: str | None = None,
    ) -> LLMResponse:
        import httpx

        cfg = self._make_config(config)
        rid = request_id or ""
        model = cfg.model or self.model

        for attempt in range(self.max_retries + 1):
            start = time.monotonic()
            try:
                payload: dict[str, Any] = {
                    "model": model,
                    "messages": [m.to_dict() for m in messages],
                    "temperature": cfg.temperature,
                    "max_tokens": cfg.max_tokens,
                }
                if cfg.stop:
                    payload["stop"] = cfg.stop
                if cfg.response_format == "json":
                    payload["response_format"] = {"type": "json_object"}
                if cfg.tools:
                    payload["tools"] = [t.to_dict() for t in cfg.tools]
                    payload["tool_choice"] = cfg.tool_choice

                async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                latency = (time.monotonic() - start) * 1000
                choice = data["choices"][0]
                msg = choice["message"]
                content = msg.get("content") or ""
                finish = choice.get("finish_reason", "stop")

                tool_calls = []
                for tc in msg.get("tool_calls", []):
                    tool_calls.append(ToolCall(
                        id=tc["id"], name=tc["function"]["name"],
                        arguments=tc["function"]["arguments"],
                    ))

                usage_data = data.get("usage", {})
                prompt_t = usage_data.get("prompt_tokens", 0)
                comp_t = usage_data.get("completion_tokens", 0)
                usage = LLMUsage(
                    prompt_tokens=prompt_t, completion_tokens=comp_t,
                    total_tokens=prompt_t + comp_t,
                    cached_tokens=usage_data.get("prompt_tokens_details", {}).get("cached_tokens", 0),
                )
                usage.estimated_cost_usd = self._estimate_cost(model, prompt_t, comp_t)
                self._record_cost(model, prompt_t, comp_t, latency, self.provider_name)

                return LLMResponse(
                    content=content, tool_calls=tool_calls,
                    finish_reason=finish, usage=usage,
                    model=model, provider=self.provider_name,
                    latency_ms=latency, retries=attempt, request_id=rid,
                )

            except Exception as exc:
                logger.warning("openai_error", error=str(exc), attempt=attempt)
                if attempt >= self.max_retries:
                    raise
                await asyncio.sleep(self.retry_base_delay_ms * (2 ** attempt) / 1000)

        raise RuntimeError("OpenAI retry exhausted")

    async def chat_stream(
        self, messages: list[LLMMessage], config: LLMConfig | None = None, *,
        request_id: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        import httpx

        cfg = self._make_config(config)
        model = cfg.model or self.model
        payload: dict[str, Any] = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                ) as resp:
                    resp.raise_for_status()
                    buffer = ""
                    async for raw_chunk in resp.aiter_text():
                        buffer += raw_chunk
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if not line or line == "data: [DONE]":
                                continue
                            if line.startswith("data: "):
                                import json
                                data = json.loads(line[6:])
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield StreamChunk(delta=content)
                                finish = data["choices"][0].get("finish_reason")
                                if finish:
                                    yield StreamChunk(finish_reason=finish)
        except Exception as exc:
            logger.exception("openai_stream_error", error=str(exc))
            yield StreamChunk(finish_reason="error")

    async def embed(self, texts: list[str], model: str = "") -> list[list[float]]:
        import httpx

        emb_model = model or "text-embedding-3-small"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": emb_model, "input": texts},
            )
            resp.raise_for_status()
            return [item["embedding"] for item in resp.json()["data"]]

    def supports_structured_output(self) -> bool:
        return True

    def supports_tool_calling(self) -> bool:
        return True

    def get_model_info(self, model: str | None = None) -> dict[str, Any]:
        return {"model": model or self.model, "provider": self.provider_name, "max_tokens": 128000}
