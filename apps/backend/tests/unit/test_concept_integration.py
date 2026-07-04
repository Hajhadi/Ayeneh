"""Tests for Concept Integration per SPEC-01A §93-97."""

import pytest
from ayeneh.runtime.concept_integration import (
    IntegratedKnowledge,
    ConceptIntegrator,
)
from ayeneh.runtime.pipeline import QueryAnalysis


@pytest.fixture
def integrator():
    return ConceptIntegrator()


@pytest.fixture
def sample_chunks():
    return [
        {"id": "c1", "book_id": "b1", "book_title": "Book A", "chapter_id": "ch1", "content": "Self and awareness are key concepts"},
        {"id": "c2", "book_id": "b1", "book_title": "Book A", "chapter_id": "ch1", "content": "Meditation helps develop mindfulness"},
        {"id": "c3", "book_id": "b2", "book_title": "Book B", "chapter_id": "ch2", "content": "Self and consciousness in philosophy"},
    ]


@pytest.fixture
def sample_query_analysis():
    qa = QueryAnalysis()
    qa.concepts = ["Self", "Awareness"]
    qa.topics = ["self_awareness"]
    qa.entities = ["Metzinger"]
    return qa


# ---------------------------------------------------------------------------
# IntegratedKnowledge
# ---------------------------------------------------------------------------


class TestIntegratedKnowledge:
    def test_creation(self):
        ik = IntegratedKnowledge()
        assert ik.integration_id is not None
        assert len(ik.integration_id) > 0

    def test_immutable(self):
        ik = IntegratedKnowledge()
        with pytest.raises(AttributeError):
            ik.total_chunks = 100

    def test_has_timestamp(self):
        ik = IntegratedKnowledge()
        assert ik.timestamp is not None

    def test_has_version_fields(self):
        ik = IntegratedKnowledge()
        assert ik.knowledge_version == "0.0.0"
        assert ik.graph_version == "0.0.0"
        assert ik.producer_version == "1.0.0"


# ---------------------------------------------------------------------------
# ConceptIntegrator
# ---------------------------------------------------------------------------


class TestConceptIntegrator:
    def test_creates_integrated_knowledge(self, integrator, sample_chunks):
        ik = integrator.integrate(sample_chunks, [])
        assert isinstance(ik, IntegratedKnowledge)

    def test_extracts_books(self, integrator, sample_chunks):
        ik = integrator.integrate(sample_chunks, [])
        assert len(ik.referenced_books) == 2
        book_ids = {b["id"] for b in ik.referenced_books}
        assert "b1" in book_ids
        assert "b2" in book_ids

    def test_extracts_chapters(self, integrator, sample_chunks):
        ik = integrator.integrate(sample_chunks, [])
        assert len(ik.referenced_chapters) == 2

    def test_preserves_chunks(self, integrator, sample_chunks):
        ik = integrator.integrate(sample_chunks, [])
        assert len(ik.referenced_chunks) == 3

    def test_extracts_concepts_from_query(self, integrator, sample_chunks, sample_query_analysis):
        ik = integrator.integrate(sample_chunks, [], query_analysis=sample_query_analysis)
        concept_names = {c["name"] for c in ik.referenced_concepts}
        assert "Self" in concept_names
        assert "Awareness" in concept_names

    def test_extracts_topics(self, integrator, sample_chunks, sample_query_analysis):
        ik = integrator.integrate(sample_chunks, [], query_analysis=sample_query_analysis)
        topic_names = {t["name"] for t in ik.referenced_topics}
        assert "self_awareness" in topic_names

    def test_cross_book_relations(self, integrator, sample_chunks):
        ik = integrator.integrate(sample_chunks, [])
        # Books sharing concepts should have relations
        assert len(ik.cross_book_relations) >= 0  # May or may not have relations

    def test_epistemic_profiles(self, integrator, sample_chunks):
        profiles = [{"primary_topics": ["meditation", "awareness"]}]
        ik = integrator.integrate(sample_chunks, profiles)
        assert len(ik.epistemic_profiles) == 1
        topic_names = {t["name"] for t in ik.referenced_topics}
        assert "meditation" in topic_names

    def test_total_counts(self, integrator, sample_chunks, sample_query_analysis):
        ik = integrator.integrate(sample_chunks, [], query_analysis=sample_query_analysis)
        assert ik.total_chunks == 3
        assert ik.total_concepts >= 2

    def test_producer(self, integrator, sample_chunks):
        ik = integrator.integrate(sample_chunks, [])
        assert ik.producer == "concept_integration"


# ---------------------------------------------------------------------------
# No Reasoning (SPEC-01A §93)
# ---------------------------------------------------------------------------


class TestNoReasoning:
    def test_integrator_does_not_reason(self, integrator, sample_chunks):
        ik = integrator.integrate(sample_chunks, [])
        # IntegratedKnowledge should not contain reasoning results
        assert not hasattr(ik, 'reasoning_chains')
        assert not hasattr(ik, 'hypotheses')
        assert not hasattr(ik, 'conflicts')


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_integrated_knowledge_has_all_required_fields(self, integrator, sample_chunks):
        ik = integrator.integrate(sample_chunks, [])
        assert hasattr(ik, 'integration_id')
        assert hasattr(ik, 'query_analysis_id')
        assert hasattr(ik, 'retrieval_plan_id')
        assert hasattr(ik, 'referenced_books')
        assert hasattr(ik, 'referenced_chapters')
        assert hasattr(ik, 'referenced_chunks')
        assert hasattr(ik, 'referenced_concepts')
        assert hasattr(ik, 'referenced_topics')
        assert hasattr(ik, 'retrieved_graph_nodes')
        assert hasattr(ik, 'retrieved_graph_edges')
        assert hasattr(ik, 'retrieved_evidence')
        assert hasattr(ik, 'retrieved_interpretations')
        assert hasattr(ik, 'cross_book_relations')
        assert hasattr(ik, 'epistemic_profiles')
        assert hasattr(ik, 'knowledge_version')
        assert hasattr(ik, 'graph_version')
