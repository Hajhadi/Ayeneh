"""Integration tests for the INF inference architecture pipeline."""

from __future__ import annotations

import pytest

from ayeneh.inf.inference.engine import InferenceEngine
from ayeneh.inf.inference.types import (
    EVIDENCE_STANDARDS,
    INFERENCE_TYPES,
    InferenceResult,
)
from ayeneh.inf.graph_reasoner.engine import GraphReasoningEngine
from ayeneh.inf.graph_reasoner.types import PATTERN_TYPES, GraphReasoningResult
from ayeneh.inf.contradiction.engine import ContradictionResolver
from ayeneh.inf.contradiction.types import (
    CONTRADICTION_CATEGORIES,
    CONTRADICTION_SEVERITY_LEVELS,
    ContradictionResult,
)
from ayeneh.inf.hypothesis.engine import HypothesisEngine
from ayeneh.inf.hypothesis.types import (
    HYPOTHESIS_SOURCES,
    HYPOTHESIS_STATUSES,
    HypothesisResult,
)
from ayeneh.inf.multihop.engine import MultiHopReasoningEngine
from ayeneh.inf.multihop.types import HOP_TYPES, MultiHopResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def inference_engine():
    return InferenceEngine()


@pytest.fixture
def graph_engine():
    return GraphReasoningEngine()


@pytest.fixture
def contradiction_engine():
    return ContradictionResolver()


@pytest.fixture
def hypothesis_engine():
    return HypothesisEngine()


@pytest.fixture
def multihop_engine():
    return MultiHopReasoningEngine()


@pytest.fixture
def sample_context():
    return {
        "context_id": "integration-test-ctx",
        "domain": "general",
        "user_message": "I believe strongly in my abilities but my actions show otherwise.",
        "conversation_history": [
            {"role": "user", "content": "I always succeed at everything I do."},
            {"role": "assistant", "content": "That's a strong claim. Can you give examples?"},
            {"role": "user", "content": "Well, I failed my last exam but I'll do better next time."},
        ],
    }


@pytest.fixture
def sample_evidence():
    return [
        {"evidence_id": "ev-1", "content": "User claims high self-efficacy", "source": "dialogue"},
        {"evidence_id": "ev-2", "content": "User reports recent failure", "source": "dialogue"},
        {"evidence_id": "ev-3", "content": "User expresses optimism about future", "source": "dialogue"},
    ]


# ---------------------------------------------------------------------------
# Full pipeline integration
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """End-to-end INF pipeline: context → inference → graph → contradictions → hypotheses."""

    def test_full_pipeline_returns_all_results(
        self, inference_engine, graph_engine, contradiction_engine,
        hypothesis_engine, sample_context,
    ):
        inf_result = inference_engine.process(sample_context, [])
        graph_result = graph_engine.process(sample_context)
        contradiction_result = contradiction_engine.process([], sample_context)
        hypothesis_result = hypothesis_engine.process([], None, sample_context)

        assert isinstance(inf_result, InferenceResult)
        assert isinstance(graph_result, GraphReasoningResult)
        assert isinstance(contradiction_result, ContradictionResult)
        assert isinstance(hypothesis_result, HypothesisResult)

    def test_full_pipeline_confidence_chain(
        self, inference_engine, graph_engine, contradiction_engine,
        hypothesis_engine, sample_context,
    ):
        inf_result = inference_engine.process(sample_context, [])
        graph_result = graph_engine.process(sample_context)
        contradiction_result = contradiction_engine.process([], sample_context)
        hypothesis_result = hypothesis_engine.process([], None, sample_context)

        assert 0.0 <= inf_result.overall_confidence <= 1.0
        assert 0.0 <= graph_result.overall_confidence <= 1.0
        assert 0.0 <= contradiction_result.overall_consistency <= 1.0
        assert 0.0 <= hypothesis_result.overall_confidence <= 1.0

    def test_pipeline_output_fields_populated(
        self, inference_engine, graph_engine, contradiction_engine,
        hypothesis_engine, sample_context,
    ):
        inf_result = inference_engine.process(sample_context, [])
        graph_result = graph_engine.process(sample_context)
        contradiction_result = contradiction_engine.process([], sample_context)
        hypothesis_result = hypothesis_engine.process([], None, sample_context)

        assert hasattr(inf_result, "inferences")
        assert hasattr(inf_result, "evidence_assessment")
        assert hasattr(graph_result, "patterns")
        assert hasattr(graph_result, "subgraph")
        assert hasattr(contradiction_result, "contradictions")
        assert hasattr(contradiction_result, "classifications")
        assert hasattr(hypothesis_result, "hypotheses")
        assert hasattr(hypothesis_result, "evidence_gaps")


