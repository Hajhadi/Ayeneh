"""LLM client — wraps LiteLLM for chat completions and embeddings."""

from __future__ import annotations


class LLMClient:
    """Stateless LLM client for chat and embedding calls."""

    async def chat(self, model: str, messages: list[dict], **kwargs: object) -> dict:
        """Placeholder — will call LiteLLM chat completion."""
        return {"choices": [{"message": {"content": ""}}]}

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        """Placeholder — will call LiteLLM embedding endpoint."""
        return [[]]
