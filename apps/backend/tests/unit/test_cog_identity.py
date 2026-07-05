"""Tests for the COG-09 Identity Graph Engine."""

from __future__ import annotations

import pytest

from ayeneh.cog.identity.coherence import IdentityCoherenceEstimator
from ayeneh.cog.identity.graph import IdentityGraphEngine
from ayeneh.cog.identity.types import (
    IDENTITY_COMPONENT_TYPES,
    IDENTITY_LIFECYCLE_STATES,
    IdentityComponent,
    IdentityGraph,
    IdentityResult,
    ObserverSelf,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return IdentityGraphEngine()


@pytest.fixture
def coherence_estimator():
    return IdentityCoherenceEstimator()


@pytest.fixture
def sample_evidence():
    return [
        {'id': 'ev-1', 'text': 'I am a very analytical person', 'category': 'identity_statement'},
        {'id': 'ev-2', 'text': 'I always start my day with meditation', 'category': 'self_report'},
        {'id': 'ev-3', 'text': 'I value honesty above all else', 'category': 'identity_statement'},
        {'id': 'ev-4', 'text': 'I decided to take the new job', 'category': 'decision_report'},
        {'id': 'ev-5', 'text': 'I believe in continuous learning', 'category': 'self_report'},
    ]


@pytest.fixture
def sample_component():
    return IdentityComponent(
        identifier='comp-1',
        identity_statement='I am analytical',
        confidence=0.8,
        stability=0.7,
        centrality=0.6,
        influence=0.5,
        supporting_evidence=('ev-1',),
        supporting_beliefs=('belief-1',),
        supporting_values=('value-1',),
        supporting_goals=('goal-1',),
        supporting_narratives=('narr-1',),
        lifecycle_state='validated',
    )


# ---------------------------------------------------------------------------
# IdentityComponent tests
# ---------------------------------------------------------------------------


class TestIdentityComponent:
    def test_creation(self, sample_component):
        assert sample_component.identifier == 'comp-1'
        assert sample_component.identity_statement == 'I am analytical'
        assert sample_component.confidence == 0.8

    def test_defaults(self):
        comp = IdentityComponent(identifier='c1', identity_statement='test')
        assert comp.confidence == 0.0
        assert comp.stability == 0.0
        assert comp.centrality == 0.0
        assert comp.influence == 0.0
        assert comp.observer_strength == 0.0
        assert comp.supporting_evidence == ()
        assert comp.lifecycle_state == 'candidate'
        assert comp.specification_version == '1.0.0'

    def test_frozen(self, sample_component):
        with pytest.raises(AttributeError):
            sample_component.confidence = 0.5  # type: ignore[misc]

    def test_frozen_identity_statement(self, sample_component):
        with pytest.raises(AttributeError):
            sample_component.identity_statement = 'other'  # type: ignore[misc]

    def test_revision_history_tuple(self):
        comp = IdentityComponent(
            identifier='c1',
            identity_statement='test',
            revision_history=({'change': 'initial'},),
        )
        assert len(comp.revision_history) == 1
        assert comp.revision_history[0]['change'] == 'initial'


# ---------------------------------------------------------------------------
# ObserverSelf tests
# ---------------------------------------------------------------------------


class TestObserverSelf:
    def test_defaults(self):
        obs = ObserverSelf()
        assert obs.confidence == 0.0
        assert obs.stability == 0.0
        assert obs.observation_episodes == 0
        assert obs.average_episode_duration_s == 0.0
        assert obs.de_identification_level == 0.0

    def test_creation(self):
        obs = ObserverSelf(
            confidence=0.7,
            stability=0.6,
            observation_episodes=10,
            average_episode_duration_s=45.0,
            de_identification_level=0.4,
        )
        assert obs.confidence == 0.7
        assert obs.observation_episodes == 10

    def test_frozen(self):
        obs = ObserverSelf(confidence=0.5)
        with pytest.raises(AttributeError):
            obs.confidence = 0.8  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IdentityGraph tests
# ---------------------------------------------------------------------------


class TestIdentityGraph:
    def test_defaults(self):
        graph = IdentityGraph()
        assert graph.components == {}
        assert graph.edges == ()
        assert graph.coherence_score == 0.0

    def test_with_components(self, sample_component):
        graph = IdentityGraph(
            components={'comp-1': sample_component},
            edges=({'source': 'a', 'target': 'b', 'type': 'support'},),
        )
        assert len(graph.components) == 1
        assert len(graph.edges) == 1

    def test_frozen(self):
        graph = IdentityGraph()
        with pytest.raises(AttributeError):
            graph.components = {}  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IdentityGraphEngine tests
# ---------------------------------------------------------------------------


class TestIdentityGraphEngine:
    def test_process_returns_result(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert isinstance(result, IdentityResult)

    def test_components_extracted(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert result.total_components > 0

    def test_all_components_have_identifiers(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        for comp in result.components.values():
            assert comp.identifier
            assert isinstance(comp.identifier, str)

    def test_components_have_evidence(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        for comp in result.components.values():
            assert len(comp.supporting_evidence) > 0

    def test_confidence_in_range(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        for comp in result.components.values():
            assert 0.0 <= comp.confidence <= 1.0

    def test_coherence_in_range(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert 0.0 <= result.coherence_score <= 1.0

    def test_graph_has_components(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert len(result.graph.components) == result.total_components

    def test_determinism(self, engine, sample_evidence):
        """Same input → same output (deterministic pipeline)."""
        r1 = engine.process(sample_evidence)
        r2 = engine.process(sample_evidence)
        assert r1.total_components == r2.total_components
        assert r1.coherence_score == r2.coherence_score

    def test_empty_evidence(self, engine):
        result = engine.process([])
        assert result.total_components == 0
        assert result.coherence_score == 0.0

    def test_with_beliefs_values_goals(self, engine, sample_evidence):
        result = engine.process(
            sample_evidence,
            beliefs=['belief-1', 'belief-2'],
            values=['value-1'],
            goals=['goal-1'],
            narratives=['narr-1'],
        )
        assert result.total_components > 0
        assert 0.0 <= result.coherence_score <= 1.0

    def test_lifecycle_summary(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert isinstance(result.lifecycle_summary, dict)
        total = sum(result.lifecycle_summary.values())
        assert total == result.total_components

    def test_observer_updated(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert isinstance(result.observer_self, ObserverSelf)
        assert result.observer_self.observation_episodes >= 0


# ---------------------------------------------------------------------------
# IdentityCoherenceEstimator tests
# ---------------------------------------------------------------------------


class TestIdentityCoherenceEstimator:
    def test_empty_components(self, coherence_estimator):
        score = coherence_estimator.estimate({})
        assert score == 0.0

    def test_with_components(self, coherence_estimator, sample_component):
        components = {'comp-1': sample_component}
        score = coherence_estimator.estimate(
            components,
            beliefs=['belief-1'],
            values=['value-1'],
            goals=['goal-1'],
        )
        assert 0.0 <= score <= 1.0

    def test_high_coherence(self, coherence_estimator):
        """Components with full cross-references should have high coherence."""
        comp = IdentityComponent(
            identifier='c1',
            identity_statement='test',
            confidence=0.8,
            supporting_evidence=('ev-1',),
            supporting_beliefs=('b1',),
            supporting_values=('v1',),
            supporting_goals=('g1',),
            supporting_narratives=('n1',),
        )
        score = coherence_estimator.estimate(
            {'c1': comp},
            beliefs=['b1'],
            values=['v1'],
            goals=['g1'],
        )
        assert score > 0.3

    def test_low_coherence_no_evidence(self, coherence_estimator):
        comp = IdentityComponent(
            identifier='c1',
            identity_statement='test',
            supporting_evidence=(),
        )
        score = coherence_estimator.estimate({'c1': comp})
        assert score < 0.5

    def test_neutral_without_values(self, coherence_estimator):
        comp = IdentityComponent(
            identifier='c1',
            identity_statement='test',
            supporting_evidence=('ev-1',),
            supporting_beliefs=('b1',),
        )
        score = coherence_estimator.estimate({'c1': comp}, beliefs=['b1'])
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Catalogue tests
# ---------------------------------------------------------------------------


class TestCatalogues:
    def test_identity_lifecycle_states(self):
        assert 'candidate' in IDENTITY_LIFECYCLE_STATES
        assert 'canonical' in IDENTITY_LIFECYCLE_STATES
        assert len(IDENTITY_LIFECYCLE_STATES) > 4

    def test_identity_component_types(self):
        assert 'role' in IDENTITY_COMPONENT_TYPES
        assert 'trait' in IDENTITY_COMPONENT_TYPES
        assert len(IDENTITY_COMPONENT_TYPES) > 5
