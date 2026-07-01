"""Multi-model routing — task-based model selection with fallback chains."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from ayeneh.llm.gateway import LLMGateway
from ayeneh.llm.types import LLMConfig

logger = structlog.get_logger(__name__)


@dataclass
class RouteEntry:
    task: str
    model: str
    provider: str = ""
    config_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass
class FallbackChain:
    models: list[str]
    current_index: int = 0

    def current(self) -> str | None:
        if self.current_index < len(self.models):
            return self.models[self.current_index]
        return None

    def advance(self) -> str | None:
        self.current_index += 1
        return self.current()

    def reset(self) -> None:
        self.current_index = 0


class ModelRouter:
    """Routes requests to appropriate models based on task type.

    Supports:
    - Task-based routing (conversation → GPT, reflection → Claude)
    - Fallback chains (GPT → Claude → Gemini → failure)
    - Configuration-driven model selection
    """

    def __init__(self) -> None:
        self._routes: dict[str, RouteEntry] = {}
        self._fallbacks: dict[str, FallbackChain] = {}
        self._gateways: dict[str, LLMGateway] = {}
        self._default_model: str = "gpt-4o-mini"

    def register_route(self, task: str, model: str, provider: str = "", **overrides: Any) -> None:
        self._routes[task] = RouteEntry(task=task, model=model, provider=provider, config_overrides=overrides)

    def register_fallback(self, task: str, models: list[str]) -> None:
        self._fallbacks[task] = FallbackChain(models=models)

    def register_gateway(self, provider: str, gateway: LLMGateway) -> None:
        self._gateways[provider] = gateway

    def set_default_model(self, model: str) -> None:
        self._default_model = model

    def select_model(self, task: str) -> tuple[str, LLMConfig]:
        route = self._routes.get(task)
        if route:
            config = LLMConfig(model=route.model, **route.config_overrides)
            return route.model, config

        fallback = self._fallbacks.get(task)
        if fallback:
            model = fallback.current()
            if model:
                return model, LLMConfig(model=model)

        return self._default_model, LLMConfig(model=self._default_model)

    def get_gateway(self, task: str) -> LLMGateway | None:
        route = self._routes.get(task)
        if route and route.provider:
            return self._gateways.get(route.provider)

        for gw in self._gateways.values():
            return gw
        return None

    def advance_fallback(self, task: str) -> str | None:
        fallback = self._fallbacks.get(task)
        if fallback:
            return fallback.advance()
        return None

    def reset_fallback(self, task: str) -> None:
        fallback = self._fallbacks.get(task)
        if fallback:
            fallback.reset()

    def get_routing_table(self) -> dict[str, str]:
        return {task: entry.model for task, entry in self._routes.items()}


class FallbackExecutor:
    """Executes requests with automatic fallback across models."""

    def __init__(self, router: ModelRouter, gateways: dict[str, LLMGateway]) -> None:
        self._router = router
        self._gateways = gateways

    async def execute_with_fallback(
        self,
        task: str,
        messages: list[Any],
        config: LLMConfig | None = None,
        max_fallbacks: int = 3,
    ) -> Any:
        model, base_config = self._router.select_model(task)
        last_error: Exception | None = None

        for attempt in range(max_fallbacks + 1):
            cfg = LLMConfig(
                model=model,
                temperature=config.temperature if config else base_config.temperature,
                max_tokens=config.max_tokens if config else base_config.max_tokens,
                timeout_seconds=config.timeout_seconds if config else base_config.timeout_seconds,
            )

            gateway = self._find_gateway(model)
            if gateway is None:
                last_error = RuntimeError(f"No gateway for model {model}")
                model = self._router.advance_fallback(task)
                if model is None:
                    break
                continue

            try:
                result = await gateway.chat(messages, cfg)
                self._router.reset_fallback(task)
                return result
            except Exception as exc:
                logger.warning("fallback_triggered", model=model, error=str(exc), attempt=attempt)
                last_error = exc
                model = self._router.advance_fallback(task)
                if model is None:
                    break

        raise last_error or RuntimeError("All fallbacks exhausted")

    def _find_gateway(self, model: str) -> LLMGateway | None:
        for gw in self._gateways.values():
            info = gw.get_model_info()
            if info.get("model") == model or model in info.get("model", ""):
                return gw
        for gw in self._gateways.values():
            return gw
        return None
