"""Gemini provider — Google Gemini API integration via httpx."""

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
)

logger = structlog.get_logger(__name__)


class GeminiProvider(BaseProvider):
    """Google Gemini API provider."""

    provider_name: str = "gemini"

    def __init__(self, api_key: str = "", model: str = "gemini-1.5-flash", **kwargs: Any) -> None:
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

        contents = []
        for m in messages:
            role = "user" if m.role in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": m.content or ""}]})

        for attempt in range(self.max_retries + 1):
            start = time.monotonic()
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                payload = {
                    "contents": contents,
                    "generationConfig": {
                        "temperature": cfg.temperature,
                        "maxOutputTokens": cfg.max_tokens,
                    },
                }
                async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                latency = (time.monotonic() - start) * 1000
                candidates = data.get("candidates", [])
                content = ""
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    content = "".join(p.get("text", "") for p in parts)

                usage_data = data.get("usageMetadata", {})
                prompt_t = usage_data.get("promptTokenCount", 0)
                comp_t = usage_data.get("candidatesTokenCount", 0)
                usage = LLMUsage(
                    prompt_tokens=prompt_t, completion_tokens=comp_t,
                    total_tokens=prompt_t + comp_t,
                )
                usage.estimated_cost_usd = self._estimate_cost(model, prompt_t, comp_t)
                self._record_cost(model, prompt_t, comp_t, latency, self.provider_name)

                return LLMResponse(
                    content=content, finish_reason="stop", usage=usage,
                    model=model, provider=self.provider_name,
                    latency_ms=latency, retries=attempt, request_id=rid,
                )
            except Exception as exc:
                logger.warning("gemini_error", error=str(exc), attempt=attempt)
                if attempt >= self.max_retries:
                    raise
                await asyncio.sleep(self.retry_base_delay_ms * (2 ** attempt) / 1000)
        raise RuntimeError("Gemini retry exhausted")

    async def chat_stream(
        self, messages: list[LLMMessage], config: LLMConfig | None = None, *,
        request_id: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        import httpx

        cfg = self._make_config(config)
        model = cfg.model or self.model
        contents = []
        for m in messages:
            role = "user" if m.role in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": m.content or ""}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={self.api_key}&alt=sse"
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": cfg.temperature, "maxOutputTokens": cfg.max_tokens},
        }

        try:
            async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    buffer = ""
                    async for raw in resp.aiter_text():
                        buffer += raw
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if line.startswith("data: "):
                                data = json.loads(line[6:])
                                candidates = data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for p in parts:
                                        text = p.get("text", "")
                                        if text:
                                            yield StreamChunk(delta=text)
        except Exception as exc:
            logger.exception("gemini_stream_error", error=str(exc))
            yield StreamChunk(finish_reason="error")

    async def embed(self, texts: list[str], model: str = "") -> list[list[float]]:
        import httpx

        emb_model = model or "text-embedding-004"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{emb_model}:embedContent?key={self.api_key}"
        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for text in texts:
                resp = await client.post(url, json={"content": {"parts": [{"text": text}]}})
                resp.raise_for_status()
                results.append(resp.json()["embedding"]["values"])
        return results

    def supports_structured_output(self) -> bool:
        return True

    def supports_tool_calling(self) -> bool:
        return True

    def get_model_info(self, model: str | None = None) -> dict[str, Any]:
        return {"model": model or self.model, "provider": self.provider_name, "max_tokens": 1000000}
