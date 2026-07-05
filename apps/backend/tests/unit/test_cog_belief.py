"""Tests for the COG-06 Belief Modeling pipeline."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.cog.belief.types import (
    BELIEF_CATEGORIES,
    BELIEF_RELATIONSHIP_TYPES,
    BeliefNetwork,
    BeliefObject,
)
from ayeneh.cog.belief.modeling import BeliefModelingEngine, BeliefModelingResult
from ayeneh.cog.belief.network import BeliefNetworkBuilder


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def belief_engine():
    return BeliefModelingEngine()


@pytest.fixture
def network_builder():
    return BeliefNetworkBuilder()


@pytest.fixture
def sample_evidence():
    return [
        {'identifier': 'ev-1', 'type': 'self_report', 'text': 'I believe in hard work.'},
        {'identifier': 'ev-2', 'type': 'self_report', 'text': 'I think that honesty matters.'},
        {'identifier': 'ev-3', 'type': 'behavioral_report', 'text': 'I always try my best.'},
        {'identifier': 'ev-4', 'type': 'observation', 'text': 'The world is competitive.'},
    ]


@pytest.fixture
def sample_narratives():
    return [
        {'identifier': 'narr-1', 'text': 'I believe that knowledge is power.'},
        {'identifier': 'narr-2', 'text': 'I know that relationships matter.'},
    ]


@pytest.fixture
def sample_belief():
    return BeliefObject(
        identifier='belief-1',
        belief_statement='I believe in hard work',
        category='competence',
        confidence=0.8,
        strength=0.7,
        stability=0.6,
        influence=0.9,
    )


# ---------------------------------------------------------------------------
# BeliefObject tests
# ---------------------------------------------------------------------------


class TestBeliefObject:
    def test_creation(self):
        b = BeliefObject(
            identifier='b1',
            belief_statement='I believe in learning',
            category='learning',
        )
        assert b.identifier == 'b1'
        assert b.belief_statement == 'I believe in learning'
        assert b.category == 'learning'

    def test_defaults(self):
        b = BeliefObject(identifier='b2', belief_statement='test', category='self')
        assert b.confidence == 0.0
        assert b.strength == 0.0
        assert b.stability == 0.0
        assert b.influence == 0.0
        assert b.lifecycle_state == 'candidate'
        assert b.specification_version == '1.0.0'

    def test_frozen(self):
        b = BeliefObject(identifier='b3', belief_statement='test', category='self')
        with pytest.raises(AttributeError):
            b.confidence = 0.5  # type: ignore[misc]

    def test_evidence_tuples(self):
        b = BeliefObject(
            identifier='b4',
            belief_statement='test',
            category='self',
            supporting_evidence=('ev-1', 'ev-2'),
            contradictory_evidence=('ev-3',),
        )
        assert len(b.supporting_evidence) == 2
        assert len(b.contradictory_evidence) == 1

    def test_cross_module_associations(self):
        b = BeliefObject(
            identifier='b5',
            belief_statement='test',
            category='self',
            associated_values=('v1',),
            associated_goals=('g1',),
            associated_identity_components=('id1',),
        )
        assert 'v1' in b.associated_values
        assert 'g1' in b.associated_goals

    def test_categories_contain_expected_values(self):
        assert 'self' in BELIEF_CATEGORIES
        assert 'competence' in BELIEF_CATEGORIES
        assert 'spiritual' in BELIEF_CATEGORIES
        assert len(BELIEF_CATEGORIES) == 17

    def test_relationship_types(self):
        assert 'supports' in BELIEF_RELATIONSHIP_TYPES
        assert 'conflicts_with' in BELIEF_RELATIONSHIP_TYPES
        assert 'depends_on' in BELIEF_RELATIONSHIP_TYPES
        assert 'hierarchy' in BELIEF_RELATIONSHIP_TYPES


# ---------------------------------------------------------------------------
# BeliefModelingEngine tests
# ---------------------------------------------------------------------------


class TestBeliefModelingEngine:
    def test_process_returns_result(self, belief_engine, sample_evidence):
        result = belief_engine.process(sample_evidence)
        assert isinstance(result, BeliefModelingResult)

    def test_extracts_beliefs(self, belief_engine, sample_evidence):
        result = belief_engine.process(sample_evidence)
        assert result.total_extracted > 0

    def test_beliefs_have_identifiers(self, belief_engine, sample_evidence):
        result = belief_engine.process(sample_evidence)
        for b in result.beliefs:
            assert b.identifier
            assert isinstance(b.identifier, str)

    def test_beliefs_have_valid_categories(self, belief_engine, sample_evidence):
        result = belief_engine.process(sample_evidence)
        for b in result.beliefs:
            assert b.category in BELIEF_CATEGORIES

    def test_beliefs_are_provisional(self, belief_engine, sample_evidence):
        result = belief_engine.process(sample_evidence)
        for b in result.beliefs:
            assert b.lifecycle_state == 'provisional'

    def test_metrics_computed(self, belief_engine, sample_evidence):
        result = belief_engine.process(sample_evidence)
        for b in result.beliefs:
            assert 0.0 <= b.confidence <= 1.0
            assert 0.0 <= b.strength <= 1.0
            assert 0.0 <= b.stability <= 1.0
            assert 0.0 <= b.influence <= 1.0

    def test_network_built(self, belief_engine, sample_evidence):
        result = belief_engine.process(sample_evidence)
        assert isinstance(result.network, BeliefNetwork)
        assert len(result.network.nodes) > 0

    def test_by_category(self, belief_engine, sample_evidence):
        result = belief_engine.process(sample_evidence)
        assert isinstance(result.by_category, dict)
        total = sum(result.by_category.values())
        assert total == result.total_extracted

    def test_with_narratives(self, belief_engine, sample_evidence, sample_narratives):
        result = belief_engine.process(sample_evidence, narratives=sample_narratives)
        assert result.total_extracted > 0

    def test_empty_evidence(self, belief_engine):
        result = belief_engine.process([])
        assert result.total_extracted == 0
        assert len(result.beliefs) == 0

    def test_determinism(self, belief_engine, sample_evidence):
        """Same input → same output."""
        r1 = belief_engine.process(sample_evidence)
        r2 = belief_engine.process(sample_evidence)
        assert r1.total_extracted == r2.total_extracted
        for b1, b2 in zip(r1.beliefs, r2.beliefs):
            assert b1.belief_statement == b2.belief_statement
            assert b1.category == b2.category

    def test_no_belief_keywords_filtered(self, belief_engine):
        evidence = [
            {'identifier': 'ev-1', 'type': 'observation', 'text': 'The weather is nice today.'},
        ]
        result = belief_engine.process(evidence)
        assert result.total_extracted == 0

    def test_belief_keywords_detected(self, belief_engine):
        evidence = [
            {'identifier': 'ev-1', 'type': 'self_report', 'text': 'I believe in hard work.'},
        ]
        result = belief_engine.process(evidence)
        assert result.total_extracted > 0


# ---------------------------------------------------------------------------
# BeliefNetworkBuilder tests
# ---------------------------------------------------------------------------


class TestBeliefNetworkBuilder:
    def test_add_belief(self, network_builder, sample_belief):
        network_builder.add_belief(sample_belief)
        assert network_builder.node_count == 1

    def test_connect(self, network_builder):
        b1 = BeliefObject(identifier='b1', belief_statement='s1', category='self')
        b2 = BeliefObject(identifier='b2', belief_statement='s2', category='self')
        network_builder.add_belief(b1)
        network_builder.add_belief(b2)
        network_builder.connect('b1', 'b2', 'supports')
        assert network_builder.edge_count == 1

    def test_connect_unknown_relationship(self, network_builder):
        b1 = BeliefObject(identifier='b1', belief_statement='s1', category='self')
        network_builder.add_belief(b1)
        with pytest.raises(ValueError, match='Unknown relationship'):
            network_builder.connect('b1', 'b1', 'invalid_type')

    def test_connect_missing_source(self, network_builder):
        b1 = BeliefObject(identifier='b1', belief_statement='s1', category='self')
        network_builder.add_belief(b1)
        with pytest.raises(ValueError, match='Source belief not found'):
            network_builder.connect('missing', 'b1', 'supports')

    def test_connect_missing_target(self, network_builder):
        b1 = BeliefObject(identifier='b1', belief_statement='s1', category='self')
        network_builder.add_belief(b1)
        with pytest.raises(ValueError, match='Target belief not found'):
            network_builder.connect('b1', 'missing', 'supports')

    def test_find_conflicts(self, network_builder):
        b1 = BeliefObject(identifier='b1', belief_statement='s1', category='self')
        b2 = BeliefObject(identifier='b2', belief_statement='s2', category='self')
        network_builder.add_belief(b1)
        network_builder.add_belief(b2)
        network_builder.connect('b1', 'b2', 'conflicts_with')
        conflicts = network_builder.find_conflicts('b1')
        assert len(conflicts) == 1

    def test_find_supporting(self, network_builder):
        b1 = BeliefObject(identifier='b1', belief_statement='s1', category='self')
        b2 = BeliefObject(identifier='b2', belief_statement='s2', category='self')
        network_builder.add_belief(b1)
        network_builder.add_belief(b2)
        network_builder.connect('b1', 'b2', 'supports')
        supporting = network_builder.find_supporting('b1')
        assert len(supporting) == 1

    def test_get_hierarchy(self, network_builder):
        b1 = BeliefObject(identifier='b1', belief_statement='world view', category='world')
        b2 = BeliefObject(identifier='b2', belief_statement='relationship view', category='relationship')
        network_builder.add_belief(b1)
        network_builder.add_belief(b2)
        network_builder.connect('b1', 'b2', 'hierarchy')
        hierarchy = network_builder.get_hierarchy()
        assert 'level_0' in hierarchy
        assert 'level_1' in hierarchy

    def test_build(self, network_builder, sample_belief):
        network_builder.add_belief(sample_belief)
        network = network_builder.build()
        assert isinstance(network, BeliefNetwork)
        assert len(network.nodes) == 1

    def test_empty_network(self, network_builder):
        network = network_builder.build()
        assert isinstance(network, BeliefNetwork)
        assert len(network.nodes) == 0
        assert len(network.edges) == 0
