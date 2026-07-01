"""Comprehensive tests for the Product Profile Layer."""

from __future__ import annotations

import asyncio

import pytest

from ayeneh.product.observability import ProductMetrics
from ayeneh.product.profiles import AYENEH_PROFILE, CAREER_PROFILE, BUSINESS_PROFILE
from ayeneh.product.registry import ProductRegistry, load_default_profiles
from ayeneh.product.types import (
    BehaviorPolicy,
    GoalPolicy,
    KnowledgePolicy,
    MemoryPolicy,
    ProductProfile,
    ResourcePolicy,
)


# ════════════════════════════════════════════════════════════════════════
# Types tests
# ════════════════════════════════════════════════════════════════════════

class TestProductTypes:
    def test_product_profile_creation(self) -> None:
        p = ProductProfile(id="test", name="Test Product", version="1.0")
        assert p.id == "test"
        assert p.name == "Test Product"

    def test_behavior_policy(self) -> None:
        b = BehaviorPolicy(philosophy="Test philosophy", identity="Test identity")
        assert b.philosophy == "Test philosophy"

    def test_resource_policy(self) -> None:
        r = ResourcePolicy(enabled_agents=["conversation", "memory"])
        assert len(r.enabled_agents) == 2

    def test_knowledge_policy(self) -> None:
        k = KnowledgePolicy(retrieval_strategy="hybrid")
        assert k.retrieval_strategy == "hybrid"

    def test_product_get_system_prompt(self) -> None:
        p = ProductProfile(
            id="test",
            behavior=BehaviorPolicy(
                identity="You are a test bot.",
                philosophy="Be helpful.",
                safety_policy="Be safe.",
            ),
        )
        prompt = p.get_system_prompt()
        assert "test bot" in prompt
        assert "helpful" in prompt

    def test_product_has_agent(self) -> None:
        p = ProductProfile(resources=ResourcePolicy(enabled_agents=["conversation", "memory"]))
        assert p.has_agent("conversation") is True
        assert p.has_agent("blind_spot") is False

    def test_product_has_agent_empty_list(self) -> None:
        p = ProductProfile(resources=ResourcePolicy(enabled_agents=[]))
        assert p.has_agent("anything") is True

    def test_product_to_dict(self) -> None:
        p = ProductProfile(id="test", name="Test")
        d = p.to_dict()
        assert d["id"] == "test"
        assert d["name"] == "Test"


# ════════════════════════════════════════════════════════════════════════
# Registry tests
# ════════════════════════════════════════════════════════════════════════

class TestProductRegistry:
    def test_register_and_get(self) -> None:
        registry = ProductRegistry()
        p = ProductProfile(id="test", name="Test")
        registry.register(p)
        assert registry.get("test") is p
        assert registry.get("missing") is None

    def test_unregister(self) -> None:
        registry = ProductRegistry()
        registry.register(ProductProfile(id="test"))
        assert registry.unregister("test") is True
        assert registry.unregister("test") is False

    def test_set_default(self) -> None:
        registry = ProductRegistry()
        registry.register(ProductProfile(id="a"))
        registry.register(ProductProfile(id="b"))
        registry.set_default("a")
        assert registry.get_or_default().id == "a"

    def test_get_or_default_fallback(self) -> None:
        registry = ProductRegistry()
        registry.register(ProductProfile(id="only"))
        assert registry.get_or_default("nonexistent").id == "only"

    def test_list_profiles(self) -> None:
        registry = ProductRegistry()
        registry.register(ProductProfile(id="a", name="A"))
        registry.register(ProductProfile(id="b", name="B"))
        profiles = registry.list_profiles()
        assert len(profiles) == 2

    def test_list_ids(self) -> None:
        registry = ProductRegistry()
        registry.register(ProductProfile(id="x"))
        assert "x" in registry.list_ids()

    def test_singleton(self) -> None:
        ProductRegistry.reset()
        r1 = ProductRegistry.get_instance()
        r2 = ProductRegistry.get_instance()
        assert r1 is r2
        ProductRegistry.reset()

    def test_reset(self) -> None:
        ProductRegistry.reset()
        r1 = ProductRegistry.get_instance()
        r1.register(ProductProfile(id="test"))
        ProductRegistry.reset()
        r2 = ProductRegistry.get_instance()
        assert r2.get("test") is None

    def test_len(self) -> None:
        registry = ProductRegistry()
        registry.register(ProductProfile(id="a"))
        registry.register(ProductProfile(id="b"))
        assert len(registry) == 2


