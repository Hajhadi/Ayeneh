"""Test 08: Streaming verification."""

from __future__ import annotations

import pytest

from integration_tests.conftest import InMemoryKnowledgeGraph
from ayeneh.graph_reasoning.engine import GraphReasoningEngine


@pytest.mark.asyncio
async def test_reason_stream_returns_partial_results(pipeline_components):
    """Verify reason_stream() returns partial results."""
    graph = pipeline_components["graph"]
    engine = GraphReasoningEngine(graph=graph)

    partials = list(engine.reason_stream("What is awareness?"))

    assert len(partials) > 0, "Streaming returned no partials"

    # Should have start event
    assert partials[0]["type"] == "start"

    # Should have evidence event
    evidence_events = [p for p in partials if p["type"] == "evidence"]
    assert len(evidence_events) > 0, "No evidence partial"

    # Should have hypotheses event
    hypothesis_events = [p for p in partials if p["type"] == "hypotheses"]
    assert len(hypothesis_events) > 0, "No hypotheses partial"

    # Should have confidence event
    confidence_events = [p for p in partials if p["type"] == "confidence"]
    assert len(confidence_events) > 0, "No confidence partial"

    # Should have complete event
    complete_events = [p for p in partials if p["type"] == "complete"]
    assert len(complete_events) > 0, "No complete event"


@pytest.mark.asyncio
async def test_streamed_result_matches_normal_result(pipeline_components):
    """Verify final streamed result equals normal result."""
    graph = pipeline_components["graph"]
    engine = GraphReasoningEngine(graph=graph)

    # Normal result
    normal_result = engine.reason("What is mindfulness?")

    # Streamed result
    partials = list(engine.reason_stream("What is mindfulness?"))
    complete = [p for p in partials if p["type"] == "complete"]
    assert complete, "No complete event in stream"
    streamed_result = complete[0]["result"]

    # Core properties should match
    assert normal_result.query == streamed_result.query
    assert len(normal_result.hypotheses) == len(streamed_result.hypotheses)
    assert len(normal_result.conflicts) == len(streamed_result.conflicts)
