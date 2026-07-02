"""Test 12: Performance — latency, memory, and cache efficiency measurements."""

from __future__ import annotations

import time

import pytest

from integration_tests.pipeline_runner import PipelineRunner


@pytest.mark.asyncio
async def test_retrieval_time(pipeline_components):
    """Measure retrieval latency."""
    runner = PipelineRunner(pipeline_components)
    start = time.monotonic()
    result = await runner.run("What is acceptance?")
    duration_ms = (time.monotonic() - start) * 1000

    retrieval_stage = next(
        (s for s in result.stages if s.stage_name == "retrieval"), None
    )
    assert retrieval_stage is not None
    assert retrieval_stage.duration_ms >= 0
    # Retrieval should be fast (< 5 seconds for test data)
    assert retrieval_stage.duration_ms < 5000


@pytest.mark.asyncio
async def test_graph_traversal_time(pipeline_components):
    """Measure graph traversal latency."""
    from ayeneh.graph_reasoning.engine import GraphReasoningEngine

    graph = pipeline_components["graph"]
    engine = GraphReasoningEngine(graph=graph)

    start = time.monotonic()
    result = engine.reason("What is awareness?")
    duration_ms = (time.monotonic() - start) * 1000

    assert duration_ms < 5000, f"Graph reasoning took {duration_ms:.0f}ms"


@pytest.mark.asyncio
async def test_reasoning_time(pipeline_components):
    """Measure reasoning latency."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is mindfulness?")

    reasoning_stage = next(
        (s for s in result.stages if s.stage_name == "graph_reasoning"), None
    )
    assert reasoning_stage is not None
    assert reasoning_stage.duration_ms < 5000


@pytest.mark.asyncio
async def test_safety_time(pipeline_components):
    """Measure safety validation latency."""
    from ayeneh.epistemic_safety.engine import EpistemicSafetyEngine

    engine = EpistemicSafetyEngine()
    start = time.monotonic()
    result = engine.validate("This is a test response about awareness.")
    duration_ms = (time.monotonic() - start) * 1000

    assert duration_ms < 1000, f"Safety validation took {duration_ms:.0f}ms"


@pytest.mark.asyncio
async def test_total_latency(pipeline_components):
    """Verify total pipeline latency is within bounds."""
    runner = PipelineRunner(pipeline_components)
    result = await runner.run("What is defusion?")

    assert result.total_duration_ms < 15000, (
        f"Total pipeline took {result.total_duration_ms:.0f}ms"
    )


@pytest.mark.asyncio
async def test_cache_efficiency(pipeline_components):
    """Verify cache hit/miss behavior works correctly."""
    from ayeneh.graph_reasoning.engine import ReasoningCache
    from ayeneh.graph_reasoning.types import CacheKey

    cache = ReasoningCache()

    # Miss
    key = CacheKey(graph_version=0)
    assert cache.get(key) is None

    # Put
    cache.put(key, {"result": "test"})

    # Hit
    start = time.monotonic()
    cached = cache.get(key)
    duration = (time.monotonic() - start) * 1000

    assert cached is not None
    assert duration < 10  # Cache lookup should be very fast
