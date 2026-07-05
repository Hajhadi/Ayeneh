"""Tests for Knowledge Retrieval Pipeline per SPEC-23."""

import pytest
from ayeneh.runtime.knowledge_retrieval import (
    KnowledgeRetrievalPipeline,
    RetrievalResult,
    RetrievalValidation,
)
from ayeneh.runtime.retrieval_planning import RetrievalPlan


@pytest.fixture
def pipeline():
    return KnowledgeRetrievalPipeline()


@pytest.fixture
def simple_plan():
    return RetrievalPlan(
        target_concepts=["Awareness"],
        target_books=["ACT"],
        strategy="book_first",
        max_retrieval_budget=10,
    )


@pytest.fixture
def complex_plan():
    return RetrievalPlan(
        target_concepts=["Self", "Fana", "Non-self"],
        target_books=["ACT", "Zen Mind"],
        strategy="concept_first",
        max_retrieval_budget=25,
    )


# ---------------------------------------------------------------------------
# RetrievalResult Artifact
# ---------------------------------------------------------------------------


class TestRetrievalResult:
    def test_creation(self):
        r = RetrievalResult()
        assert r.result_id is not None
        assert len(r.result_id) > 0

    def test_immutable(self):
        r = RetrievalResult()
        with pytest.raises(AttributeError):
            r.total_chunks = 100

    def test_has_timestamp(self):
        r = RetrievalResult()
        assert r.timestamp is not None

    def test_has_version_fields(self):
        r = RetrievalResult()
        assert r.knowledge_version == "0.0.0"
        assert r.graph_version == "0.0.0"
        assert r.producer_version == "1.0.0"


# ---------------------------------------------------------------------------
# Retrieval Validation
# ---------------------------------------------------------------------------


class TestRetrievalValidation:
    def test_valid_result(self):
        v = RetrievalValidation(is_valid=True, evidence_complete=True)
        assert v.is_valid is True

    def test_invalid_result(self):
        v = RetrievalValidation(is_valid=False, evidence_complete=False)
        assert v.is_valid is False


# ---------------------------------------------------------------------------
# Pipeline Phases
# ---------------------------------------------------------------------------


class TestPhaseSourceExecution:
    def test_retrieves_chunks(self, pipeline, simple_plan):
        result = pipeline.execute(simple_plan)
        assert result.total_chunks >= 0

    def test_retrieves_profiles(self, pipeline, simple_plan):
        result = pipeline.execute(simple_plan)
        assert isinstance(result.epistemic_profiles, list)

    def test_retrieves_books(self, pipeline, simple_plan):
        result = pipeline.execute(simple_plan)
        assert isinstance(result.books, list)


class TestPhaseEvidenceAggregation:
    def test_deduplicates_chunks(self, pipeline):
        source_data = {
            "chunks": [
                {"id": "c1", "content": "test"},
                {"id": "c1", "content": "test"},
                {"id": "c2", "content": "test2"},
            ],
            "profiles": [],
            "books": [],
        }
        aggregated = pipeline._phase_evidence_aggregation(source_data)
        assert len(aggregated["chunks"]) == 2

    def test_builds_citations(self, pipeline):
        source_data = {
            "chunks": [{"id": "c1", "chapter_id": "ch1", "book_id": "b1", "book_title": "Book A", "sequence": 1}],
            "profiles": [],
            "books": [],
        }
        aggregated = pipeline._phase_evidence_aggregation(source_data)
        assert len(aggregated["citations"]) == 1
        assert aggregated["citations"][0]["book_title"] == "Book A"


class TestPhaseRetrievalValidation:
    def test_valid_with_chunks(self, pipeline):
        aggregated = {"chunks": [{"id": "c1"}], "profiles": [], "books": []}
        validation = pipeline._phase_retrieval_validation(aggregated)
        assert validation.is_valid is True

    def test_invalid_without_chunks(self, pipeline):
        aggregated = {"chunks": [], "profiles": [], "books": []}
        validation = pipeline._phase_retrieval_validation(aggregated)
        assert validation.is_valid is False


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_executes_all_phases(self, pipeline, simple_plan):
        result = pipeline.execute(simple_plan)
        assert isinstance(result, RetrievalResult)

    def test_has_result_id(self, pipeline, simple_plan):
        result = pipeline.execute(simple_plan)
        assert result.result_id is not None

    def test_has_timestamp(self, pipeline, simple_plan):
        result = pipeline.execute(simple_plan)
        assert result.timestamp is not None

    def test_retrieval_confidence(self, pipeline, simple_plan):
        result = pipeline.execute(simple_plan)
        assert result.retrieval_confidence > 0

    def test_duration_recorded(self, pipeline, simple_plan):
        result = pipeline.execute(simple_plan)
        assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_result_has_all_required_fields(self, pipeline, simple_plan):
        result = pipeline.execute(simple_plan)
        assert hasattr(result, 'result_id')
        assert hasattr(result, 'session_id')
        assert hasattr(result, 'plan_id')
        assert hasattr(result, 'chunks')
        assert hasattr(result, 'epistemic_profiles')
        assert hasattr(result, 'books')
        assert hasattr(result, 'citations')
        assert hasattr(result, 'total_chunks')
        assert hasattr(result, 'total_profiles')
        assert hasattr(result, 'retrieval_confidence')
        assert hasattr(result, 'duration_ms')
