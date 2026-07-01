"""Tests for Interpretation Layer extensions v2: context-aware cache, consumer-driven, deep graph."""

from __future__ import annotations

import pytest

from ayeneh.knowledge_interpretation.engine import (
    DeepGraphReasoner,
    InterpretationCache,
    InterpretationEngine,
    InterpretationTypeSelector,
    OnDemandInterpretationService,
)
from ayeneh.knowledge_interpretation.types import (
    GraphContext,
    GraphReasoningResult,
    Interpretation,
    InterpretationCacheKey,
    InterpretationContext,
    InterpretationKind,
    SourceReference,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cache() -> InterpretationCache:
    return InterpretationCache()


@pytest.fixture
def engine() -> InterpretationEngine:
    return InterpretationEngine()


@pytest.fixture
def on_demand_service(engine: InterpretationEngine) -> OnDemandInterpretationService:
    return OnDemandInterpretationService(engine=engine)


@pytest.fixture
def graph_reasoner() -> DeepGraphReasoner:
    return DeepGraphReasoner()


# ---------------------------------------------------------------------------
# Context-Aware Cache Key tests
# ---------------------------------------------------------------------------


class TestInterpretationCacheKey:
    def test_key_creation(self) -> None:
        key = InterpretationCacheKey(
            chunk_id="chunk1",
            product_profile="ayeneh",
            interpretation_kind="conservative",
            generator_version="1.0.0",
        )
        assert key.chunk_id == "chunk1"
        assert key.product_profile == "ayeneh"

    def test_key_to_string(self) -> None:
        key = InterpretationCacheKey(
            chunk_id="chunk1",
            product_profile="ayeneh",
            interpretation_kind="conservative",
        )
        s = key.to_string()
        assert "chunk1" in s
        assert "ayeneh" in s
        assert "conservative" in s

    def test_key_equality(self) -> None:
        key1 = InterpretationCacheKey(chunk_id="c1", product_profile="p1")
        key2 = InterpretationCacheKey(chunk_id="c1", product_profile="p1")
        assert key1 == key2

    def test_key_inequality(self) -> None:
        key1 = InterpretationCacheKey(chunk_id="c1", product_profile="p1")
        key2 = InterpretationCacheKey(chunk_id="c1", product_profile="p2")
        assert key1 != key2

    def test_key_hashable(self) -> None:
        key = InterpretationCacheKey(chunk_id="c1")
        d = {key: "value"}
        assert d[key] == "value"


# ---------------------------------------------------------------------------
# Context-Aware Cache tests
# ---------------------------------------------------------------------------


class TestContextAwareCache:
    def test_put_by_key_and_get_by_key(self, cache: InterpretationCache) -> None:
        key = InterpretationCacheKey(chunk_id="c1", product_profile="p1")
        interp = Interpretation(id="test_id")
        cache.put_by_key(key, interp)
        result = cache.get_by_key(key)
        assert result is not None
        assert result.id == "test_id"

    def test_get_by_key_missing(self, cache: InterpretationCache) -> None:
        key = InterpretationCacheKey(chunk_id="c1")
        result = cache.get_by_key(key)
        assert result is None

    def test_invalidate_key(self, cache: InterpretationCache) -> None:
        key = InterpretationCacheKey(chunk_id="c1")
        cache.put_by_key(key, Interpretation())
        assert cache.invalidate_key(key) is True
        assert cache.get_by_key(key) is None

    def test_invalidate_chunk_removes_key_entries(self, cache: InterpretationCache) -> None:
        key1 = InterpretationCacheKey(chunk_id="c1", product_profile="p1")
        key2 = InterpretationCacheKey(chunk_id="c1", product_profile="p2")
        cache.put_by_key(key1, Interpretation())
        cache.put_by_key(key2, Interpretation())
        cache.invalidate("c1")
        assert cache.get_by_key(key1) is None
        assert cache.get_by_key(key2) is None

    def test_get_stats(self, cache: InterpretationCache) -> None:
        cache.put("c1", Interpretation())
        key = InterpretationCacheKey(chunk_id="c2")
        cache.put_by_key(key, Interpretation())
        stats = cache.get_stats()
        assert stats["simple_cache_size"] == 1
        assert stats["key_cache_size"] == 1
        assert stats["total_size"] == 2


# ---------------------------------------------------------------------------
# Consumer-Driven Selection tests
# ---------------------------------------------------------------------------


class TestConsumerDrivenSelection:
    @pytest.mark.asyncio
    async def test_explicit_kind_request(
        self, on_demand_service: OnDemandInterpretationService,
    ) -> None:
        context = InterpretationContext(
            chunk_id="chunk_explicit",
            chunk_content="Test content",
        )
        interp = await on_demand_service.get_or_generate(
            context,
            interpretation_kind="practical",
        )
        assert interp.interpretation_kind == "practical"

    @pytest.mark.asyncio
    async def test_different_kinds_different_cache(
        self, on_demand_service: OnDemandInterpretationService,
    ) -> None:
        context = InterpretationContext(
            chunk_id="chunk_kinds",
            chunk_content="Test content",
        )
        interp1 = await on_demand_service.get_or_generate(
            context, interpretation_kind="conservative",
        )
        interp2 = await on_demand_service.get_or_generate(
            context, interpretation_kind="practical",
        )
        # Both should exist and have different kinds
        assert interp1.interpretation_kind == "conservative"
        assert interp2.interpretation_kind == "practical"

    @pytest.mark.asyncio
    async def test_automatic_selection_fallback(
        self, on_demand_service: OnDemandInterpretationService,
    ) -> None:
        context = InterpretationContext(
            chunk_id="chunk_auto",
            chunk_content="Compare these two approaches",
        )
        interp = await on_demand_service.get_or_generate(context)
        # Should auto-select comparative based on content
        assert interp.interpretation_kind == "comparative"

    @pytest.mark.asyncio
    async def test_product_profile_in_cache_key(
        self, on_demand_service: OnDemandInterpretationService,
    ) -> None:
        context = InterpretationContext(
            chunk_id="chunk_profile",
            chunk_content="Test content",
        )
        interp1 = await on_demand_service.get_or_generate(
            context, product_profile="ayeneh",
        )
        interp2 = await on_demand_service.get_or_generate(
            context, product_profile="career",
        )
        # Different profiles should produce different cache entries
        assert interp1 is not None
        assert interp2 is not None


# ---------------------------------------------------------------------------
# Deep Graph Reasoning tests
# ---------------------------------------------------------------------------


class TestDeepGraphReasoning:
    def test_enhances_with_supporting_perspectives(
        self, graph_reasoner: DeepGraphReasoner,
    ) -> None:
        interp = Interpretation(
            source=SourceReference(document_id="doc1", original_text="text"),
        )
        graph_data = {
            "supporting_books": ["Book A", "Book B"],
            "shared_concepts": ["mindfulness"],
        }
        enhanced = graph_reasoner.enhance(interp, graph_data)
        assert enhanced.graph_reasoning is not None
        assert len(enhanced.graph_reasoning.supporting_perspectives) > 0

    def test_enhances_with_alternative_perspectives(
        self, graph_reasoner: DeepGraphReasoner,
    ) -> None:
        interp = Interpretation(
            source=SourceReference(document_id="doc1", original_text="text"),
        )
        graph_data = {
            "alternative_traditions": ["Zen", "Sufism"],
        }
        enhanced = graph_reasoner.enhance(interp, graph_data)
        assert len(enhanced.graph_reasoning.alternative_perspectives) > 0

    def test_enhances_with_conflicting_perspectives(
        self, graph_reasoner: DeepGraphReasoner,
    ) -> None:
        interp = Interpretation(
            source=SourceReference(document_id="doc1", original_text="text"),
        )
        graph_data = {
            "known_disagreements": ["Different views on consciousness"],
        }
        enhanced = graph_reasoner.enhance(interp, graph_data)
        assert len(enhanced.graph_reasoning.conflicting_perspectives) > 0

    def test_enhances_with_complementary_perspectives(
        self, graph_reasoner: DeepGraphReasoner,
    ) -> None:
        interp = Interpretation(
            source=SourceReference(document_id="doc1", original_text="text"),
        )
        graph_data = {
            "complementary_viewpoints": ["Neuroscience perspective"],
        }
        enhanced = graph_reasoner.enhance(interp, graph_data)
        assert len(enhanced.graph_reasoning.complementary_perspectives) > 0

    def test_enhances_with_scope_limitations(
        self, graph_reasoner: DeepGraphReasoner,
    ) -> None:
        interp = Interpretation(
            source=SourceReference(document_id="doc1", original_text="text"),
        )
        graph_data = {
            "scope_comparisons": ["Limited to Western tradition"],
        }
        enhanced = graph_reasoner.enhance(interp, graph_data)
        assert len(enhanced.graph_reasoning.scope_limitations) > 0

    def test_enhances_with_authority_differences(
        self, graph_reasoner: DeepGraphReasoner,
    ) -> None:
        interp = Interpretation(
            source=SourceReference(document_id="doc1", original_text="text"),
        )
        graph_data = {
            "authority_comparisons": ["Primary vs secondary source"],
        }
        enhanced = graph_reasoner.enhance(interp, graph_data)
        assert len(enhanced.graph_reasoning.authority_differences) > 0

    def test_boosts_confidence_with_support(
        self, graph_reasoner: DeepGraphReasoner,
    ) -> None:
        interp = Interpretation(
            source=SourceReference(document_id="doc1", original_text="text"),
            confidence=0.5,
        )
        graph_data = {
            "supporting_books": ["Book A", "Book B"],
            "shared_concepts": ["concept1"],
        }
        enhanced = graph_reasoner.enhance(interp, graph_data)
        assert enhanced.confidence > 0.5

    def test_preserves_distinctions(
        self, graph_reasoner: DeepGraphReasoner,
    ) -> None:
        interp = Interpretation(
            source=SourceReference(document_id="doc1", original_text="text"),
        )
        graph_data = {
            "alternative_traditions": ["Zen"],
            "known_disagreements": ["Different metaphysics"],
        }
        enhanced = graph_reasoner.enhance(interp, graph_data)
        # Should have both alternative and conflicting perspectives
        assert len(enhanced.graph_reasoning.alternative_perspectives) > 0
        assert len(enhanced.graph_reasoning.conflicting_perspectives) > 0


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    @pytest.mark.asyncio
    async def test_on_demand_with_deep_reasoning(
        self, engine: InterpretationEngine,
    ) -> None:
        service = OnDemandInterpretationService(engine=engine)

        # Mock graph context provider
        class MockProvider:
            async def get_context(self, chunk_id: str, doc_id: str) -> dict:
                return {
                    "related_concepts": ["mindfulness"],
                    "supporting_books": ["Book A"],
                    "alternative_traditions": ["Zen"],
                    "shared_concepts": ["presence"],
                    "graph_confidence": 0.8,
                }

        service.set_graph_context_provider(MockProvider())

        context = InterpretationContext(
            chunk_id="chunk_reasoning",
            chunk_content="Meditation practice for awareness",
        )
        interp = await service.get_or_generate(context)
        assert interp.graph_reasoning is not None
        assert len(interp.graph_reasoning.supporting_perspectives) > 0

    @pytest.mark.asyncio
    async def test_explicit_kind_with_graph(
        self, engine: InterpretationEngine,
    ) -> None:
        service = OnDemandInterpretationService(engine=engine)

        class MockProvider:
            async def get_context(self, chunk_id: str, doc_id: str) -> dict:
                return {"alternative_traditions": ["Sufism"]}

        service.set_graph_context_provider(MockProvider())

        context = InterpretationContext(
            chunk_id="chunk_kind_graph",
            chunk_content="Contemplative practice",
        )
        interp = await service.get_or_generate(
            context, interpretation_kind="cross_tradition",
        )
        assert interp.interpretation_kind == "cross_tradition"
        assert interp.graph_reasoning is not None


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_simple_cache_still_works(self, cache: InterpretationCache) -> None:
        interp = Interpretation(id="test")
        cache.put("chunk1", interp)
        result = cache.get("chunk1")
        assert result is not None
        assert result.id == "test"

    def test_interpretation_kind_defaults_to_conservative(self) -> None:
        interp = Interpretation()
        assert interp.interpretation_kind == InterpretationKind.CONSERVATIVE

    def test_graph_reasoning_optional(self) -> None:
        interp = Interpretation()
        assert interp.graph_reasoning is None
