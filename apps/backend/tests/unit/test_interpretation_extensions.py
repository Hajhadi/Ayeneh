"""Tests for Interpretation Layer extensions: on-demand, graph-aware, and types."""

from __future__ import annotations

import uuid

import pytest

from ayeneh.knowledge_interpretation.engine import (
    GraphAwareInterpretationGenerator,
    InterpretationCache,
    InterpretationEngine,
    InterpretationGenerator,
    InterpretationTypeSelector,
    OnDemandInterpretationService,
)
from ayeneh.knowledge_interpretation.types import (
    GraphContext,
    Interpretation,
    InterpretationContext,
    InterpretationKind,
    InterpretationType,
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
def graph_generator() -> GraphAwareInterpretationGenerator:
    return GraphAwareInterpretationGenerator()


@pytest.fixture
def type_selector() -> InterpretationTypeSelector:
    return InterpretationTypeSelector()


# ---------------------------------------------------------------------------
# InterpretationKind tests
# ---------------------------------------------------------------------------


class TestInterpretationKind:
    def test_all_kinds_exist(self) -> None:
        assert InterpretationKind.CONSERVATIVE == "conservative"
        assert InterpretationKind.COMPARATIVE == "comparative"
        assert InterpretationKind.PRACTICAL == "practical"
        assert InterpretationKind.CROSS_TRADITION == "cross_tradition"
        assert InterpretationKind.EXPLORATORY == "exploratory"

    def test_interpretation_has_kind_field(self) -> None:
        interp = Interpretation()
        assert hasattr(interp, "interpretation_kind")
        assert interp.interpretation_kind == InterpretationKind.CONSERVATIVE


# ---------------------------------------------------------------------------
# InterpretationCache tests
# ---------------------------------------------------------------------------


class TestInterpretationCache:
    def test_put_and_get(self, cache: InterpretationCache) -> None:
        interp = Interpretation(id="test_id")
        cache.put("chunk1", interp)
        result = cache.get("chunk1")
        assert result is not None
        assert result.id == "test_id"

    def test_get_missing(self, cache: InterpretationCache) -> None:
        result = cache.get("nonexistent")
        assert result is None

    def test_invalidate(self, cache: InterpretationCache) -> None:
        interp = Interpretation(id="test_id")
        cache.put("chunk1", interp)
        assert cache.invalidate("chunk1") is True
        assert cache.get("chunk1") is None

    def test_invalidate_missing(self, cache: InterpretationCache) -> None:
        assert cache.invalidate("nonexistent") is False

    def test_clear(self, cache: InterpretationCache) -> None:
        cache.put("chunk1", Interpretation())
        cache.put("chunk2", Interpretation())
        cache.clear()
        assert len(cache) == 0

    def test_contains(self, cache: InterpretationCache) -> None:
        cache.put("chunk1", Interpretation())
        assert "chunk1" in cache
        assert "chunk2" not in cache

    def test_len(self, cache: InterpretationCache) -> None:
        assert len(cache) == 0
        cache.put("chunk1", Interpretation())
        assert len(cache) == 1


# ---------------------------------------------------------------------------
# On-Demand Interpretation tests
# ---------------------------------------------------------------------------


class TestOnDemandInterpretation:
    @pytest.mark.asyncio
    async def test_generates_when_not_cached(
        self, on_demand_service: OnDemandInterpretationService,
    ) -> None:
        context = InterpretationContext(
            chunk_id="chunk_new",
            chunk_content="Test content about meditation",
        )
        interp = await on_demand_service.get_or_generate(context)
        assert interp is not None
        assert interp.source.chunk_id == "chunk_new"

    @pytest.mark.asyncio
    async def test_returns_cached_when_available(
        self, on_demand_service: OnDemandInterpretationService,
    ) -> None:
        context = InterpretationContext(
            chunk_id="chunk_cached",
            chunk_content="Test content",
        )
        # First call generates
        interp1 = await on_demand_service.get_or_generate(context)
        # Second call should return cached
        interp2 = await on_demand_service.get_or_generate(context)
        assert interp1.id == interp2.id

    @pytest.mark.asyncio
    async def test_cache_stats(
        self, on_demand_service: OnDemandInterpretationService,
    ) -> None:
        context = InterpretationContext(
            chunk_id="chunk_stats",
            chunk_content="Test content",
        )
        await on_demand_service.get_or_generate(context)
        stats = on_demand_service.get_cache_stats()
        assert stats["total_size"] >= 1


# ---------------------------------------------------------------------------
# Graph-Aware Generation tests
# ---------------------------------------------------------------------------


class TestGraphAwareGeneration:
    def test_generates_without_graph(
        self, graph_generator: GraphAwareInterpretationGenerator,
    ) -> None:
        context = InterpretationContext(
            chunk_content="Meditation practice for inner peace",
        )
        interp = graph_generator.generate(context)
        assert interp is not None
        assert interp.graph_context is None

    def test_enriches_with_graph_context(
        self, graph_generator: GraphAwareInterpretationGenerator,
    ) -> None:
        context = InterpretationContext(
            chunk_content="Meditation practice for inner peace",
            knowledge_graph_context={
                "related_concepts": ["mindfulness", "awareness"],
                "supporting_books": ["Book A", "Book B"],
                "alternative_traditions": ["Zen", "Sufism"],
                "shared_concepts": ["presence", "stillness"],
                "graph_confidence": 0.8,
            },
        )
        interp = graph_generator.generate(context)
        assert interp.graph_context is not None
        assert len(interp.graph_context.related_concepts) == 2
        assert len(interp.graph_context.supporting_books) == 2
        assert interp.confidence > 0.5  # Boosted by graph

    def test_graph_adds_alternatives(
        self, graph_generator: GraphAwareInterpretationGenerator,
    ) -> None:
        context = InterpretationContext(
            chunk_content="Meditation practice",
            knowledge_graph_context={
                "alternative_traditions": ["Zen", "Sufism"],
            },
        )
        interp = graph_generator.generate(context)
        assert any("Zen" in a or "Sufism" in a for a in interp.alternative_interpretations)


# ---------------------------------------------------------------------------
# Type Selector tests
# ---------------------------------------------------------------------------


class TestTypeSelector:
    def test_selects_conservative_by_default(
        self, type_selector: InterpretationTypeSelector,
    ) -> None:
        context = InterpretationContext(chunk_content="Simple text about truth")
        kind = type_selector.select(context)
        assert kind == "conservative"

    def test_selects_comparative(
        self, type_selector: InterpretationTypeSelector,
    ) -> None:
        context = InterpretationContext(chunk_content="Compare these two approaches")
        kind = type_selector.select(context)
        assert kind == "comparative"

    def test_selects_practical(
        self, type_selector: InterpretationTypeSelector,
    ) -> None:
        context = InterpretationContext(chunk_content="How to practice meditation")
        kind = type_selector.select(context)
        assert kind == "practical"

    def test_selects_exploratory(
        self, type_selector: InterpretationTypeSelector,
    ) -> None:
        context = InterpretationContext(chunk_content="This might possibly suggest")
        kind = type_selector.select(context)
        assert kind == "exploratory"

    def test_selects_cross_tradition_with_graph(
        self, type_selector: InterpretationTypeSelector,
    ) -> None:
        context = InterpretationContext(chunk_content="Meditation practice")
        graph = {"shared_concepts": ["presence"], "alternative_traditions": ["Zen"]}
        kind = type_selector.select(context, graph)
        assert kind == "cross_tradition"


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    @pytest.mark.asyncio
    async def test_on_demand_with_graph(
        self, engine: InterpretationEngine,
    ) -> None:
        service = OnDemandInterpretationService(engine=engine)

        # Mock graph context provider
        class MockProvider:
            async def get_context(self, chunk_id: str, doc_id: str) -> dict:
                return {"related_concepts": ["test"], "graph_confidence": 0.7}

        service.set_graph_context_provider(MockProvider())

        context = InterpretationContext(
            chunk_id="chunk_graph",
            chunk_content="Test content about meditation",
        )
        interp = await service.get_or_generate(context)
        assert interp is not None

    @pytest.mark.asyncio
    async def test_on_demand_idempotent(
        self, on_demand_service: OnDemandInterpretationService,
    ) -> None:
        context = InterpretationContext(
            chunk_id="chunk_idem",
            chunk_content="Test content",
        )
        interp1 = await on_demand_service.get_or_generate(context)
        interp2 = await on_demand_service.get_or_generate(context)
        assert interp1.id == interp2.id
        assert interp1.version == interp2.version


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_existing_interpretation_still_works(self) -> None:
        interp = Interpretation(
            source=SourceReference(document_id="doc1", original_text="text"),
            practical_insight="test",
        )
        assert interp.practical_insight == "test"
        assert interp.interpretation_kind == InterpretationKind.CONSERVATIVE

    def test_existing_engine_still_works(self) -> None:
        engine = InterpretationEngine()
        assert engine._generator is not None
        assert engine._validator is not None