# ════════════════════════════════════════════════════════════════════════
# Built-in profiles tests
# ════════════════════════════════════════════════════════════════════════

class TestBuiltInProfiles:
    def test_ayeneh_profile(self) -> None:
        assert AYENEH_PROFILE.id == "ayeneh"
        assert "mirror" in AYENEH_PROFILE.behavior.philosophy.lower()
        assert "conversation" in AYENEH_PROFILE.resources.enabled_agents
        assert AYENEH_PROFILE.knowledge.retrieval_strategy == "hybrid"

    def test_career_profile(self) -> None:
        assert CAREER_PROFILE.id == "career"
        assert "action" in CAREER_PROFILE.behavior.communication_style.lower()
        assert CAREER_PROFILE.goals.goal_reasoning_mode == "planning"

    def test_business_profile(self) -> None:
        assert BUSINESS_PROFILE.id == "business"
        assert "roi" in BUSINESS_PROFILE.behavior.philosophy.lower()
        assert BUSINESS_PROFILE.knowledge.citation_policy == "always"

    def test_load_default_profiles(self) -> None:
        ProductRegistry.reset()
        registry = load_default_profiles()
        assert len(registry) == 3
        assert registry.get_or_default().id == "ayeneh"

    def test_ayeneh_no_unsupported_philosophy(self) -> None:
        bad_words = ["therapist", "spiritual guide", "chatbot", "generic assistant"]
        text = AYENEH_PROFILE.behavior.identity.lower()
        for word in bad_words:
            if word in text:
                assert False, f"Unsupported philosophy term: {word}"


# ════════════════════════════════════════════════════════════════════════
# Prompt composition with profiles tests
# ════════════════════════════════════════════════════════════════════════

class TestProfilePromptComposition:
    @pytest.mark.asyncio
    async def test_compose_with_ayeneh_profile(self) -> None:
        from ayeneh.prompt.composition import PromptComposer
        from ayeneh.prompt.profiles import get_profile, get_policy
        from ayeneh.prompt.types import AdaptiveSelection

        composer = PromptComposer()
        profile = get_profile("conversation")
        policy = get_policy("standard")
        selection = AdaptiveSelection(token_budget=12000)
        comp = await composer.compose(
            profile, policy, selection, "test",
            token_budget=12000, product_profile=AYENEH_PROFILE,
        )
        assert "Ayeneh" in comp.system_prompt
        assert "mirror" in comp.system_prompt.lower()

    @pytest.mark.asyncio
    async def test_compose_with_career_profile(self) -> None:
        from ayeneh.prompt.composition import PromptComposer
        from ayeneh.prompt.profiles import get_profile, get_policy
        from ayeneh.prompt.types import AdaptiveSelection

        composer = PromptComposer()
        profile = get_profile("conversation")
        policy = get_policy("standard")
        selection = AdaptiveSelection(token_budget=12000)
        comp = await composer.compose(
            profile, policy, selection, "test",
            token_budget=12000, product_profile=CAREER_PROFILE,
        )
        assert "Career Mentor" in comp.system_prompt

    @pytest.mark.asyncio
    async def test_compose_with_business_profile(self) -> None:
        from ayeneh.prompt.composition import PromptComposer
        from ayeneh.prompt.profiles import get_profile, get_policy
        from ayeneh.prompt.types import AdaptiveSelection

        composer = PromptComposer()
        profile = get_profile("conversation")
        policy = get_policy("standard")
        selection = AdaptiveSelection(token_budget=12000)
        comp = await composer.compose(
            profile, policy, selection, "test",
            token_budget=12000, product_profile=BUSINESS_PROFILE,
        )
        assert "Business Advisor" in comp.system_prompt

    @pytest.mark.asyncio
    async def test_compose_without_profile_fallback(self) -> None:
        from ayeneh.prompt.composition import PromptComposer
        from ayeneh.prompt.profiles import get_profile, get_policy
        from ayeneh.prompt.types import AdaptiveSelection

        composer = PromptComposer()
        profile = get_profile("conversation")
        policy = get_policy("standard")
        selection = AdaptiveSelection(token_budget=12000)
        comp = await composer.compose(
            profile, policy, selection, "test",
            token_budget=12000, product_profile=None,
        )
        assert "Ayeneh" in comp.system_prompt


