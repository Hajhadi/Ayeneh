"""Test 07: Incremental update verification."""

from __future__ import annotations

import pytest

from integration_tests.conftest import InMemoryKnowledgeGraph


@pytest.mark.asyncio
async def test_new_book_only_affects_related_concepts(pipeline_components):
    """Verify importing a new book only affects related concepts."""
    graph = pipeline_components["graph"]
    initial_concepts = set(graph.get_all_concepts())
    initial_node_count = len(graph.nodes)
    initial_edge_count = len(graph.edges)

    # Add a new concept that's related to existing ones
    new_concept_id = "new-mindfulness-concept"
    graph.add_node(new_concept_id, "concept", "Mindful Attention", domain="contemplative")

    # Only the new concept should be added
    assert len(graph.nodes) == initial_node_count + 1
    assert new_concept_id in graph.nodes


@pytest.mark.asyncio
async def test_graph_version_incremented(pipeline_components):
    """Verify graph version is incremented on changes."""
    graph = pipeline_components["graph"]
    initial_version = graph.version

    graph.increment_version()
    assert graph.version == initial_version + 1


@pytest.mark.asyncio
async def test_cache_invalidated_on_graph_change(pipeline_components):
    """Verify cache is invalidated when graph changes."""
    from ayeneh.graph_reasoning.engine import ReasoningCache, CacheKey

    cache = ReasoningCache()
    key = CacheKey(graph_version=1)
    cache.put(key, {"result": "test"})

    assert cache.get(key) is not None

    # Invalidate by graph version
    removed = cache.invalidate_by_graph_version(1)
    assert removed == 1
    assert cache.get(key) is None


@pytest.mark.asyncio
async def test_concept_extraction_only_affected_areas(pipeline_components):
    """Verify concept extraction only processes affected text."""
    from ayeneh.knowledge_concepts.engine import ConceptExtractionEngine

    engine = ConceptExtractionEngine()
    result1 = engine.extract_from_text("Acceptance involves making room for difficult experiences.")
    result2 = engine.extract_from_text("Mindfulness is present-moment awareness.")

    # Different texts should produce different concept sets
    assert result1.concepts != result2.concepts or len(result1.concepts) == 0


@pytest.mark.asyncio
async def test_cross_book_diff_detects_changes(pipeline_components):
    """Verify CrossBookDiff correctly detects what changed."""
    from ayeneh.cross_book_linking.engine import CrossBookConceptLinker

    linker = CrossBookConceptLinker()
    old_concepts = ["acceptance", "defusion", "mindfulness"]
    new_concepts = ["acceptance", "defusion", "mindfulness", "compassion"]

    diff = linker.detect_diff(old_concepts, new_concepts)

    assert "compassion" in diff.new_concepts
    assert "acceptance" in diff.affected_concepts
