"""Test 11: Failure recovery — graceful degradation under simulated failures."""

from __future__ import annotations

import pytest

from ayeneh.epistemic_safety.engine import EpistemicSafetyEngine
from ayeneh.graph_reasoning.engine import GraphReasoningEngine
from ayeneh.reasoning.engine import ReasoningEngine


@pytest.mark.asyncio
async def test_missing_concept_graceful(pipeline_components):
    """Verify system handles missing concepts gracefully."""
    graph = pipeline_components["graph"]
    engine = GraphReasoningEngine(graph=graph)

    # Query about a non-existent concept
    result = engine.reason("What is the meaning ofxyznonexistent?")

    # Should not crash
    assert result is not None
    assert result.query == "What is the meaning ofxyznonexistent?"
    # Should have low confidence
    assert result.confidence.overall_confidence <= 1.0


@pytest.mark.asyncio
async def test_empty_graph_graceful():
    """Verify system handles empty graph gracefully."""
    from integration_tests.conftest import InMemoryKnowledgeGraph

    graph = InMemoryKnowledgeGraph()
    engine = GraphReasoningEngine(graph=graph)

    result = engine.reason("What is consciousness?")

    assert result is not None
    assert result.hypotheses == []
    assert result.conflicts == []


@pytest.mark.asyncio
async def test_provider_failure_graceful(pipeline_components):
    """Verify system handles LLM provider failure gracefully."""
    from ayeneh.agents.conversation import ConversationAgent

    # Use LLM that will fail
    class FailingLLM:
        async def chat(self, *args, **kwargs):
            raise RuntimeError("Provider unavailable")

    agent = ConversationAgent(llm=FailingLLM())
    output = await agent.execute({
        "user_id": "test",
        "user_message": "Hello",
        "conversation_history": [],
    })

    assert output.status == "failed"
    assert "error" in output.data


@pytest.mark.asyncio
async def test_safety_engine_never_crashes():
    """Verify safety engine never crashes on any input."""
    engine = EpistemicSafetyEngine()

    test_inputs = [
        "",
        "Normal response.",
        "You should trust me. I know your problem.",
        "This is scientifically proven and always true.",
        "A" * 10000,
    ]

    for text in test_inputs:
        result = engine.validate(text)
        assert result is not None
        assert 0.0 <= result.overall_safety_score <= 1.0


@pytest.mark.asyncio
async def test_reasoning_engine_degrades(pipeline_components):
    """Verify reasoning engine degrades gracefully with limited evidence."""
    runner_reasoning = ReasoningEngine()

    session = await runner_reasoning.reason(
        user_id="test",
        query="What is the meaning of life?",
        context={},
    )

    # Should complete without error
    assert session is not None
    assert session.summary is not None
    # Should report limitations
    assert len(session.uncertainties) > 0
