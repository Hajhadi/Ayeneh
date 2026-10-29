"""AI Router — single entry point for all AI requests with capability-based routing."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

import structlog

from ayeneh.ai_router.capabilities import (
    Capability,
    get_required_capabilities,
    score_provider,
)
from ayeneh.ai_router.metrics import MetricsCollector
from ayeneh.ai_router.policies import PolicyEngine
from ayeneh.ai_router.registry import ProviderRegistry
from ayeneh.ai_router.types import (
    AITask,
    RoutingDecision,
    RoutingMetrics,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from ayeneh.ai_router.retry import RetryManager

logger = structlog.get_logger(__name__)


class AIRouter:
    """Single entry point for all AI requests.

    Capability-based routing:
    1. Task declares required capabilities
    2. Providers advertise their capabilities
    3. Policy engine scores providers
    4. Best provider selected with fallback
    """

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        policy_engine: PolicyEngine | None = None,
        metrics: MetricsCollector | None = None,
        retry_manager: RetryManager | None = None,
    ) -> None:
        self._registry = registry or ProviderRegistry()
        self._policy_engine = policy_engine or PolicyEngine()
        self._metrics = metrics or MetricsCollector()
        self._retry_manager = retry_manager
        self._cache: dict[str, Any] = {}

    @property
    def registry(self) -> ProviderRegistry:
        return self._registry

    @property
    def metrics(self) -> MetricsCollector:
        return self._metrics

    async def route(
        self,
        task: AITask,
        *,
        force_provider: str | None = None,
    ) -> RoutingDecision:
        """Route an AI task using capability-based scoring.

        This is the ONLY public API for AI access.
        """
        start = time.monotonic()

        # Get required capabilities for this task
        required_caps = get_required_capabilities(task.task_type.value)

        # Force provider if specified
        if force_provider:
            provider = self._registry.get(force_provider)
            if provider:
                provider_caps = provider.get_capabilities()
                return RoutingDecision(
                    task_type=task.task_type,
                    chosen_provider=force_provider,
                    chosen_model=getattr(provider, "_model", "unknown"),
                    routing_reason=f"forced provider: {force_provider}",
                    policy_used="forced",
                    estimated_cost=provider.estimate_cost(
                        task.max_tokens // 2, task.max_tokens // 2
                    ),
                    estimated_tokens=task.max_tokens,
                    confidence=1.0,
                )

        # Score all healthy providers
        candidates = []
        for name, provider in self._registry.get_healthy().items():
            provider_caps = provider.get_capabilities()

            # Check if provider has OFFLINE capability for offline mode
            if task.context.get("offline_mode") and not provider_caps.supports_any(
                [
                    Capability.OFFLINE,
                    Capability.LOCAL_ONLY,
                ]
            ):
                continue

            health = self._registry.get_health(name)
            cost = provider.estimate_cost(task.max_tokens // 2, task.max_tokens // 2)
            latency = provider.estimate_latency_ms(task.max_tokens)

            # Get policy preference
            policy_pref = self._policy_engine.get_provider_preference(
                task.task_type, provider.provider_type
            )

            score = score_provider(
                provider_caps,
                required_caps,
                latency_ms=latency,
                cost_usd=cost,
                success_rate=health.success_rate,
                is_healthy=health.is_healthy,
                policy_preference=policy_pref,
            )

            candidates.append((name, provider, score))

        # Sort by total score descending
        candidates.sort(key=lambda x: x[2].total_score, reverse=True)

        if not candidates:
            logger.error("no_provider_available", task_type=task.task_type)
            return RoutingDecision(
                task_type=task.task_type,
                chosen_provider="none",
                chosen_model="",
                routing_reason="no providers available",
                policy_used="default",
            )

        # Select best provider
        best_name, best_provider, best_score = candidates[0]
        alternatives = [name for name, _, _ in candidates[1:]]

        # Build fallback list from remaining candidates
        fallbacks = [name for name, _, _ in candidates[1:]]

        decision = RoutingDecision(
            task_type=task.task_type,
            chosen_provider=best_name,
            chosen_model=getattr(best_provider, "_model", "unknown"),
            routing_reason=f"capability score: {best_score.total_score:.3f}",
            policy_used="capability_based",
            alternative_providers=alternatives,
            estimated_cost=best_provider.estimate_cost(task.max_tokens // 2, task.max_tokens // 2),
            estimated_tokens=task.max_tokens,
            confidence=best_score.total_score,
            fallbacks_used=fallbacks,
        )

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "task_routed",
            task_type=task.task_type,
            provider=best_name,
            model=decision.chosen_model,
            score=round(best_score.total_score, 3),
            coverage=round(best_score.capability_coverage, 3),
            matched=best_score.matched_capabilities,
            missing=best_score.missing_capabilities,
            duration_ms=round(duration_ms, 2),
        )

        return decision

    async def chat(
        self,
        task: AITask,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Route and execute a chat request with retry and fallback."""
        decision = await self.route(task)
        provider = self._registry.get(decision.chosen_provider)

        if provider is None:
            return {"choices": [{"message": {"content": "No AI provider available."}}]}

        start = time.monotonic()
        last_error: Exception | None = None

        # Try primary provider with retries
        providers_to_try = [
            (decision.chosen_provider, provider, False),
            *[(name, self._registry.get(name), True) for name in decision.fallbacks_used],
        ]

        for provider_name, prov, is_fallback in providers_to_try:
            if prov is None:
                continue

            max_attempts = (self._retry_manager.max_retries + 1) if self._retry_manager else 1

            for attempt in range(max_attempts):
                try:
                    result = await prov.chat(
                        messages,
                        model=getattr(prov, "_model", ""),
                        temperature=task.temperature,
                        max_tokens=task.max_tokens,
                    )
                    latency_ms = (time.monotonic() - start) * 1000

                    usage = result.get("usage", {})
                    tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                    cost = prov.estimate_cost(
                        usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
                    )

                    self._metrics.record_routing(
                        RoutingMetrics(
                            task_type=task.task_type,
                            provider=provider_name,
                            model=getattr(prov, "_model", ""),
                            latency_ms=latency_ms,
                            tokens_used=tokens,
                            cost_usd=cost,
                            success=True,
                            fallback_used=is_fallback or bool(decision.fallbacks_used),
                        )
                    )

                    return result

                except Exception as exc:
                    last_error = exc
                    latency_ms = (time.monotonic() - start) * 1000
                    self._metrics.record_routing(
                        RoutingMetrics(
                            task_type=task.task_type,
                            provider=provider_name,
                            model=getattr(prov, "_model", ""),
                            latency_ms=latency_ms,
                            success=False,
                            fallback_used=is_fallback,
                        )
                    )

                    # Check if we should retry the same provider
                    if self._retry_manager and self._retry_manager.should_retry(attempt, exc):
                        delay = self._retry_manager.get_delay(attempt)
                        logger.warning(
                            "retrying_provider",
                            provider=provider_name,
                            attempt=attempt + 1,
                            delay_ms=round(delay * 1000, 1),
                        )
                        await asyncio.sleep(delay)
                        continue

                    # Not retryable or retries exhausted — try next provider
                    break

        logger.exception("chat_failed", provider=decision.chosen_provider, error=str(last_error))
        return {"choices": [{"message": {"content": f"Error: {str(last_error)[:200]}"}}]}

    async def chat_stream(
        self,
        task: AITask,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[dict[str, Any]]:
        """Route and stream a chat request with fallback on error."""
        decision = await self.route(task)
        provider = self._registry.get(decision.chosen_provider)

        if provider is None:
            yield {"choices": [{"delta": {"content": "No AI provider available."}}]}
            return

        providers_to_try = [
            (decision.chosen_provider, provider),
            *[(name, self._registry.get(name)) for name in decision.fallbacks_used],
        ]

        last_error: Exception | None = None

        for provider_name, prov in providers_to_try:
            if prov is None:
                continue

            try:
                async for chunk in prov.chat_stream(
                    messages,
                    model=getattr(prov, "_model", ""),
                    temperature=task.temperature,
                    max_tokens=task.max_tokens,
                ):
                    yield chunk
                return  # success
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "stream_provider_failed",
                    provider=provider_name,
                    error=str(exc)[:200],
                )
                continue

        logger.exception("stream_failed", provider=decision.chosen_provider, error=str(last_error))
        yield {"choices": [{"delta": {"content": f"Error: {str(last_error)[:200]}"}}]}

    def get_metrics(self) -> dict[str, Any]:
        """Get routing metrics."""
        return self._metrics.get_summary()

    def get_provider_status(self) -> dict[str, Any]:
        """Get status of all providers."""
        return self._registry.list_providers()
