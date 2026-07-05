"""Tests for Response Validation and Generation Pipeline per SPEC-25."""

import pytest
from ayeneh.runtime.response_pipeline import (
    ResponsePipeline,
    ResponseArtifact,
    ResponseValidationResult,
)
from ayeneh.runtime.reasoning_pipeline import ReasoningResult
from ayeneh.runtime.pipeline import QueryAnalysis


@pytest.fixture
def pipeline():
    return ResponsePipeline()


@pytest.fixture
def simple_reasoning():
    return ReasoningResult(
        conclusions=[
            {"statement": "Awareness is a key concept in mindfulness.", "source": "Book A", "confidence": 0.8},
        ],
        evidence_references=[{"fact": "evidence 1", "source": "Book A"}],
        conflicts=[],
        uncertainty_statements=["Limited evidence available"],
        overall_confidence=0.7,
    )


@pytest.fixture
def empty_reasoning():
    return ReasoningResult(
        conclusions=[],
        evidence_references=[],
        conflicts=[],
        overall_confidence=0.2,
    )


# ---------------------------------------------------------------------------
# ResponseArtifact
# ---------------------------------------------------------------------------


class TestResponseArtifact:
    def test_creation(self):
        r = ResponseArtifact(response_text="Test response")
        assert r.response_text == "Test response"
        assert r.response_id is not None

    def test_immutable(self):
        r = ResponseArtifact()
        with pytest.raises(AttributeError):
            r.response_text = "changed"


# ---------------------------------------------------------------------------
# Validation Result
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_valid(self):
        v = ResponseValidationResult(is_valid=True)
        assert v.is_valid is True

    def test_invalid(self):
        v = ResponseValidationResult(is_valid=False, errors=["error"])
        assert v.is_valid is False
        assert len(v.errors) == 1


# ---------------------------------------------------------------------------
# Pipeline Phases
# ---------------------------------------------------------------------------


class TestPhaseValidation:
    def test_valid_with_conclusions(self, pipeline, simple_reasoning):
        v = pipeline._phase_validation(simple_reasoning, None)
        assert v.is_valid is True

    def test_invalid_without_conclusions(self, pipeline, empty_reasoning):
        v = pipeline._phase_validation(empty_reasoning, None)
        assert v.is_valid is False


class TestPhaseResponseConstruction:
    def test_constructs_response(self, pipeline, simple_reasoning):
        v = ResponseValidationResult(is_valid=True)
        result = pipeline._phase_response_construction(simple_reasoning, None, v)
        assert len(result["response_text"]) > 0
        assert len(result["citations"]) > 0

    def test_invalid_returns_fallback(self, pipeline, empty_reasoning):
        v = ResponseValidationResult(is_valid=False)
        result = pipeline._phase_response_construction(empty_reasoning, None, v)
        assert "متأسفانه" in result["response_text"]


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_executes_all_phases(self, pipeline, simple_reasoning):
        result = pipeline.execute(simple_reasoning)
        assert isinstance(result, ResponseArtifact)

    def test_has_response_text(self, pipeline, simple_reasoning):
        result = pipeline.execute(simple_reasoning)
        assert len(result.response_text) > 0

    def test_has_citations(self, pipeline, simple_reasoning):
        result = pipeline.execute(simple_reasoning)
        assert isinstance(result.citations, list)

    def test_validation_passed(self, pipeline, simple_reasoning):
        result = pipeline.execute(simple_reasoning)
        assert result.validation_passed is True

    def test_empty_reasoning_fails_validation(self, pipeline, empty_reasoning):
        result = pipeline.execute(empty_reasoning)
        assert result.validation_passed is False

    def test_duration_recorded(self, pipeline, simple_reasoning):
        result = pipeline.execute(simple_reasoning)
        assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_artifact_has_all_required_fields(self, pipeline, simple_reasoning):
        result = pipeline.execute(simple_reasoning)
        assert hasattr(result, 'response_id')
        assert hasattr(result, 'session_id')
        assert hasattr(result, 'reasoning_id')
        assert hasattr(result, 'response_text')
        assert hasattr(result, 'citations')
        assert hasattr(result, 'uncertainty_statements')
        assert hasattr(result, 'overall_confidence')
        assert hasattr(result, 'validation_passed')
        assert hasattr(result, 'duration_ms')


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


class TestStreaming:
    def test_is_streaming_field_default(self):
        r = ResponseArtifact()
        assert r.is_streaming is False

    def test_is_streaming_field_set(self):
        r = ResponseArtifact(is_streaming=True)
        assert r.is_streaming is True

    def test_stream_yields_artifacts(self, pipeline, simple_reasoning):
        artifacts = list(pipeline.stream(simple_reasoning))
        assert len(artifacts) == 2
        assert artifacts[0].is_streaming is True
        assert artifacts[1].is_streaming is False

    def test_stream_text_matches_execute(self, pipeline, simple_reasoning):
        artifacts = list(pipeline.stream(simple_reasoning))
        execute_result = pipeline.execute(simple_reasoning)
        assert artifacts[1].response_text == execute_result.response_text

    def test_stream_calls_on_chunk(self, pipeline, simple_reasoning):
        chunks = []
        list(pipeline.stream(simple_reasoning, on_chunk=chunks.append))
        assert len(chunks) == 1
        assert len(chunks[0]) > 0

    def test_stream_passes_session_id(self, pipeline, simple_reasoning):
        artifacts = list(pipeline.stream(simple_reasoning, session_id="test-sess"))
        assert artifacts[0].session_id == "test-sess"
        assert artifacts[1].session_id == "test-sess"
