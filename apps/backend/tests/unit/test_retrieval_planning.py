"""Tests for Retrieval Planning Pipeline per SPEC-22."""

import pytest
from ayeneh.runtime.retrieval_planning import (
    RetrievalPlan,
    RetrievalPlanningPipeline,
    KnowledgeSourceSelection,
    EvidenceRequirement,
    EvidenceRequirementAnalysis,
    GraphTraversalPlan,
    RetrievalStrategyPlan,
    RetrievalCapabilityAnalysis,
)
from ayeneh.runtime.pipeline import QueryAnalysis


@pytest.fixture
def pipeline():
    return RetrievalPlanningPipeline()


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
# RetrievalPlan Artifact
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

    def test_has_spec22_fields(self):
        plan = RetrievalPlan()
        assert hasattr(plan, 'knowledge_sources')
        assert hasattr(plan, 'evidence_requirements')
        assert hasattr(plan, 'starting_nodes')
        assert hasattr(plan, 'traversal_direction')
        assert hasattr(plan, 'relationship_types')
        assert hasattr(plan, 'stopping_conditions')
        assert hasattr(plan, 'retrieval_order')
        assert hasattr(plan, 'parallel_opportunities')
        assert hasattr(plan, 'cache_policy')
        assert hasattr(plan, 'priority_levels')
        assert hasattr(plan, 'early_stop_rules')
        assert hasattr(plan, 'fallback_sources')
        assert hasattr(plan, 'required_capabilities')


# ---------------------------------------------------------------------------
# Pipeline Phases
# ---------------------------------------------------------------------------


class TestPhaseSourceSelection:
    def test_selects_chunk_store(self, pipeline):
        sources = pipeline._phase_source_selection([], [], [], [], "single_book")
        names = [s["name"] for s in sources.selected_sources]
        assert "chunk_store" in names

    def test_selects_concept_registry(self, pipeline):
        sources = pipeline._phase_source_selection(["Self"], [], [], [], "single_book")
        names = [s["name"] for s in sources.selected_sources]
        assert "canonical_concept_registry" in names

    def test_selects_knowledge_graph_for_cross_book(self, pipeline):
        sources = pipeline._phase_source_selection([], [], [], [], "cross_book")
        names = [s["name"] for s in sources.selected_sources]
        assert "knowledge_graph" in names

    def test_all_sources_have_justification(self, pipeline):
        sources = pipeline._phase_source_selection(["Self"], ["ACT"], ["mysticism"], ["ACT"], "cross_book")
        for s in sources.selected_sources:
            assert "justification" in s
            assert len(s["justification"]) > 0


class TestPhaseEvidenceRequirements:
    def test_base_requirement(self, pipeline):
        evidence = pipeline._phase_evidence_requirements("definition", "single_book", "low", ["Awareness"])
        assert len(evidence.requirements) >= 1
        assert evidence.total_min_evidence >= 1

    def test_comparison_requires_multiple(self, pipeline):
        evidence = pipeline._phase_evidence_requirements("comparison", "cross_book", "high", ["Self", "Fana"])
        categories = [r.category for r in evidence.requirements]
        assert "comparison" in categories
        assert evidence.total_min_evidence >= 3

    def test_cross_book_requires_cross_source(self, pipeline):
        evidence = pipeline._phase_evidence_requirements("question", "cross_book", "medium", ["Self"])
        cross_source = [r for r in evidence.requirements if r.cross_source]
        assert len(cross_source) > 0


class TestPhaseGraphTraversal:
    def test_traversal_params(self, pipeline):
        traversal = pipeline._phase_graph_traversal(["Self", "Awareness"], ["ACT"], "cross_book", "high")
        assert traversal.max_depth >= 3
        assert traversal.budget >= 50
        assert "APPEARS_IN" in traversal.relationship_types
        assert len(traversal.starting_nodes) > 0

    def test_stopping_conditions(self, pipeline):
        traversal = pipeline._phase_graph_traversal([], [], "single_book", "low")
        assert "max_depth" in traversal.stopping_conditions
        assert "max_budget" in traversal.stopping_conditions


