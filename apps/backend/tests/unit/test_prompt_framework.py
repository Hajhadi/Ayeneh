"""Comprehensive tests for the Cognitive Prompting Framework."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from ayeneh.prompt.composition import PromptComposer
from ayeneh.prompt.grounding import GroundingValidator
from ayeneh.prompt.observability import PromptMetrics
from ayeneh.prompt.profiles import (
    CONVERSATION_PROFILE,
    REFLECTION_PROFILE,
    BLIND_SPOT_PROFILE,
    PATTERN_PROFILE,
    MEMORY_PROFILE,
    GOAL_REASONING_PROFILE,
    REASONING_POLICIES,
    get_policy,
    get_profile,
)
from ayeneh.prompt.selection import AdaptiveSelector
from ayeneh.prompt.types import (
    AdaptiveSelection,
    GroundingResult,
    PromptComposition,
    PromptModule,
    PromptProfile,
    ReasoningMetadata,
    ReasoningPolicy,
)


# ════════════════════════════════════════════════════════════════════════
# Types tests
# ════════════════════════════════════════════════════════════════════════

class TestTypes:
    def test_prompt_module(self):
        m = PromptModule(name="test", content="hello", version="1.0", priority=5)
        assert m.name == "test"
        assert m.version == "1.0"

    def test_prompt_profile(self):
        p = PromptProfile(agent_type="test", version="2.0", system_instructions="sys")
        assert p.agent_type == "test"
        assert p.version == "2.0"

    def test_reasoning_policy(self):
        p = ReasoningPolicy(name="fast", reasoning_depth="shallow", citation_required=False)
        assert p.name == "fast"
        assert p.citation_required is False

    def test_prompt_composition(self):
        c = PromptComposition(system_prompt="sys", user_prompt="usr", token_budget=1000)
        assert c.token_budget == 1000
        assert c.compression_applied is False

    def test_reasoning_metadata_to_dict(self):
        m = ReasoningMetadata(reasoning_policy="standard")
        d = m.to_dict()
        assert d["reasoning_policy"] == "standard"

    def test_adaptive_selection(self):
        s = AdaptiveSelection(token_budget=5000)
        assert s.token_budget == 5000
        assert s.total_tokens == 0

    def test_grounding_result(self):
        r = GroundingResult(is_grounded=True, grounding_score=0.9)
        assert r.is_grounded is True


# ════════════════════════════════════════════════════════════════════════
# Profiles tests
# ════════════════════════════════════════════════════════════════════════

class TestProfiles:
    def test_all_profiles_exist(self):
        assert "conversation" in [CONVERSATION_PROFILE.agent_type]
        assert CONVERSATION_PROFILE.version == "1.0"
        assert REFLECTION_PROFILE.version == "1.0"
        assert BLIND_SPOT_PROFILE.version == "1.0"
        assert PATTERN_PROFILE.version == "1.0"
        assert MEMORY_PROFILE.version == "1.0"
        assert GOAL_REASONING_PROFILE.version == "1.0"

    def test_profiles_have_modules(self):
        assert len(CONVERSATION_PROFILE.modules) >= 3
        assert len(REFLECTION_PROFILE.modules) >= 1

    def test_get_profile(self):
        p = get_profile("conversation")
        assert p.agent_type == "conversation"
        p2 = get_profile("nonexistent")
        assert p2.agent_type == "conversation"

    def test_get_policy(self):
        p = get_policy("fast")
        assert p.name == "fast"
        p2 = get_policy("nonexistent")
        assert p2.name == "standard"

    def test_reasoning_policies(self):
        assert "fast" in REASONING_POLICIES
        assert "deep" in REASONING_POLICIES
        assert "goal_planning" in REASONING_POLICIES
        assert "pattern_discovery" in REASONING_POLICIES
        assert "blind_spot_analysis" in REASONING_POLICIES

    def test_profile_modules_have_content(self):
        for profile in [CONVERSATION_PROFILE, REFLECTION_PROFILE, BLIND_SPOT_PROFILE, PATTERN_PROFILE]:
            for module in profile.modules:
                assert module.content
                assert module.name
                assert module.version

    def test_profile_safety_rules(self):
        assert len(CONVERSATION_PROFILE.safety_rules) >= 2
        assert len(BLIND_SPOT_PROFILE.safety_rules) >= 2

    def test_profile_citation_rules(self):
        assert len(CONVERSATION_PROFILE.citation_rules) >= 2


# ════════════════════════════════════════════════════════════════════════
# Composition tests
# ════════════════════════════════════════════════════════════════════════

class TestComposition:
    @pytest.mark.asyncio
    async def test_compose_conversation(self):
        composer = PromptComposer()
        profile = get_profile("conversation")
        policy = get_policy("standard")
        selection = AdaptiveSelection(
            goals_to_inject=[{"title": "Learn Python", "progress": 0.5, "priority": "high"}],
            memories_to_inject=[{"type": "semantic", "content": "User likes coding", "confidence": 0.8}],
            knowledge_to_inject=[{"content": "Python is popular", "book_title": "Guide"}],
            token_budget=12000,
        )
        comp = await composer.compose(profile, policy, selection, "How is my learning going?", token_budget=12000)
        assert comp.system_prompt
        assert comp.user_prompt
        assert "Learn Python" in comp.user_prompt
        assert "User likes coding" in comp.user_prompt
        assert comp.token_estimate > 0

    @pytest.mark.asyncio
    async def test_compose_with_goal_priority(self):
        composer = PromptComposer()
        profile = get_profile("conversation")
        policy = get_policy("goal_planning")
        selection = AdaptiveSelection(
            goals_to_inject=[{"title": "Finish report", "progress": 0.3, "priority": "critical", "deadline": "tomorrow"}],
            token_budget=12000,
        )
        comp = await composer.compose(profile, policy, selection, "What should I do?", token_budget=12000)
        assert "Finish report" in comp.user_prompt

    @pytest.mark.asyncio
    async def test_compose_applies_compression(self):
        composer = PromptComposer()
        profile = get_profile("conversation")
        policy = get_policy("standard")
        selection = AdaptiveSelection(
            goals_to_inject=[{"title": f"Goal {i} with extra description", "progress": 0.5, "priority": "medium"} for i in range(20)],
            memories_to_inject=[{"type": "semantic", "content": " ".join(["word"] * 100), "confidence": 0.5} for i in range(20)],
            knowledge_to_inject=[{"content": " ".join(["knowledge"] * 100), "book_title": f"Book {i}"} for i in range(20)],
            token_budget=12000,
        )
        comp = await composer.compose(profile, policy, selection, "test", token_budget=200)
        assert comp.compression_applied is True

    @pytest.mark.asyncio
    async def test_compose_empty_selection(self):
        composer = PromptComposer()
        profile = get_profile("conversation")
        policy = get_policy("standard")
        selection = AdaptiveSelection(token_budget=12000)
        comp = await composer.compose(profile, policy, selection, "hello", token_budget=12000)
        assert comp.system_prompt
        assert comp.user_prompt

    @pytest.mark.asyncio
    async def test_compose_reflection_profile(self):
        composer = PromptComposer()
        profile = get_profile("reflection")
        policy = get_policy("deep")
        selection = AdaptiveSelection(
            goals_to_inject=[{"title": "Goal A", "progress": 0.5}],
            memories_to_inject=[{"type": "episodic", "content": "Event", "confidence": 0.7}],
            token_budget=12000,
        )
        comp = await composer.compose(profile, policy, selection, "reflect", token_budget=12000)
        assert "reflection" in comp.system_prompt.lower() or "reflect" in comp.user_prompt.lower()

    @pytest.mark.asyncio
    async def test_compose_includes_modules_used(self):
        composer = PromptComposer()
        profile = get_profile("conversation")
        policy = get_policy("standard")
        selection = AdaptiveSelection(token_budget=12000)
        comp = await composer.compose(profile, policy, selection, "test", token_budget=12000)
        assert len(comp.modules_used) >= 3

    @pytest.mark.asyncio
    async def test_compose_grounding_stats(self):
        composer = PromptComposer()
        profile = get_profile("conversation")
        policy = get_policy("standard")
        selection = AdaptiveSelection(
            memories_to_inject=[{"content": "A"}],
            knowledge_to_inject=[{"content": "B"}],
            goals_to_inject=[{"title": "C"}],
            token_budget=12000,
        )
        comp = await composer.compose(profile, policy, selection, "test", token_budget=12000)
        assert comp.grounding_stats["sources_injected"] == 3


# ════════════════════════════════════════════════════════════════════════
# Adaptive Selection tests
# ════════════════════════════════════════════════════════════════════════

class TestAdaptiveSelection:
    def test_select_goals_by_priority(self):
        selector = AdaptiveSelector()
        policy = ReasoningPolicy(goal_priority="high")
        retrieval = type('R', (), {
            'active_goals': [
                {"id": "1", "title": "Critical", "progress": 0.5, "priority": "critical"},
                {"id": "2", "title": "Low", "progress": 0.5, "priority": "low"},
            ],
            'blocked_goals': [],
            'urgent_goals': [{"id": "3", "title": "Urgent", "progress": 0.1, "deadline": "tomorrow"}],
            'memories': [],
            'knowledge_chunks': [],
            'patterns': [],
            'reflections': [],
            'recent_goal_progress': [],
        })()

        sel = selector.select(retrieval, policy, "test", token_budget=5000)
        assert any(g.get("title") == "Urgent" for g in sel.goals_to_inject)

    def test_select_respects_budget(self):
        selector = AdaptiveSelector()
        policy = ReasoningPolicy()
        retrieval = type('R', (), {
            'active_goals': [],
            'blocked_goals': [],
            'urgent_goals': [],
            'memories': [{"id": str(i), "type": "semantic", "content": f"Memory {i}", "confidence": 0.5, "score": 0.5} for i in range(50)],
            'knowledge_chunks': [],
            'patterns': [],
            'reflections': [],
            'recent_goal_progress': [],
        })()

        sel = selector.select(retrieval, policy, "test", token_budget=500)
        assert sel.total_tokens <= 500

    def test_select_low_score_memories_rejected(self):
        selector = AdaptiveSelector()
        policy = ReasoningPolicy()
        retrieval = type('R', (), {
            'active_goals': [],
            'blocked_goals': [],
            'urgent_goals': [],
            'memories': [
                {"id": "1", "type": "semantic", "content": "High", "confidence": 0.9, "score": 0.8},
                {"id": "2", "type": "semantic", "content": "Low", "confidence": 0.1, "score": 0.05},
            ],
            'knowledge_chunks': [],
            'patterns': [],
            'reflections': [],
            'recent_goal_progress': [],
        })()

        sel = selector.select(retrieval, policy, "test", token_budget=5000)
        assert len(sel.memories_to_inject) == 1
        assert sel.memories_to_inject[0]["content"] == "High"

    def test_select_includes_blocked_goals(self):
        selector = AdaptiveSelector()
        policy = ReasoningPolicy()
        retrieval = type('R', (), {
            'active_goals': [],
            'blocked_goals': [{"title": "Blocked", "dependencies": 2}],
            'urgent_goals': [],
            'memories': [],
            'knowledge_chunks': [],
            'patterns': [],
            'reflections': [],
            'recent_goal_progress': [],
        })()

        sel = selector.select(retrieval, policy, "test", token_budget=5000)
        assert len(sel.goals_to_inject) == 1


# ════════════════════════════════════════════════════════════════════════
# Grounding tests
# ════════════════════════════════════════════════════════════════════════

class TestGrounding:
    def test_validate_supported(self):
        gv = GroundingValidator()
        sources = [{"content": "Python is a programming language"}]
        result = gv.validate("Python is a popular programming language.", sources)
        assert result.is_grounded is True
        assert result.grounding_score > 0

    def test_validate_unsupported(self):
        gv = GroundingValidator()
        sources = [{"content": "cats are fluffy"}]
        result = gv.validate("Quantum computing requires qubits.", sources)
        assert result.grounding_score < 1.0

    def test_check_uncertainty_high(self):
        gv = GroundingValidator()
        score = gv.check_uncertainty("I think this might be the case based on available information.")
        assert score >= 0.7

    def test_check_uncertainty_low(self):
        gv = GroundingValidator()
        score = gv.check_uncertainty("The data clearly proves this is always true.")
        assert score < 0.5

    def test_grounding_result_structure(self):
        result = GroundingResult(is_grounded=True, grounding_score=0.95, citations_used=3)
        assert result.citations_used == 3
        assert result.grounding_score == 0.95


# ════════════════════════════════════════════════════════════════════════
# Observability tests
# ════════════════════════════════════════════════════════════════════════

class TestObservability:
    def test_record_and_summary(self):
        m = PromptMetrics()
        m.record_prompt("conversation", "standard", 500, ["identity", "safety"], False, 0.9)
        m.record_prompt("reflection", "deep", 800, ["identity"], True, 0.7)
        summary = m.get_summary()
        assert summary["total_prompts"] == 2
        assert summary["total_tokens"] == 1300

    def test_compression_rate(self):
        m = PromptMetrics()
        m.record_prompt("a", "b", 100, ["x"], True)
        m.record_prompt("a", "b", 100, ["x"], False)
        assert m.total_compressions == 1

    def test_prometheus_export(self):
        m = PromptMetrics()
        m.record_prompt("a", "b", 100, ["x"])
        text = m.export_prometheus_text()
        assert "ayeneh_prompts_total 1" in text
        assert "ayeneh_prompt_tokens_total 100" in text


# ════════════════════════════════════════════════════════════════════════
# Concurrent tests
# ════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_composition(self):
        composer = PromptComposer()
        profile = get_profile("conversation")
        policy = get_policy("standard")
        selection = AdaptiveSelection(
            goals_to_inject=[{"title": "G1", "progress": 0.5, "priority": "high"}],
            token_budget=12000,
        )

        async def compose():
            return await composer.compose(profile, policy, selection, "test", token_budget=12000)

        results = await asyncio.gather(*[compose() for _ in range(5)])
        assert all(r.token_estimate > 0 for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_metrics_recording(self):
        metrics = PromptMetrics()

        def record():
            metrics.record_prompt("test", "test", 100, ["x"])

        tasks = [asyncio.to_thread(record) for _ in range(100)]
        await asyncio.gather(*tasks)
        assert metrics.total_prompts_generated == 100
