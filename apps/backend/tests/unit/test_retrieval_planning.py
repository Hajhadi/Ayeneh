"""Tests for Retrieval Planning per SPEC-01A §74-76."""

import pytest
from ayeneh.runtime.retrieval_planning import (
    RetrievalPlan,
    RetrievalPlanner,
    RetrievalStrategy,
)
from ayeneh.runtime.pipeline import QueryAnalysis


@pytest.fixture
def planner():
    return RetrievalPlanner()


@pytest.fixture
def simple_query():
    qa = QueryAnalysis()
    qa.intent = "definition"
    qa.concepts = ["Awareness"]
    qa.entities = []
    qa.topics = ["self_awareness"]
    qa.book_references = []
    qa.scope = "single_book"
    qa.complexity = "low"
    qa.required_reasoning = "single_source"
    return qa


@pytest.fixture
def complex_query():
    qa = QueryAnalysis()
    qa.intent = "comparison"
    qa.concepts = ["Self", "Fana", "Non-self"]
    qa.entities = ["ACT", "Zen"]
    qa.topics = ["mysticism", "contemplation"]
    qa.book_references = ["ACT", "Zen Mind"]
    qa.scope = "cross_book"
    qa.complexity = "high"
    qa.required_reasoning = "cross_book"
    return qa


# ---------------------------------------------------------------------------
# RetrievalPlan
# ---------------------------------------------------------------------------


class TestRetrievalPlan:
    def test_creation(self):
        plan = RetrievalPlan()
        assert plan.plan_id is not None
        assert len(plan.plan_id) > 0

    def test_immutable(self):
        plan = RetrievalPlan()
        with pytest.raises(AttributeError):
            plan.strategy = "new_strategy"

    def test_has_version_fields(self):
        plan = RetrievalPlan()
        assert plan.knowledge_version == "0.0.0"
        assert plan.graph_version == "0.0.0"
        assert plan.policy_version == "0.0.0"
        assert plan.producer_version == "1.0.0"

    def test_has_timestamp(self):
        plan = RetrievalPlan()
        assert plan.timestamp is not None


# ---------------------------------------------------------------------------
# Planner — Simple Query
# ---------------------------------------------------------------------------


class TestPlannerSimple:
    def test_creates_plan(self, planner, simple_query):
        plan = planner.plan(simple_query)
        assert isinstance(plan, RetrievalPlan)

    def test_strategy_book_first(self, planner, simple_query):
        plan = planner.plan(simple_query)
        assert plan.strategy == RetrievalStrategy.BOOK_FIRST

    def test_budget_low(self, planner, simple_query):
        plan = planner.plan(simple_query)
        assert plan.max_retrieval_budget <= 15

    def test_traversal_limits_low(self, planner, simple_query):
        plan = planner.plan(simple_query)
        assert plan.traversal_limits["max_depth"] <= 2

    def test_expected_evidence(self, planner, simple_query):
        plan = planner.plan(simple_query)
        assert plan.expected_evidence_count <= 6


# ---------------------------------------------------------------------------
# Planner — Complex Query
# ---------------------------------------------------------------------------


class TestPlannerComplex:
    def test_strategy_concept_first(self, planner, complex_query):
        plan = planner.plan(complex_query)
        assert plan.strategy == RetrievalStrategy.CONCEPT_FIRST

    def test_budget_high(self, planner, complex_query):
        plan = planner.plan(complex_query)
        assert plan.max_retrieval_budget >= 20

    def test_traversal_limits_high(self, planner, complex_query):
        plan = planner.plan(complex_query)
        assert plan.traversal_limits["max_depth"] >= 3

    def test_target_concepts(self, planner, complex_query):
        plan = planner.plan(complex_query)
        assert "Self" in plan.target_concepts
        assert "Fana" in plan.target_concepts

    def test_target_books(self, planner, complex_query):
        plan = planner.plan(complex_query)
        assert "ACT" in plan.target_books
        assert "Zen Mind" in plan.target_books


# ---------------------------------------------------------------------------
# Strategy Selection
# ---------------------------------------------------------------------------


class TestStrategySelection:
    def test_cross_book_uses_concept_first(self, planner):
        qa = QueryAnalysis(scope="cross_book", complexity="medium", required_reasoning="cross_book")
        plan = planner.plan(qa)
        assert plan.strategy == RetrievalStrategy.CONCEPT_FIRST

    def test_cross_tradition_uses_topic_first(self, planner):
        qa = QueryAnalysis(scope="cross_tradition", complexity="medium", required_reasoning="cross_tradition")
        plan = planner.plan(qa)
        assert plan.strategy == RetrievalStrategy.TOPIC_FIRST

    def test_high_complexity_uses_concept_first(self, planner):
        qa = QueryAnalysis(scope="single_book", complexity="high", required_reasoning="single_source")
        plan = planner.plan(qa)
        assert plan.strategy == RetrievalStrategy.CONCEPT_FIRST

    def test_default_uses_book_first(self, planner):
        qa = QueryAnalysis(scope="single_book", complexity="low", required_reasoning="single_source")
        plan = planner.plan(qa)
        assert plan.strategy == RetrievalStrategy.BOOK_FIRST


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_plan_has_all_required_fields(self, planner, simple_query):
        plan = planner.plan(simple_query)
        assert hasattr(plan, 'plan_id')
        assert hasattr(plan, 'session_id')
        assert hasattr(plan, 'target_books')
        assert hasattr(plan, 'target_concepts')
        assert hasattr(plan, 'target_topics')
        assert hasattr(plan, 'strategy')
        assert hasattr(plan, 'traversal_limits')
        assert hasattr(plan, 'max_retrieval_budget')
        assert hasattr(plan, 'expected_evidence_count')
        assert hasattr(plan, 'required_evidence_level')
        assert hasattr(plan, 'knowledge_version')
        assert hasattr(plan, 'graph_version')