# ---------------------------------------------------------------------------
# Inference confidence estimation
# ---------------------------------------------------------------------------


class TestInferenceConfidence:
    def test_confidence_range(self, inference_engine, sample_context):
        result = inference_engine.process(sample_context, [])
        assert 0.0 <= result.overall_confidence <= 1.0

    def test_evidence_quality_assessment(self, inference_engine, sample_context):
        result = inference_engine.process(sample_context, [])
        qa = result.evidence_assessment
        assert 0.0 <= qa.overall() <= 1.0

    def test_inference_types_from_catalogue(self, inference_engine, sample_context):
        result = inference_engine.process(sample_context, [])
        for inf in result.inferences:
            assert inf.inference_type in INFERENCE_TYPES or inf.inference_type == ""

    def test_empty_context_yields_low_confidence(self, inference_engine):
        result = inference_engine.process({}, [])
        assert result.overall_confidence <= 0.5


# ---------------------------------------------------------------------------
# Graph pattern detection
# ---------------------------------------------------------------------------


class TestGraphPatterns:
    def test_graph_returns_result(self, graph_engine, sample_context):
        result = graph_engine.process(sample_context)
        assert isinstance(result, GraphReasoningResult)

    def test_patterns_are_known_types(self, graph_engine, sample_context):
        result = graph_engine.process(sample_context)
        for pattern in result.patterns:
            assert pattern.pattern_type in PATTERN_TYPES or pattern.pattern_type == ""

    def test_graph_confidence_range(self, graph_engine, sample_context):
        result = graph_engine.process(sample_context)
        assert 0.0 <= result.overall_confidence <= 1.0

    def test_subgraph_populated(self, graph_engine, sample_context):
        result = graph_engine.process(sample_context)
        assert result.subgraph is not None


# ---------------------------------------------------------------------------
# Contradiction detection and classification
# ---------------------------------------------------------------------------


class TestContradictionDetection:
    def test_contradictions_detected(self, contradiction_engine, sample_context):
        result = contradiction_engine.process([], sample_context)
        assert isinstance(result, ContradictionResult)
        assert isinstance(result.contradictions, tuple)

    def test_classifications_use_known_categories(self, contradiction_engine, sample_context):
        result = contradiction_engine.process([], sample_context)
        for cls in result.classifications:
            assert cls.category in CONTRADICTION_CATEGORIES or cls.category == ""

    def test_severity_levels_valid(self, contradiction_engine, sample_context):
        result = contradiction_engine.process([], sample_context)
        for cls in result.classifications:
            assert cls.severity in CONTRADICTION_SEVERITY_LEVELS or cls.severity == ""

    def test_consistency_range(self, contradiction_engine, sample_context):
        result = contradiction_engine.process([], sample_context)
        assert 0.0 <= result.overall_consistency <= 1.0


# ---------------------------------------------------------------------------
# Hypothesis generation and Bayesian updating
# ---------------------------------------------------------------------------


