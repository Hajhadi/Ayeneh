"""Provider protocol plus adapters for the existing LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from ..capabilities import Capability, CapabilitySet
from ..types import ProviderType

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class AIProvider(ABC):
    provider_name = "provider"
    provider_type = ProviderType.CLOUD

    @abstractmethod
    def get_capabilities(self) -> CapabilitySet: ...
    @abstractmethod
    async def chat(self, messages, *, model="", temperature=0.7, max_tokens=2048): ...
    @abstractmethod
    async def chat_stream(
        self, messages, *, model="", temperature=0.7, max_tokens=2048
    ) -> AsyncIterator[dict[str, Any]]: ...
    async def health_check(self) -> bool:
        return True

    def estimate_cost(self, prompt_tokens, completion_tokens) -> float:
        return 0.0

    def estimate_latency_ms(self, max_tokens=2048) -> float:
        return 500.0


class _LLMAdapter(AIProvider):
    def __init__(self, provider, *, provider_type=ProviderType.CLOUD):
        self._provider = provider
        self._model = getattr(provider, "model", "")
        self.provider_type = provider_type

    def get_capabilities(self):
        return CapabilitySet(
            frozenset(
                [
                    Capability.STREAMING,
                    Capability.REASONING,
                    Capability.LONG_CONTEXT,
                    Capability.MULTILINGUAL,
                    Capability.HIGH_ACCURACY,
                    Capability.SUMMARIZATION,
                    Capability.EXTRACTION,
                    Capability.CLASSIFICATION,
                    Capability.CLOUD_ONLY,
                ]
            )
        )

    async def chat(self, messages, *, model="", temperature=0.7, max_tokens=2048):
        from ayeneh.container import ProviderGatewayAdapter

        return await ProviderGatewayAdapter(self._provider).chat(
            messages, model=model or self._model, temperature=temperature, max_tokens=max_tokens
        )

    async def chat_stream(self, messages, *, model="", temperature=0.7, max_tokens=2048):
        from ayeneh.container import ProviderGatewayAdapter

        async for chunk in ProviderGatewayAdapter(self._provider).chat_stream(
            messages, model=model or self._model, temperature=temperature, max_tokens=max_tokens
        ):
            yield chunk


class OpenAIProvider(_LLMAdapter):
    provider_name = "openai"

    def __init__(self, **kwargs):
        from ayeneh.llm.providers.openai_provider import OpenAIProvider as P

        super().__init__(P(**kwargs))


class AnthropicProvider(_LLMAdapter):
    provider_name = "anthropic"

    def __init__(self, **kwargs):
        from ayeneh.llm.providers.anthropic_provider import AnthropicProvider as P

        super().__init__(P(**kwargs))


class LMStudioProvider(_LLMAdapter):
    provider_name = "lmstudio"

    def __init__(self, **kwargs):
        from ayeneh.llm.providers.openai_provider import OpenAIProvider as P

        super().__init__(
            P(
                base_url=kwargs.get("base_url", "http://localhost:1234/v1"),
                api_key="lm-studio",
                model=kwargs.get("model", "local-model"),
            ),
            provider_type=ProviderType.LOCAL,
        )
