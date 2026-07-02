"""Test 10: Determinism verification — identical queries produce identical results."""

from __future__ import annotations

import pytest

from integration_tests.pipeline_runner import PipelineRunner


@pytest.mark.asyncio
async def test_same_reasoning_chain(pipeline_components):
    """Verify identical queries produce the same reasoning chain."""
    runner = PipelineRunner(pipeline_components)
    question = "What is acceptance?"

    result1 = await runner.run(question)
    result2 = await runner.run(question)

    # Dialogue analysis should be deterministic
    assert result1.dialogue_analysis is not None
    assert result2.dialogue_analysis is not None
    assert (
        result1.dialogue_analysis.user_intention
        == result2.dialogue_analysis.user_intention
    )


@pytest.mark.asyncio
async def test_same_confidence(pipeline_components):
    """Verify identical queries produce the same confidence values."""
    runner = PipelineRunner(pipeline_components)
    question = "What is mindfulness?"

    result1 = await runner.run(question)
    result2 = await runner.run(question)

    # Safety confidence should be deterministic
    safety1 = next(
        (s for s in result1.stages if s.stage_name == "epistemic_safety"), None
    )
    safety2 = next(
        (s for s in result2.stages if s.stage_name == "epistemic_safety"), None
    )
    assert safety1 is not None
    assert safety2 is not None
    assert safety1.confidence == safety2.confidence


@pytest.mark.asyncio
async def test_same_provenance(pipeline_components):
    """Verify identical queries produce consistent provenance."""
    runner = PipelineRunner(pipeline_components)
    question = "What is defusion?"

    result1 = await runner.run(question)
    result2 = await runner.run(question)

    # Both should have provenance bundles
    assert result1.provenance_bundle.id
    assert result2.provenance_bundle.id
    # Both should have the same engine versions
    assert (
        result1.provenance_bundle.engine_versions
        == result2.provenance_bundle.engine_versions
    )


@pytest.mark.asyncio
async def test_graph_reasoning_deterministic(pipeline_components):
    """Verify graph reasoning components produce deterministic results."""
    from ayeneh.graph_reasoning.engine import (
        GraphReasoningEngine,
        HypothesisGenerator,
        ConflictAnalyzer,
        AgreementAnalyzer,
        ReasoningConfidenceAggregator,
    )

    graph = pipeline_components["graph"]

    # Test individual components are deterministic
    evidence = [{"id": "e1", "type": "concept", "title": "test", "stance": "support"}]

    gen = HypothesisGenerator()
    h1 = gen.generate(evidence, "What is awareness?")
    h2 = gen.generate(evidence, "What is awareness?")
    assert len(h1) == len(h2)
    assert h1[0].statement == h2[0].statement

    analyzer = ConflictAnalyzer()
    c1 = analyzer.analyze(evidence)
    c2 = analyzer.analyze(evidence)
    assert len(c1) == len(c2)

    agreement = AgreementAnalyzer()
    a1 = agreement.analyze(evidence)
    a2 = agreement.analyze(evidence)
    assert len(a1) == len(a2)

    agg = ReasoningConfidenceAggregator()
    r1 = agg.aggregate({"evidence": 0.5, "reasoning": 0.6})
    r2 = agg.aggregate({"evidence": 0.5, "reasoning": 0.6})
    assert r1.overall_confidence == r2.overall_confidence