class TestHypothesisGeneration:
    def test_hypotheses_generated(self, hypothesis_engine, sample_context):
        result = hypothesis_engine.process([], None, sample_context)
        assert isinstance(result, HypothesisResult)
        assert isinstance(result.hypotheses, tuple)

    def test_hypothesis_statuses_valid(self, hypothesis_engine, sample_context):
        result = hypothesis_engine.process([], None, sample_context)
        for hyp in result.hypotheses:
            assert hyp.current_status in HYPOTHESIS_STATUSES or hyp.current_status == ""

    def test_hypothesis_confidence_range(self, hypothesis_engine, sample_context):
        result = hypothesis_engine.process([], None, sample_context)
        assert 0.0 <= result.overall_confidence <= 1.0

    def test_hypothesis_with_evidence(self, hypothesis_engine, sample_evidence):
        result = hypothesis_engine.process(sample_evidence, None, None)
        assert isinstance(result, HypothesisResult)

    def test_strongest_hypothesis_is_valid_id(self, hypothesis_engine, sample_context):
        result = hypothesis_engine.process([], None, sample_context)
        if result.strongest_hypothesis:
            assert isinstance(result.strongest_hypothesis, str)


# ---------------------------------------------------------------------------
# Multi-hop reasoning
# ---------------------------------------------------------------------------


class TestMultiHopReasoning:
    def test_multihop_returns_result(self, multihop_engine):
        result = multihop_engine.process([], None)
        assert isinstance(result, MultiHopResult)

    def test_multihop_confidence_range(self, multihop_engine):
        result = multihop_engine.process([], None)
        assert 0.0 <= result.overall_confidence <= 1.0

    def test_chains_are_tuple(self, multihop_engine):
        result = multihop_engine.process([], None)
        assert isinstance(result.chains, tuple)


# ---------------------------------------------------------------------------
# Cross-module integration
# ---------------------------------------------------------------------------


class TestCrossModuleIntegration:
    def test_inference_feeds_graph(self, inference_engine, graph_engine, sample_context):
        inf_result = inference_engine.process(sample_context, [])
        inf_dicts = [vars(i) for i in inf_result.inferences]
        enriched_context = {**sample_context, "inferences": inf_dicts}
        graph_result = graph_engine.process(enriched_context)
        assert isinstance(graph_result, GraphReasoningResult)

    def test_graph_feeds_contradictions(
        self, graph_engine, contradiction_engine, sample_context,
    ):
        graph_result = graph_engine.process(sample_context)
        pattern_dicts = [vars(p) for p in graph_result.patterns]
        contradiction_result = contradiction_engine.process(pattern_dicts, sample_context)
        assert isinstance(contradiction_result, ContradictionResult)

    def test_contradictions_feed_hypotheses(
        self, contradiction_engine, hypothesis_engine, sample_context,
    ):
        contradiction_result = contradiction_engine.process([], sample_context)
        contradiction_dicts = [vars(c) for c in contradiction_result.contradictions]
        hypothesis_result = hypothesis_engine.process(
            contradiction_dicts, None, sample_context,
        )
        assert isinstance(hypothesis_result, HypothesisResult)

    def test_full_chain_inference_to_hypotheses(
        self, inference_engine, graph_engine, contradiction_engine,
        hypothesis_engine, sample_context,
    ):
        inf_result = inference_engine.process(sample_context, [])
        inf_dicts = [vars(i) for i in inf_result.inferences]

        graph_result = graph_engine.process({**sample_context, "inferences": inf_dicts})
        pattern_dicts = [vars(p) for p in graph_result.patterns]

        contradiction_result = contradiction_engine.process(pattern_dicts, sample_context)
        contradiction_dicts = [vars(c) for c in contradiction_result.contradictions]

        hypothesis_result = hypothesis_engine.process(
            contradiction_dicts + inf_dicts, None, sample_context,
        )

        assert isinstance(hypothesis_result, HypothesisResult)
        assert 0.0 <= hypothesis_result.overall_confidence <= 1.0

    def test_inference_counts_deterministic(self, inference_engine, sample_context):
        r1 = inference_engine.process(sample_context, [])
        r2 = inference_engine.process(sample_context, [])
        assert len(r1.inferences) == len(r2.inferences)
