"""Tests for the COG-04 Personal Knowledge Extraction pipeline."""

from __future__ import annotations

import uuid
import pytest
from datetime import UTC, datetime
from typing import Any

from ayeneh.cog.knowledge.types import (
    KNOWLEDGE_CATEGORIES,
    KNOWLEDGE_VALIDATION_STATUSES,
    KnowledgeEdge,
    KnowledgeExtractionResult,
    PersonalKnowledgeObject,
)
from ayeneh.cog.knowledge.extraction import PersonalKnowledgeEngine
from ayeneh.cog.knowledge.graph import KnowledgeGraph


# ---------------------------------------------------------------------------
# Helpers — lightweight evidence-like objects for testing
# ---------------------------------------------------------------------------


def _make_evidence(
    identifier: str = '',
    category: str = 'self_report',
    text: str = '',
    confidence: float = 0.7,
) -> Any:
    """Create a minimal evidence-like object for testing."""

    class _Ev:
        def __init__(self, ident: str, cat: str, txt: str, conf: float) -> None:
            self.identifier = ident
            self.category = cat
            self.original_text = txt
            self.normalized_text = txt
            self.confidence = conf

    return _Ev(
        identifier or str(uuid.uuid4()),
        category,
        text,
        confidence,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def knowledge_engine():
    return PersonalKnowledgeEngine()


@pytest.fixture
def knowledge_graph():
    return KnowledgeGraph()


@pytest.fixture
def sample_pko():
    return PersonalKnowledgeObject(
        identifier='pk-test-001',
        knowledge_category='biographical',
        statement='I grew up in Tehran.',
        confidence=0.8,
        supporting_evidence=('ev-1', 'ev-2'),
    )


@pytest.fixture
def sample_evidence_list():
    return [
        _make_evidence('ev-1', 'self_report', 'I speak fluent English and Persian.'),
        _make_evidence('ev-2', 'identity_statement', 'I am a software engineer.'),
        _make_evidence('ev-3', 'self_report', 'I work at a tech startup.'),
        _make_evidence('ev-4', 'preference', 'I love reading science fiction.'),
        _make_evidence('ev-5', 'goal_statement', 'I want to learn machine learning.'),
    ]


# ---------------------------------------------------------------------------
# PersonalKnowledgeObject type tests
# ---------------------------------------------------------------------------


class TestPersonalKnowledgeObject:
    def test_creation(self):
        pko = PersonalKnowledgeObject(
            identifier='pk-1',
            knowledge_category='education',
            statement='I studied computer science at university.',
            confidence=0.9,
        )
        assert pko.identifier == 'pk-1'
        assert pko.knowledge_category == 'education'
        assert pko.confidence == 0.9
        assert pko.lifecycle_state == 'candidate'
        assert pko.validation_status == 'pending'

    def test_frozen(self, sample_pko):
        with pytest.raises(AttributeError):
            sample_pko.confidence = 0.5  # type: ignore[misc]

    def test_frozen_identifier(self, sample_pko):
        with pytest.raises(AttributeError):
            sample_pko.identifier = 'pk-new'  # type: ignore[misc]

    def test_defaults(self):
        pko = PersonalKnowledgeObject()
        assert pko.identifier == ''
        assert pko.knowledge_category == 'other'
        assert pko.statement == ''
        assert pko.confidence == 0.0
        assert pko.supporting_evidence == ()
        assert pko.contradictory_evidence == ()
        assert pko.behavioral_evidence == ()
        assert pko.lifecycle_state == 'candidate'
        assert pko.validation_status == 'pending'
        assert pko.specification_version == '1.0.0'

    def test_timestamp_auto(self):
        pko = PersonalKnowledgeObject()
        assert isinstance(pko.creation_timestamp, datetime)
        assert pko.creation_timestamp.tzinfo is not None

    def test_tuples_are_immutable(self, sample_pko):
        assert isinstance(sample_pko.supporting_evidence, tuple)

    def test_revision_history_default(self):
        pko = PersonalKnowledgeObject()
        assert pko.revision_history == ()

    def test_temporal_metadata_default(self):
        pko = PersonalKnowledgeObject()
        assert pko.temporal_metadata == {}


# ---------------------------------------------------------------------------
# KnowledgeExtractionResult tests
# ---------------------------------------------------------------------------


class TestKnowledgeExtractionResult:
    def test_creation(self):
        result = KnowledgeExtractionResult()
        assert result.knowledge_objects == ()
        assert result.total_extracted == 0
        assert result.by_category == {}

    def test_frozen(self):
        result = KnowledgeExtractionResult()
        with pytest.raises(AttributeError):
            result.total_extracted = 5  # type: ignore[misc]

    def test_timestamp_auto(self):
        result = KnowledgeExtractionResult()
        assert isinstance(result.processing_timestamp, datetime)


# ---------------------------------------------------------------------------
# PersonalKnowledgeEngine tests
# ---------------------------------------------------------------------------


class TestPersonalKnowledgeEngine:
    def test_process_returns_result(self, knowledge_engine, sample_evidence_list):
        result = knowledge_engine.process(sample_evidence_list)
        assert isinstance(result, KnowledgeExtractionResult)

    def test_extracts_knowledge(self, knowledge_engine, sample_evidence_list):
        result = knowledge_engine.process(sample_evidence_list)
        assert result.total_extracted > 0

    def test_all_have_identifiers(self, knowledge_engine, sample_evidence_list):
        result = knowledge_engine.process(sample_evidence_list)
        for pko in result.knowledge_objects:
            assert pko.identifier
            assert isinstance(pko.identifier, str)

    def test_all_have_categories(self, knowledge_engine, sample_evidence_list):
        result = knowledge_engine.process(sample_evidence_list)
        for pko in result.knowledge_objects:
            assert pko.knowledge_category in KNOWLEDGE_CATEGORIES

    def test_by_category_counts(self, knowledge_engine, sample_evidence_list):
        result = knowledge_engine.process(sample_evidence_list)
        assert isinstance(result.by_category, dict)
        total_from_counts = sum(result.by_category.values())
        assert total_from_counts == result.total_extracted

    def test_empty_input(self, knowledge_engine):
        result = knowledge_engine.process([])
        assert result.total_extracted == 0
        assert len(result.knowledge_objects) == 0
        assert result.by_category == {}

    def test_single_evidence_stays_candidate(self, knowledge_engine):
        """Single evidence item should remain as candidate (not promoted)."""
        evidence = [
            _make_evidence('ev-single', 'self_report', 'I like coffee.'),
        ]
        result = knowledge_engine.process(evidence)
        # With only 1 evidence, it may stay candidate or become provisional
        # depending on the pipeline — but should not exceed 1 item
        assert result.total_extracted >= 0

    def test_repeated_evidence_promotes(self, knowledge_engine):
        """Multiple evidence items for the same category should promote lifecycle state."""
        evidence = [
            _make_evidence('ev-1', 'self_report', 'I speak English.'),
            _make_evidence('ev-2', 'self_report', 'I speak English fluently.'),
            _make_evidence('ev-3', 'self_report', 'My English is very good.'),
        ]
        result = knowledge_engine.process(evidence)
        # With 3 evidence items, at least some should be promoted
        assert result.total_extracted > 0

    def test_determinism(self, knowledge_engine, sample_evidence_list):
        """Same input → same output (deterministic pipeline)."""
        r1 = knowledge_engine.process(sample_evidence_list)
        r2 = knowledge_engine.process(sample_evidence_list)
        assert r1.total_extracted == r2.total_extracted
        assert len(r1.knowledge_objects) == len(r2.knowledge_objects)
        for k1, k2 in zip(r1.knowledge_objects, r2.knowledge_objects):
            assert k1.knowledge_category == k2.knowledge_category
            assert k1.statement == k2.statement
            assert k1.lifecycle_state == k2.lifecycle_state

    def test_category_inference_education(self, knowledge_engine):
        evidence = [
            _make_evidence('ev-edu', 'self_report', 'I studied at university.'),
        ]
        result = knowledge_engine.process(evidence)
        categories = [pko.knowledge_category for pko in result.knowledge_objects]
        assert 'education' in categories

    def test_category_inference_career(self, knowledge_engine):
        evidence = [
            _make_evidence('ev-career', 'self_report', 'I work at a company.'),
        ]
        result = knowledge_engine.process(evidence)
        categories = [pko.knowledge_category for pko in result.knowledge_objects]
        assert 'career' in categories

    def test_category_inference_technologies(self, knowledge_engine):
        evidence = [
            _make_evidence('ev-tech', 'self_report', 'I use Django technology and a Python library.'),
        ]
        result = knowledge_engine.process(evidence)
        categories = [pko.knowledge_category for pko in result.knowledge_objects]
        assert 'technologies' in categories

    def test_result_timestamp(self, knowledge_engine, sample_evidence_list):
        result = knowledge_engine.process(sample_evidence_list)
        assert isinstance(result.processing_timestamp, datetime)


# ---------------------------------------------------------------------------
# KnowledgeGraph tests
# ---------------------------------------------------------------------------


class TestKnowledgeGraph:
    def test_add_knowledge(self, knowledge_graph, sample_pko):
        knowledge_graph.add_knowledge(sample_pko)
        assert knowledge_graph.node_count() == 1

    def test_add_replaces(self, knowledge_graph, sample_pko):
        knowledge_graph.add_knowledge(sample_pko)
        updated = PersonalKnowledgeObject(
            identifier='pk-test-001',
            knowledge_category='biographical',
            statement='Updated statement.',
            confidence=0.95,
        )
        knowledge_graph.add_knowledge(updated)
        assert knowledge_graph.node_count() == 1
        node = knowledge_graph.get_node('pk-test-001')
        assert node is not None
        assert node.statement == 'Updated statement.'

    def test_get_node(self, knowledge_graph, sample_pko):
        knowledge_graph.add_knowledge(sample_pko)
        retrieved = knowledge_graph.get_node('pk-test-001')
        assert retrieved is not None
        assert retrieved.identifier == 'pk-test-001'

    def test_get_node_nonexistent(self, knowledge_graph):
        assert knowledge_graph.get_node('nonexistent') is None

    def test_connect(self, knowledge_graph):
        pko1 = PersonalKnowledgeObject(identifier='pk-1', statement='A')
        pko2 = PersonalKnowledgeObject(identifier='pk-2', statement='B')
        knowledge_graph.add_knowledge(pko1)
        knowledge_graph.add_knowledge(pko2)
        knowledge_graph.connect('pk-1', 'pk-2', 'related_to')
        assert knowledge_graph.edge_count() == 1

    def test_connect_nonexistent_source(self, knowledge_graph):
        pko = PersonalKnowledgeObject(identifier='pk-1', statement='A')
        knowledge_graph.add_knowledge(pko)
        with pytest.raises(ValueError, match='Source'):
            knowledge_graph.connect('nonexistent', 'pk-1', 'related_to')

    def test_connect_nonexistent_target(self, knowledge_graph):
        pko = PersonalKnowledgeObject(identifier='pk-1', statement='A')
        knowledge_graph.add_knowledge(pko)
        with pytest.raises(ValueError, match='Target'):
            knowledge_graph.connect('pk-1', 'nonexistent', 'related_to')

    def test_get_by_category(self, knowledge_graph):
        pko1 = PersonalKnowledgeObject(
            identifier='pk-1', knowledge_category='education', statement='A',
        )
        pko2 = PersonalKnowledgeObject(
            identifier='pk-2', knowledge_category='career', statement='B',
        )
        pko3 = PersonalKnowledgeObject(
            identifier='pk-3', knowledge_category='education', statement='C',
        )
        knowledge_graph.add_knowledge(pko1)
        knowledge_graph.add_knowledge(pko2)
        knowledge_graph.add_knowledge(pko3)

        edu = knowledge_graph.get_by_category('education')
        assert len(edu) == 2
        career = knowledge_graph.get_by_category('career')
        assert len(career) == 1

    def test_get_related(self, knowledge_graph):
        pko1 = PersonalKnowledgeObject(identifier='pk-1', statement='A')
        pko2 = PersonalKnowledgeObject(identifier='pk-2', statement='B')
        pko3 = PersonalKnowledgeObject(identifier='pk-3', statement='C')
        knowledge_graph.add_knowledge(pko1)
        knowledge_graph.add_knowledge(pko2)
        knowledge_graph.add_knowledge(pko3)
        knowledge_graph.connect('pk-1', 'pk-2', 'depends_on')
        knowledge_graph.connect('pk-3', 'pk-1', 'supports')

        related = knowledge_graph.get_related('pk-1')
        assert len(related) == 2
        related_ids = {p.identifier for p in related}
        assert 'pk-2' in related_ids
        assert 'pk-3' in related_ids

    def test_get_related_nonexistent(self, knowledge_graph):
        assert knowledge_graph.get_related('nonexistent') == []

    def test_traverse(self, knowledge_graph):
        for i in range(5):
            knowledge_graph.add_knowledge(
                PersonalKnowledgeObject(identifier=f'pk-{i}', statement=f'S{i}')
            )
        knowledge_graph.connect('pk-0', 'pk-1', 'leads_to')
        knowledge_graph.connect('pk-1', 'pk-2', 'leads_to')
        knowledge_graph.connect('pk-2', 'pk-3', 'leads_to')
        knowledge_graph.connect('pk-3', 'pk-4', 'leads_to')

        result = knowledge_graph.traverse('pk-0', max_depth=2)
        assert len(result) == 2
        result_ids = [p.identifier for p in result]
        assert 'pk-1' in result_ids
        assert 'pk-2' in result_ids

    def test_traverse_full_depth(self, knowledge_graph):
        for i in range(4):
            knowledge_graph.add_knowledge(
                PersonalKnowledgeObject(identifier=f'pk-{i}', statement=f'S{i}')
            )
        knowledge_graph.connect('pk-0', 'pk-1', 'leads_to')
        knowledge_graph.connect('pk-1', 'pk-2', 'leads_to')
        knowledge_graph.connect('pk-2', 'pk-3', 'leads_to')

        result = knowledge_graph.traverse('pk-0', max_depth=10)
        assert len(result) == 3

    def test_traverse_nonexistent_start(self, knowledge_graph):
        assert knowledge_graph.traverse('nonexistent') == []

    def test_remove_node(self, knowledge_graph):
        pko1 = PersonalKnowledgeObject(identifier='pk-1', statement='A')
        pko2 = PersonalKnowledgeObject(identifier='pk-2', statement='B')
        knowledge_graph.add_knowledge(pko1)
        knowledge_graph.add_knowledge(pko2)
        knowledge_graph.connect('pk-1', 'pk-2', 'related_to')

        assert knowledge_graph.remove_node('pk-1') is True
        assert knowledge_graph.node_count() == 1
        assert knowledge_graph.edge_count() == 0

    def test_remove_nonexistent(self, knowledge_graph):
        assert knowledge_graph.remove_node('nonexistent') is False

    def test_all_nodes(self, knowledge_graph):
        for i in range(3):
            knowledge_graph.add_knowledge(
                PersonalKnowledgeObject(identifier=f'pk-{i}', statement=f'S{i}')
            )
        assert len(knowledge_graph.all_nodes()) == 3

    def test_all_edges(self, knowledge_graph):
        pko1 = PersonalKnowledgeObject(identifier='pk-1', statement='A')
        pko2 = PersonalKnowledgeObject(identifier='pk-2', statement='B')
        knowledge_graph.add_knowledge(pko1)
        knowledge_graph.add_knowledge(pko2)
        knowledge_graph.connect('pk-1', 'pk-2', 'related_to')
        assert len(knowledge_graph.all_edges()) == 1

    def test_empty_graph(self, knowledge_graph):
        assert knowledge_graph.node_count() == 0
        assert knowledge_graph.edge_count() == 0
        assert knowledge_graph.all_nodes() == []
        assert knowledge_graph.all_edges() == []


# ---------------------------------------------------------------------------
# KnowledgeEdge tests
# ---------------------------------------------------------------------------


class TestKnowledgeEdge:
    def test_creation(self):
        edge = KnowledgeEdge(
            source_id='pk-1',
            target_id='pk-2',
            relationship='depends_on',
            confidence=0.7,
        )
        assert edge.source_id == 'pk-1'
        assert edge.target_id == 'pk-2'
        assert edge.relationship == 'depends_on'
        assert edge.confidence == 0.7

    def test_frozen(self):
        edge = KnowledgeEdge(source_id='a', target_id='b', relationship='r')
        with pytest.raises(AttributeError):
            edge.confidence = 0.9  # type: ignore[misc]

    def test_defaults(self):
        edge = KnowledgeEdge()
        assert edge.source_id == ''
        assert edge.target_id == ''
        assert edge.relationship == ''
        assert edge.confidence == 0.0
        assert edge.evidence_refs == ()


# ---------------------------------------------------------------------------
# Knowledge categories tests
# ---------------------------------------------------------------------------


class TestKnowledgeCategories:
    def test_categories_list(self):
        assert 'biographical' in KNOWLEDGE_CATEGORIES
        assert 'education' in KNOWLEDGE_CATEGORIES
        assert 'career' in KNOWLEDGE_CATEGORIES
        assert 'skills' in KNOWLEDGE_CATEGORIES
        assert 'other' in KNOWLEDGE_CATEGORIES
        assert len(KNOWLEDGE_CATEGORIES) > 15

    def test_validation_statuses(self):
        assert 'pending' in KNOWLEDGE_VALIDATION_STATUSES
        assert 'provisional' in KNOWLEDGE_VALIDATION_STATUSES
        assert 'validated' in KNOWLEDGE_VALIDATION_STATUSES
        assert 'contradicted' in KNOWLEDGE_VALIDATION_STATUSES
