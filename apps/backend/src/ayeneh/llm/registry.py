"""Provider registry — dynamic provider resolution with automatic fallback."""

from __future__ import annotations

import structlog
from typing import Any

from ayeneh.config import Settings, get_settings
from ayeneh.llm.gateway import LLMGateway

logger = structlog.get_logger(__name__)


class ProviderRegistry:
    """Singleton registry that manages LLM provider instances.

    Providers self-register. Runtime resolves provider dynamically
    based on configuration. No hardcoded provider selection.
    """

    _instance: ProviderRegistry | None = None

    def __init__(self) -> None:
        self._providers: dict[str, LLMGateway] = {}
        self._fallback_chain: list[str] = []

    @classmethod
    def get_instance(cls) -> ProviderRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def register(self, name: str, gateway: LLMGateway) -> None:
        self._providers[name] = gateway
        logger.info("provider_registered", name=name)

    def get(self, name: str) -> LLMGateway | None:
        return self._providers.get(name)

    def get_or_default(self, name: str | None = None) -> LLMGateway:
        if name and name in self._providers:
            return self._providers[name]

        settings = get_settings()
        default = name or settings.llm_provider
        if default in self._providers:
            return self._providers[default]

        for fallback_name in self._fallback_chain:
            if fallback_name in self._providers:
                logger.warning("provider_fallback",
                               requested=default, using=fallback_name)
                return self._providers[fallback_name]

        if self._providers:
            first = next(iter(self._providers))
            logger.warning("provider_fallback_to_first",
                           requested=default, using=first)
            return self._providers[first]

        raise RuntimeError(f"No LLM provider available. Requested: {default}")

    def set_fallback_chain(self, chain: list[str]) -> None:
        self._fallback_chain = list(chain)

    def list_providers(self) -> dict[str, str]:
        return {name: type(gw).__name__ for name, gw in self._providers.items()}

    def has_provider(self, name: str) -> bool:
        return name in self._providers


def initialize_providers(settings: Settings | None = None) -> ProviderRegistry:
    """Create and register all configured providers from environment."""
    if settings is None:
        settings = get_settings()

    registry = ProviderRegistry.get_instance()
    registry.reset()
    registry = ProviderRegistry.get_instance()

    if settings.llm_litellm_api_key:
        try:
            from ayeneh.llm.providers.litellm_provider import LiteLLMProvider
            provider = LiteLLMProvider(
                model=settings.llm_default_model,
                api_key=settings.llm_litellm_api_key,
            )
            registry.register("litellm", provider)
        except Exception as exc:
            logger.warning("litellm_init_failed", error=str(exc))

    if settings.llm_openai_api_key:
        try:
            from ayeneh.llm.providers.openai_provider import OpenAIProvider
            provider = OpenAIProvider(
                model=settings.llm_default_model,
                api_key=settings.llm_openai_api_key,
                base_url=settings.llm_openai_base_url,
            )
            registry.register("openai", provider)
        except Exception as exc:
            logger.warning("openai_init_failed", error=str(exc))

    if settings.llm_anthropic_api_key:
        try:
            from ayeneh.llm.providers.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider(
                model=settings.llm_default_model,
                api_key=settings.llm_anthropic_api_key,
            )
            registry.register("anthropic", provider)
        except Exception as exc:
            logger.warning("anthropic_init_failed", error=str(exc))

    if settings.llm_gemini_api_key:
        try:
            from ayeneh.llm.providers.gemini_provider import GeminiProvider
            provider = GeminiProvider(
                model=settings.llm_default_model,
                api_key=settings.llm_gemini_api_key,
            )
            registry.register("gemini", provider)
        except Exception as exc:
            logger.warning("gemini_init_failed", error=str(exc))

    fallback = [m.strip() for m in settings.llm_fallback_models.split(",") if m.strip()]
    registry.set_fallback_chain(fallback)

    logger.info("providers_initialized",
                providers=list(registry.list_providers().keys()),
                fallback=fallback)
    return registry
