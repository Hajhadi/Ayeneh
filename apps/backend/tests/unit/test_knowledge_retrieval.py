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


# ---------------------------------------------------------------------------
# Conversation History (KRA-008)
# ---------------------------------------------------------------------------


class TestConversationHistory:
    def test_conversation_history_param_accepted(self, pipeline, simple_plan):
        history = [{"role": "user", "content": "Tell me about awareness"}]
        result = pipeline.execute(simple_plan, conversation_history=history)
        assert isinstance(result, RetrievalResult)

    def test_conversation_context_stored(self, pipeline, simple_plan):
        history = [{"role": "user", "content": "Tell me about awareness"}]
        result = pipeline.execute(simple_plan, conversation_history=history)
        assert result.conversation_context == history

    def test_no_conversation_history(self, pipeline, simple_plan):
        result = pipeline.execute(simple_plan)
        assert result.conversation_context == []

    def test_none_conversation_history(self, pipeline, simple_plan):
        result = pipeline.execute(simple_plan, conversation_history=None)
        assert result.conversation_context == []


# ---------------------------------------------------------------------------
# Cache Integration (KRA-009)
# ---------------------------------------------------------------------------


class TestCacheIntegration:
    def setup_method(self):
        KnowledgeRetrievalPipeline._cache.clear()

    def test_cache_miss_on_first_query(self, pipeline, simple_plan):
        result = pipeline.execute(simple_plan)
        assert result.cache_misses == 1
        assert result.cache_hits == 0

    def test_cache_hit_on_second_query(self, pipeline, simple_plan):
        pipeline.execute(simple_plan)
        # Clear DB-related side effects but keep cache
        result = pipeline.execute(simple_plan)
        assert result.cache_hits == 1

    def test_cache_max_size(self):
        for i in range(105):
            plan = RetrievalPlan(
                target_concepts=[f"concept_{i}"],
                target_books=[],
                strategy="concept_first",
                max_retrieval_budget=5,
            )
            KnowledgeRetrievalPipeline()._phase_source_execution(plan)
        assert len(KnowledgeRetrievalPipeline._cache) <= KnowledgeRetrievalPipeline._CACHE_MAX_SIZE

    def test_cache_lru_eviction(self):
        for i in range(101):
            plan = RetrievalPlan(
                target_concepts=[f"concept_{i}"],
                target_books=[],
                strategy="concept_first",
                max_retrieval_budget=5,
            )
            KnowledgeRetrievalPipeline()._phase_source_execution(plan)
        # Oldest entry should have been evicted
        first_key = "|".join(sorted(["concept_0"]))
        assert first_key not in KnowledgeRetrievalPipeline._cache

    def test_different_plans_get_separate_cache_entries(self, pipeline):
        plan1 = RetrievalPlan(
            target_concepts=["ConceptA"], target_books=[], strategy="concept_first", max_retrieval_budget=5,
        )
        plan2 = RetrievalPlan(
            target_concepts=["ConceptB"], target_books=[], strategy="concept_first", max_retrieval_budget=5,
        )
        pipeline.execute(plan1)
        pipeline.execute(plan2)
        assert len(KnowledgeRetrievalPipeline._cache) == 2
