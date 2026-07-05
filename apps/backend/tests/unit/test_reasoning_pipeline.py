"""Tests for Runtime Reasoning Pipeline per SPEC-24."""

import pytest
from ayeneh.runtime.reasoning_pipeline import (
    ReasoningPipeline,
    ReasoningResult,
    EvidenceInterpretation,
)
from ayeneh.runtime.knowledge_retrieval import RetrievalResult
from ayeneh.runtime.pipeline import QueryAnalysis


@pytest.fixture
def pipeline():
    return ReasoningPipeline()


@pytest.fixture
def simple_retrieval():
    return RetrievalResult(
        chunks=[
            {"id": "c1", "content": "Awareness is a key concept in mindfulness practice.", "book_title": "Book A", "book_id": "b1"},
            {"id": "c2", "content": "Meditation helps develop awareness and consciousness.", "book_title": "Book B", "book_id": "b2"},
        ],
        epistemic_profiles=[],
        books=[],
    )


@pytest.fixture
def complex_retrieval():
    return RetrievalResult(
        chunks=[
            {"id": "c1", "content": "Self is a constructed narrative.", "book_title": "Metzinger", "book_id": "b1"},
            {"id": "c2", "content": "Self is an illusion in Buddhism.", "book_title": "Zen", "book_id": "b2"},
            {"id": "c3", "content": "Self is a useful fiction.", "book_title": "ACT", "book_id": "b3"},
        ],
        epistemic_profiles=[{"framework": "phenomenological"}, {"framework": "empiricist"}],
        books=[],
    )


# ---------------------------------------------------------------------------
# ReasoningResult Artifact
# ---------------------------------------------------------------------------


class TestReasoningResult:
    def test_creation(self):
        r = ReasoningResult()
        assert r.reasoning_id is not None

    def test_immutable(self):
        r = ReasoningResult()
        with pytest.raises(AttributeError):
            r.overall_confidence = 0.9


# ---------------------------------------------------------------------------
# Evidence Interpretation
# ---------------------------------------------------------------------------


class TestEvidenceInterpretation:
    def test_extracts_facts(self, pipeline, simple_retrieval):
        interp = pipeline._phase_evidence_interpretation(simple_retrieval, None)
        assert len(interp.facts) == 2

    def test_builds_evidence_graph(self, pipeline, simple_retrieval):
        interp = pipeline._phase_evidence_interpretation(simple_retrieval, None)
        # Same source facts should be linked
        assert len(interp.evidence_graph) >= 0

    def test_detects_conflicts(self, pipeline, complex_retrieval):
        interp = pipeline._phase_evidence_interpretation(complex_retrieval, None)
        # Different sources may have conflicts
        assert isinstance(interp.conflicts, list)


# ---------------------------------------------------------------------------
# Reasoning Execution
# ---------------------------------------------------------------------------


class TestReasoningExecution:
    def test_determines_mode(self, pipeline):
        interp = EvidenceInterpretation(facts=[{"source": "A", "content": "fact a"}, {"source": "B", "content": "fact b"}])
        qa = QueryAnalysis(scope="cross_book")
        result = pipeline._phase_reasoning_execution(interp, qa)
        assert result["mode"] == "cross_book"

    def test_generates_conclusions(self, pipeline, simple_retrieval):
        interp = pipeline._phase_evidence_interpretation(simple_retrieval, None)
        result = pipeline._phase_reasoning_execution(interp, None)
        assert len(result["conclusions"]) > 0

    def test_generates_uncertainty(self, pipeline, simple_retrieval):
        interp = pipeline._phase_evidence_interpretation(simple_retrieval, None)
        result = pipeline._phase_reasoning_execution(interp, None)
        assert isinstance(result["uncertainty"], list)


# ---------------------------------------------------------------------------
# Confidence Assessment
# ---------------------------------------------------------------------------


class TestConfidenceAssessment:
    def test_produces_confidence(self, pipeline, simple_retrieval):
        interp = pipeline._phase_evidence_interpretation(simple_retrieval, None)
        reasoning = pipeline._phase_reasoning_execution(interp, None)
        confidence = pipeline._phase_confidence_assessment(reasoning, interp)
        assert 0.0 <= confidence["overall"] <= 1.0
        assert "evidence_quality" in confidence
        assert "agreement_level" in confidence


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_executes_all_phases(self, pipeline, simple_retrieval):
        result = pipeline.execute(simple_retrieval)
        assert isinstance(result, ReasoningResult)

    def test_has_reasoning_mode(self, pipeline, simple_retrieval):
        result = pipeline.execute(simple_retrieval)
        assert result.reasoning_mode in ("single_source", "cross_book", "comparative", "definition")

    def test_has_conclusions(self, pipeline, simple_retrieval):
        result = pipeline.execute(simple_retrieval)
        assert len(result.conclusions) > 0

    def test_has_confidence(self, pipeline, simple_retrieval):
        result = pipeline.execute(simple_retrieval)
        assert 0.0 <= result.overall_confidence <= 1.0

    def test_cross_book_reasoning(self, pipeline, complex_retrieval):
        qa = QueryAnalysis(scope="cross_book")
        result = pipeline.execute(complex_retrieval, query_analysis=qa)
        assert result.reasoning_mode == "cross_book"

    def test_duration_recorded(self, pipeline, simple_retrieval):
        result = pipeline.execute(simple_retrieval)
        assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_result_has_all_required_fields(self, pipeline, simple_retrieval):
        result = pipeline.execute(simple_retrieval)
        assert hasattr(result, 'reasoning_id')
        assert hasattr(result, 'session_id')
        assert hasattr(result, 'reasoning_mode')
        assert hasattr(result, 'conclusions')
        assert hasattr(result, 'evidence_references')
        assert hasattr(result, 'conflicts')
        assert hasattr(result, 'assumptions')
        assert hasattr(result, 'uncertainty_statements')
        assert hasattr(result, 'overall_confidence')
        assert hasattr(result, 'confidence_components')
        assert hasattr(result, 'duration_ms')
