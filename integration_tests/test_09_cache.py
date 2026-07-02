"""Test 09: Cache verification."""

from __future__ import annotations

import pytest

from ayeneh.graph_reasoning.engine import ReasoningCache
from ayeneh.graph_reasoning.types import CacheKey
from ayeneh.knowledge_interpretation.engine import InterpretationCache
from ayeneh.knowledge_interpretation.types import InterpretationCacheKey


@pytest.mark.asyncio
async def test_cache_hit():
    """Verify cache hit returns stored result."""
    cache = ReasoningCache()
    key = CacheKey(graph_version=1, policy_version="conservative")
    result = {"query": "test", "confidence": 0.7}

    cache.put(key, result)
    cached = cache.get(key)

    assert cached is not None
    assert cached["query"] == "test"
    stats = cache.get_stats()
    assert stats["hits"] == 1


@pytest.mark.asyncio
async def test_cache_miss():
    """Verify cache miss returns None."""
    cache = ReasoningCache()
    key = CacheKey(graph_version=999)
    cached = cache.get(key)

    assert cached is None
    stats = cache.get_stats()
    assert stats["misses"] == 1


@pytest.mark.asyncio
async def test_cache_invalidation_by_graph_version():
    """Verify cache invalidation by graph version."""
    cache = ReasoningCache()

    key1 = CacheKey(graph_version=1)
    key2 = CacheKey(graph_version=2)
    cache.put(key1, {"result": "v1"})
    cache.put(key2, {"result": "v2"})

    removed = cache.invalidate_by_graph_version(1)
    assert removed == 1
    assert cache.get(key1) is None
    assert cache.get(key2) is not None


@pytest.mark.asyncio
async def test_interpretation_cache_hit():
    """Verify interpretation cache hit."""
    from integration_tests.conftest import FakeLLMGateway
    from ayeneh.knowledge_interpretation.engine import (
        InterpretationEngine,
        InterpretationCache,
        OnDemandInterpretationService,
    )
    from ayeneh.knowledge_interpretation.types import InterpretationContext

    engine = InterpretationEngine()
    cache = InterpretationCache()
    service = OnDemandInterpretationService(engine, cache)

    context = InterpretationContext(
        document_id="doc-1",
        book_id="book-1",
        chapter_id="ch-1",
        chapter_title="Test",
        chunk_id="chunk-1",
        chunk_content="Acceptance involves making room for difficult experiences.",
    )

    # First call generates
    interp1 = await service.get_or_generate(context)
    # Second call should hit cache
    interp2 = await service.get_or_generate(context)

    assert interp1.id == interp2.id
    stats = service.get_cache_stats()
    assert stats["total_size"] >= 1


@pytest.mark.asyncio
async def test_interpretation_cache_invalidation():
    """Verify interpretation cache invalidation."""
    cache = InterpretationCache()

    key = InterpretationCacheKey(
        chunk_id="chunk-1",
        product_profile="default",
        interpretation_kind="conservative",
    )

    from ayeneh.knowledge_interpretation.types import Interpretation, SourceReference
    interp = Interpretation(source=SourceReference(chunk_id="chunk-1"))
    cache.put_by_key(key, interp)

    assert cache.get_by_key(key) is not None

    removed = cache.invalidate("chunk-1")
    assert removed
    assert cache.get_by_key(key) is None