# ════════════════════════════════════════════════════════════════════════
# Observability tests
# ════════════════════════════════════════════════════════════════════════

class TestProductObservability:
    def test_record_execution(self) -> None:
        m = ProductMetrics()
        m.record_execution("ayeneh", 500, 100.0)
        m.record_execution("ayeneh", 300, 80.0)
        assert m.executions_per_product["ayeneh"] == 2
        assert m.token_usage_per_product["ayeneh"] == 800

    def test_record_switch(self) -> None:
        m = ProductMetrics()
        m.record_switch()
        m.record_switch()
        assert m.profile_switches == 2

    def test_summary(self) -> None:
        m = ProductMetrics()
        m.record_execution("ayeneh", 100, 50.0)
        s = m.get_summary()
        assert s["executions_per_product"]["ayeneh"] == 1

    def test_prometheus_export(self) -> None:
        m = ProductMetrics()
        m.record_execution("ayeneh", 100, 50.0)
        text = m.export_prometheus_text()
        assert 'ayeneh_product_executions_total{product="ayeneh"} 1' in text


# ════════════════════════════════════════════════════════════════════════
# Profile switching tests
# ════════════════════════════════════════════════════════════════════════

class TestProfileSwitching:
    def test_switch_default_profile(self) -> None:
        ProductRegistry.reset()
        registry = load_default_profiles()
        registry.set_default("career")
        assert registry.get_or_default().id == "career"

    def test_profile_has_different_agents(self) -> None:
        ayeneh_agents = set(AYENEH_PROFILE.resources.enabled_agents)
        career_agents = set(CAREER_PROFILE.resources.enabled_agents)
        assert ayeneh_agents != career_agents

    def test_profile_has_different_retrieval(self) -> None:
        assert AYENEH_PROFILE.knowledge.retrieval_strategy == "hybrid"
        assert CAREER_PROFILE.knowledge.retrieval_strategy == "knowledge_focused"

    def test_profile_has_different_goals(self) -> None:
        assert AYENEH_PROFILE.goals.goal_strategy == "standard"
        assert BUSINESS_PROFILE.goals.goal_strategy == "okr"


# ════════════════════════════════════════════════════════════════════════
# Custom profile tests
# ════════════════════════════════════════════════════════════════════════

class TestCustomProfiles:
    def test_register_custom_profile(self) -> None:
        registry = ProductRegistry()
        custom = ProductProfile(
            id="learning",
            name="Learning Companion",
            behavior=BehaviorPolicy(
                identity="You help people learn.",
                philosophy="Active learning through practice.",
            ),
            resources=ResourcePolicy(enabled_agents=["conversation", "memory"]),
        )
        registry.register(custom)
        assert registry.get("learning") is not None
        assert registry.get("learning").behavior.identity == "You help people learn."

    def test_multiple_custom_profiles(self) -> None:
        registry = ProductRegistry()
        for i in range(5):
            registry.register(ProductProfile(id=f"custom-{i}", name=f"Custom {i}"))
        assert len(registry) == 5
        all_ids = registry.list_ids()
        assert all(f"custom-{i}" in all_ids for i in range(5))


# ════════════════════════════════════════════════════════════════════════
# Concurrency tests
# ════════════════════════════════════════════════════════════════════════

class TestProductConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_profile_access(self) -> None:
        ProductRegistry.reset()
        registry = load_default_profiles()

        async def access(pid: str) -> str:
            p = registry.get(pid)
            return p.id if p else ""

        results = await asyncio.gather(*[access("ayeneh") for _ in range(10)])
        assert all(r == "ayeneh" for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_metrics_recording(self) -> None:
        metrics = ProductMetrics()

        def record():
            metrics.record_execution("test", 100, 50.0)

        tasks = [asyncio.to_thread(record) for _ in range(100)]
        await asyncio.gather(*tasks)
        assert metrics.executions_per_product["test"] == 100
