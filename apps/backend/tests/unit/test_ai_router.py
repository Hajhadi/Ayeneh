"""Tests for AI Router — capability-based routing, fallback, provider selection."""

from __future__ import annotations

import pytest

from ayeneh.ai_router import AIRouter, AITask, AITaskType, ProviderType
from ayeneh.ai_router.capabilities import (
    Capability, CapabilitySet, get_required_capabilities, score_provider,
)
from ayeneh.ai_router.policies import PolicyEngine, RoutingPolicy
from ayeneh.ai_router.providers import AIProvider
from ayeneh.ai_router.registry import ProviderRegistry
from ayeneh.ai_router.types import TaskComplexity


# ---------------------------------------------------------------------------
# Test Doubles
# ---------------------------------------------------------------------------


class FakeLocalProvider(AIProvider):
    """Fake local provider for testing."""

    provider_name: str = "fake_local"
    provider_type: ProviderType = ProviderType.LOCAL

    def get_capabilities(self) -> CapabilitySet:
        return CapabilitySet(capabilities=frozenset([
            Capability.STREAMING,
            Capability.EXTRACTION,
            Capability.CLASSIFICATION,
            Capability.SUMMARIZATION,
            Capability.MULTILINGUAL,
            Capability.LOW_COST,
            Capability.LOCAL_ONLY,
            Capability.OFFLINE,
            Capability.DETERMINISTIC,
        ]))

    async def chat(self, messages, *, model="", temperature=0.7, max_tokens=2048):
        return {"choices": [{"message": {"content": "Local response"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 20}}

    async def chat_stream(self, messages, *, model="", temperature=0.7, max_tokens=2048):
        yield {"choices": [{"delta": {"content": "Local "}}]}
        yield {"choices": [{"delta": {"content": "streaming"}}]}

    async def health_check(self):
        return True

    def estimate_cost(self, prompt_tokens, completion_tokens):
        return 0.0


class FakeCloudProvider(AIProvider):
    """Fake cloud provider for testing."""

    provider_name: str = "fake_cloud"
    provider_type: ProviderType = ProviderType.CLOUD

    def get_capabilities(self) -> CapabilitySet:
        return CapabilitySet(capabilities=frozenset([
            Capability.STRUCTURED_OUTPUT,
            Capability.JSON_MODE,
            Capability.TOOL_CALLING,
            Capability.STREAMING,
            Capability.LONG_CONTEXT,
            Capability.MULTILINGUAL,
            Capability.REASONING,
            Capability.SUMMARIZATION,
            Capability.EXTRACTION,
            Capability.CLASSIFICATION,
            Capability.HIGH_ACCURACY,
            Capability.CLOUD_ONLY,
        ]))

    async def chat(self, messages, *, model="", temperature=0.7, max_tokens=2048):
        return {"choices": [{"message": {"content": "Cloud response"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 20}}

    async def chat_stream(self, messages, *, model="", temperature=0.7, max_tokens=2048):
        yield {"choices": [{"delta": {"content": "Cloud "}}]}
        yield {"choices": [{"delta": {"content": "streaming"}}]}

    async def health_check(self):
        return True

    def estimate_cost(self, prompt_tokens, completion_tokens):
        return 0.001


# ---------------------------------------------------------------------------
# Capability Model Tests
# ---------------------------------------------------------------------------


def test_capability_set_supports():
    caps = CapabilitySet(capabilities=frozenset([Capability.STREAMING, Capability.REASONING]))
    assert caps.supports(Capability.STREAMING) is True
    assert caps.supports(Capability.VISION) is False


def test_capability_set_supports_all():
    caps = CapabilitySet(capabilities=frozenset([Capability.STREAMING, Capability.REASONING, Capability.LONG_CONTEXT]))
    assert caps.supports_all([Capability.STREAMING, Capability.REASONING]) is True
    assert caps.supports_all([Capability.STREAMING, Capability.VISION]) is False


def test_capability_set_coverage():
    caps = CapabilitySet(capabilities=frozenset([Capability.STREAMING, Capability.REASONING]))
    assert caps.coverage([Capability.STREAMING, Capability.REASONING]) == 1.0
    assert caps.coverage([Capability.STREAMING, Capability.VISION]) == 0.5
    assert caps.coverage([]) == 1.0


def test_get_required_capabilities():
    caps = get_required_capabilities("concept_discovery")
    assert Capability.EXTRACTION in caps
    assert Capability.MULTILINGUAL in caps
    assert Capability.DETERMINISTIC in caps


def test_capability_scoring():
    caps = CapabilitySet(capabilities=frozenset([
        Capability.REASONING, Capability.LONG_CONTEXT, Capability.STREAMING,
    ]))
    required = [Capability.REASONING, Capability.LONG_CONTEXT, Capability.STREAMING]

    score = score_provider(caps, required, latency_ms=500, cost_usd=0.001, success_rate=0.95, is_healthy=True)
    assert score.capability_coverage == 1.0
    assert score.total_score > 0.8
    assert len(score.matched_capabilities) == 3
    assert len(score.missing_capabilities) == 0


# ---------------------------------------------------------------------------
# Provider Capability Declaration Tests
# ---------------------------------------------------------------------------


def test_local_provider_capabilities():
    provider = FakeLocalProvider()
    caps = provider.get_capabilities()
    assert caps.supports(Capability.LOCAL_ONLY)
    assert caps.supports(Capability.OFFLINE)
    assert caps.supports(Capability.DETERMINISTIC)
    assert not caps.supports(Capability.REASONING)


def test_cloud_provider_capabilities():
    provider = FakeCloudProvider()
    caps = provider.get_capabilities()
    assert caps.supports(Capability.REASONING)
    assert caps.supports(Capability.HIGH_ACCURACY)
    assert caps.supports(Capability.CLOUD_ONLY)
    assert not caps.supports(Capability.OFFLINE)


# ---------------------------------------------------------------------------
# Registry Capability Queries
# ---------------------------------------------------------------------------


def test_registry_get_by_capability():
    registry = ProviderRegistry()
    registry.register("local", FakeLocalProvider())
    registry.register("cloud", FakeCloudProvider())

    local_only = registry.get_by_capability(Capability.LOCAL_ONLY)
    assert "local" in local_only
    assert "cloud" not in local_only

    reasoning = registry.get_by_capability(Capability.REASONING)
    assert "cloud" in reasoning
    assert "local" not in reasoning


def test_registry_get_supporting_all():
    registry = ProviderRegistry()
    registry.register("local", FakeLocalProvider())
    registry.register("cloud", FakeCloudProvider())

    both = registry.get_supporting_all([Capability.STREAMING, Capability.EXTRACTION])
    assert "local" in both
    assert "cloud" in both

    reasoning_only = registry.get_supporting_all([Capability.REASONING, Capability.HIGH_ACCURACY])
    assert "cloud" in reasoning_only
    assert "local" not in reasoning_only


def test_registry_list_capabilities():
    registry = ProviderRegistry()
    registry.register("local", FakeLocalProvider())
    registry.register("cloud", FakeCloudProvider())

    caps = registry.list_capabilities()
    assert "local" in caps
    assert "cloud" in caps
    assert "streaming" in caps["local"]
    assert "reasoning" in caps["cloud"]


# ---------------------------------------------------------------------------
# Router Capability-Based Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_routes_by_capabilities():
    """Router should select provider based on capability matching."""
    registry = ProviderRegistry()
    registry.register("local", FakeLocalProvider())
    registry.register("cloud", FakeCloudProvider())
    router = AIRouter(registry=registry)

    # Task requiring EXTRACTION should prefer local (has it, plus LOW_COST)
    task = AITask(task_type=AITaskType.CONCEPT_DISCOVERY, content="test")
    decision = await router.route(task)

    assert decision.chosen_provider in ("local", "cloud")
    assert decision.confidence > 0


@pytest.mark.asyncio
async def test_router_cloud_preferred_task():
    """Cloud-preferred tasks should route to cloud provider."""
    registry = ProviderRegistry()
    registry.register("local", FakeLocalProvider())
    registry.register("cloud", FakeCloudProvider())
    router = AIRouter(registry=registry)

    task = AITask(task_type=AITaskType.FINAL_RESPONSE, content="test")
    decision = await router.route(task)

    # Cloud has REASONING + LONG_CONTEXT + STREAMING, should score higher
    assert decision.chosen_provider == "cloud"


@pytest.mark.asyncio
async def test_router_fallback_on_failure():
    """Router should fallback when primary provider fails."""
    class FailingProvider(AIProvider):
        provider_name = "failing"
        provider_type = ProviderType.LOCAL

        def get_capabilities(self):
            return CapabilitySet(capabilities=frozenset([Capability.EXTRACTION, Capability.LOCAL_ONLY]))

        async def chat(self, messages, **kwargs):
            raise RuntimeError("Provider failed")

        async def chat_stream(self, messages, **kwargs):
            raise RuntimeError("Provider failed")

        async def health_check(self):
            return True

    registry = ProviderRegistry()
    registry.register("failing", FailingProvider())
    registry.register("backup", FakeCloudProvider())
    router = AIRouter(registry=registry)

    task = AITask(task_type=AITaskType.CONCEPT_DISCOVERY, content="test")
    messages = [{"role": "user", "content": "Hello"}]
    result = await router.chat(task, messages)

    # Should fallback to cloud provider
    assert result["choices"][0]["message"]["content"] == "Cloud response"


@pytest.mark.asyncio
async def test_router_force_provider():
    """Router should respect forced provider."""
    registry = ProviderRegistry()
    registry.register("local", FakeLocalProvider())
    registry.register("cloud", FakeCloudProvider())
    router = AIRouter(registry=registry)

    task = AITask(task_type=AITaskType.CONCEPT_DISCOVERY, content="test")
    decision = await router.route(task, force_provider="local")

    assert decision.chosen_provider == "local"


@pytest.mark.asyncio
async def test_router_chat():
    """Router should execute chat through selected provider."""
    registry = ProviderRegistry()
    registry.register("test_provider", FakeCloudProvider())
    router = AIRouter(registry=registry)

    task = AITask(task_type=AITaskType.CONVERSATION_GENERATION, content="test")
    messages = [{"role": "user", "content": "Hello"}]
    result = await router.chat(task, messages)

    assert "choices" in result
    assert result["choices"][0]["message"]["content"] == "Cloud response"


@pytest.mark.asyncio
async def test_router_chat_stream():
    """Router should stream through selected provider."""
    registry = ProviderRegistry()
    registry.register("test_provider", FakeCloudProvider())
    router = AIRouter(registry=registry)

    task = AITask(task_type=AITaskType.CONVERSATION_GENERATION, content="test")
    messages = [{"role": "user", "content": "Hello"}]

    chunks = []
    async for chunk in router.chat_stream(task, messages):
        chunks.append(chunk)

    assert len(chunks) == 2


@pytest.mark.asyncio
async def test_router_metrics():
    """Router should collect metrics."""
    registry = ProviderRegistry()
    registry.register("test_provider", FakeCloudProvider())
    router = AIRouter(registry=registry)

    task = AITask(task_type=AITaskType.CONVERSATION_GENERATION, content="test")
    messages = [{"role": "user", "content": "Hello"}]
    await router.chat(task, messages)

    metrics = router.get_metrics()
    assert metrics["total_requests"] >= 1


@pytest.mark.asyncio
async def test_router_explain_routing():
    """RoutingDecision should contain explanation fields."""
    registry = ProviderRegistry()
    registry.register("local", FakeLocalProvider())
    registry.register("cloud", FakeCloudProvider())
    router = AIRouter(registry=registry)

    task = AITask(task_type=AITaskType.FINAL_RESPONSE, content="test")
    decision = await router.route(task)

    assert decision.chosen_provider
    assert decision.routing_reason
    assert decision.policy_used
    assert decision.confidence >= 0


# ---------------------------------------------------------------------------
# Policy Engine Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_policy_engine_local_preferred():
    """Policy engine should prefer local for local-preferred tasks."""
    engine = PolicyEngine()
    task = AITask(task_type=AITaskType.CONCEPT_DISCOVERY)

    providers = {"local": FakeLocalProvider()}
    provider_type, reason = engine.evaluate(task, providers)

    assert provider_type == ProviderType.LOCAL
    assert "local" in reason.lower()


@pytest.mark.asyncio
async def test_policy_engine_cloud_preferred():
    """Policy engine should prefer cloud for cloud-preferred tasks."""
    engine = PolicyEngine()
    task = AITask(task_type=AITaskType.FINAL_RESPONSE)

    providers = {"cloud": FakeCloudProvider()}
    provider_type, reason = engine.evaluate(task, providers)

    assert provider_type == ProviderType.CLOUD
    assert "cloud" in reason.lower()


@pytest.mark.asyncio
async def test_policy_engine_hybrid_high_complexity():
    """Hybrid tasks with high complexity should prefer cloud."""
    engine = PolicyEngine()
    task = AITask(
        task_type=AITaskType.REASONING,
        complexity=TaskComplexity.HIGH,
    )

    providers = {"cloud": FakeCloudProvider()}
    provider_type, reason = engine.evaluate(task, providers)

    assert provider_type == ProviderType.CLOUD


@pytest.mark.asyncio
async def test_policy_engine_get_provider_preference():
    """Policy engine should return preference scores."""
    engine = PolicyEngine()

    local_pref = engine.get_provider_preference(AITaskType.CONCEPT_DISCOVERY, ProviderType.LOCAL)
    cloud_pref = engine.get_provider_preference(AITaskType.CONCEPT_DISCOVERY, ProviderType.CLOUD)

    assert local_pref > cloud_pref


# ---------------------------------------------------------------------------
# Registry Health Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registry_health_check():
    """Registry should track provider health."""
    registry = ProviderRegistry()
    registry.register("test_provider", FakeLocalProvider())

    healthy = await registry.check_health("test_provider")
    assert healthy is True

    health = registry.get_health("test_provider")
    assert health.is_healthy is True


@pytest.mark.asyncio
async def test_registry_list_providers():
    """Registry should list all providers with capabilities."""
    registry = ProviderRegistry()
    registry.register("local_provider", FakeLocalProvider())
    registry.register("cloud_provider", FakeCloudProvider())

    providers = registry.list_providers()
    assert len(providers) == 2
    assert "local_provider" in providers
    assert "capabilities" in providers["local_provider"]


# ---------------------------------------------------------------------------
# Backward Compatibility Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backward_compatible_routing():
    """Existing task types should still route correctly."""
    registry = ProviderRegistry()
    registry.register("local", FakeLocalProvider())
    registry.register("cloud", FakeCloudProvider())
    router = AIRouter(registry=registry)

    # Test all task types can be routed
    for task_type in AITaskType:
        task = AITask(task_type=task_type, content="test")
        decision = await router.route(task)
        assert decision.chosen_provider, f"Failed to route {task_type}"
