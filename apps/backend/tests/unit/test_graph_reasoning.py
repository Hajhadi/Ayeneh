"""Comprehensive tests for Graph Reasoning Engine."""

from __future__ import annotations

import pytest

from ayeneh.graph_reasoning.engine import (
    AgreementAnalyzer,
    ConflictAnalyzer,
    EvidenceAggregator,
    GraphReasoningEngine,
    HypothesisGenerator,
    ReasoningConfidenceAggregator,
)
from ayeneh.graph_reasoning.types import (
    Hypothesis,
    ReasoningChain,
    ReasoningConflict,
    ReasoningConfidence,
    ReasoningExplanation,
    ReasoningResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> GraphReasoningEngine:
    return GraphReasoningEngine()


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestGraphReasoningEngine:
    def test_reason_returns_result(self, engine: GraphReasoningEngine) -> None:
        result = engine.reason("test query")
        assert isinstance(result, ReasoningResult)
        assert result.query == "test query"

    def test_reason_with_context(self, engine: GraphReasoningEngine) -> None:
        result = engine.reason("test", {"concepts": ["mindfulness"]})
        assert isinstance(result, ReasoningResult)

    def test_reason_has_confidence(self, engine: GraphReasoningEngine) -> None:
        result = engine.reason("test")
        assert 0.0 <= result.confidence.overall_confidence <= 1.0

    def test_reason_has_explanation(self, engine: GraphReasoningEngine) -> None:
        result = engine.reason("test")
        assert isinstance(result.explanation, ReasoningExplanation)


# ---------------------------------------------------------------------------
# Hypothesis tests
# ---------------------------------------------------------------------------


class TestHypothesisGenerator:
    def test_generates_hypothesis(self) -> None:
        gen = HypothesisGenerator()
        evidence = [{"id": "e1", "content": "test"}]
        hypotheses = gen.generate(evidence, "test query")
        assert len(hypotheses) > 0

    def test_empty_evidence(self) -> None:
        gen = HypothesisGenerator()
        hypotheses = gen.generate([], "test")
        assert len(hypotheses) == 0


# ---------------------------------------------------------------------------
# Conflict tests
# ---------------------------------------------------------------------------


class TestConflictAnalyzer:
    def test_detects_conflicts(self) -> None:
        analyzer = ConflictAnalyzer()
        evidence = [
            {"id": "e1", "stance": "yes"},
            {"id": "e2", "stance": "no"},
        ]
        conflicts = analyzer.analyze(evidence)
        assert len(conflicts) > 0

    def test_no_conflicts(self) -> None:
        analyzer = ConflictAnalyzer()
        evidence = [
            {"id": "e1", "stance": "yes"},
            {"id": "e2", "stance": "yes"},
        ]
        conflicts = analyzer.analyze(evidence)
        assert len(conflicts) == 0


# ---------------------------------------------------------------------------
# Agreement tests
# ---------------------------------------------------------------------------


class TestAgreementAnalyzer:
    def test_detects_agreements(self) -> None:
        analyzer = AgreementAnalyzer()
        evidence = [
            {"id": "e1", "stance": "yes"},
            {"id": "e2", "stance": "yes"},
        ]
        agreements = analyzer.analyze(evidence)
        assert len(agreements) > 0


# ---------------------------------------------------------------------------
# Confidence tests
# ---------------------------------------------------------------------------


class TestReasoningConfidence:
    def test_aggregates_confidence(self) -> None:
        aggregator = ReasoningConfidenceAggregator()
        confidence = aggregator.aggregate({"evidence": 0.8, "graph": 0.7})
        assert 0.0 <= confidence.overall_confidence <= 1.0


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_engine_works(self, engine: GraphReasoningEngine) -> None:
        result = engine.reason("test")
        assert isinstance(result, ReasoningResult)