class TestPhaseStrategyConstruction:
    def test_concept_first_strategy(self, pipeline):
        sources = KnowledgeSourceSelection()
        evidence = EvidenceRequirementAnalysis()
        traversal = GraphTraversalPlan()
        strategy = pipeline._phase_strategy_construction("cross_book", "high", "cross_book", sources, evidence, traversal)
        assert strategy.strategy == "concept_first"
        assert len(strategy.retrieval_order) > 0
        assert len(strategy.parallel_opportunities) > 0
        assert strategy.cache_policy == "read_through"

    def test_book_first_strategy(self, pipeline):
        sources = KnowledgeSourceSelection()
        evidence = EvidenceRequirementAnalysis()
        traversal = GraphTraversalPlan()
        strategy = pipeline._phase_strategy_construction("single_book", "low", "single_source", sources, evidence, traversal)
        assert strategy.strategy == "book_first"


class TestPhaseCapabilityAnalysis:
    def test_cross_book_capabilities(self, pipeline):
        evidence = EvidenceRequirementAnalysis(requirements=[EvidenceRequirement(category="cross_book", min_count=2, cross_source=True)])
        traversal = GraphTraversalPlan(max_depth=3)
        caps = pipeline._phase_capability_analysis("cross_book", "high", "cross_book", evidence, traversal)
        assert "cross_book_retrieval" in caps.required_capabilities
        assert "graph_traversal" in caps.required_capabilities


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def _make_complex_query(self):
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

    def test_executes_all_phases(self, pipeline):
        plan = pipeline.execute(simple_query)
        assert isinstance(plan, RetrievalPlan)

    def test_strategy_selection(self, pipeline):
        plan = pipeline.execute(self._make_complex_query())
        assert plan.strategy in ("concept_first", "topic_first")

    def test_target_concepts(self, pipeline):
        plan = pipeline.execute(self._make_complex_query())
        assert len(plan.target_concepts) > 0

    def test_target_books(self, pipeline):
        plan = pipeline.execute(self._make_complex_query())
        assert len(plan.target_books) > 0

    def test_knowledge_sources_selected(self, pipeline):
        plan = pipeline.execute(self._make_complex_query())
        assert len(plan.knowledge_sources) > 0
        source_names = [s["name"] for s in plan.knowledge_sources]
        assert "chunk_store" in source_names

    def test_evidence_requirements(self, pipeline):
        plan = pipeline.execute(self._make_complex_query())
        assert len(plan.evidence_requirements) > 0
        assert plan.total_min_evidence >= 1

    def test_traversal_plan(self, pipeline):
        plan = pipeline.execute(self._make_complex_query())
        assert plan.max_depth >= 2
        assert plan.traversal_budget >= 40
        assert len(plan.relationship_types) > 0

    def test_capabilities(self, pipeline):
        plan = pipeline.execute(self._make_complex_query())
        assert len(plan.required_capabilities) > 0

    def test_budget_scales_with_concepts(self, pipeline):
        plan = pipeline.execute(self._make_complex_query())
        assert plan.max_retrieval_budget >= 10


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_plan_has_all_required_fields(self, pipeline, simple_query):
        plan = pipeline.execute(simple_query)
        assert hasattr(plan, 'plan_id')
        assert hasattr(plan, 'session_id')
        assert hasattr(plan, 'target_books')
        assert hasattr(plan, 'target_concepts')
        assert hasattr(plan, 'target_topics')
        assert hasattr(plan, 'strategy')
        assert hasattr(plan, 'max_retrieval_budget')
        assert hasattr(plan, 'expected_evidence_count')
        assert hasattr(plan, 'required_evidence_level')
        assert hasattr(plan, 'knowledge_version')
        assert hasattr(plan, 'graph_version')
        assert hasattr(plan, 'knowledge_sources')
        assert hasattr(plan, 'evidence_requirements')
        assert hasattr(plan, 'required_capabilities')
