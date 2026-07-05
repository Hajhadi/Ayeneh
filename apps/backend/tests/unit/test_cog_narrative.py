"""Tests for the COG-05 Narrative Extraction pipeline."""

from __future__ import annotations

import uuid
import pytest
from datetime import UTC, datetime
from typing import Any

from ayeneh.cog.narrative.types import (
    NARRATIVE_CATEGORIES,
    NARRATIVE_TEMPLATES,
    NARRATIVE_VALIDATION_STATUSES,
    NarrativeEdge,
    NarrativeExtractionResult,
    NarrativeNetwork,
    NarrativeObject,
)
from ayeneh.cog.narrative.extraction import NarrativeExtractionEngine
from ayeneh.cog.narrative.network import NarrativeNetworkBuilder
from ayeneh.cog.narrative.dynamics import (
    FusionResult,
    NarrativeDynamicsAnalyzer,
    NarrativeDrift,
    NarrativeGravity,
    RigidityResult,
)


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
def narrative_engine():
    return NarrativeExtractionEngine()


@pytest.fixture
def network_builder():
    return NarrativeNetworkBuilder()


@pytest.fixture
def dynamics_analyzer():
    return NarrativeDynamicsAnalyzer()


@pytest.fixture
def sample_narrative():
    return NarrativeObject(
        identifier='narr-test-001',
        narrative_type='growth',
        title='Growth Through Adversity',
        summary='I overcame challenges and became stronger.',
        supporting_evidence=('ev-1', 'ev-2', 'ev-3'),
        confidence=0.7,
        influence_score=0.6,
        template='growth',
        core_assumptions=('Adversity leads to growth.',),
        identity_implications=('I am resilient.',),
        emotional_associations=('pride', 'determination'),
        behavioral_consequences=('I seek challenges.',),
    )


@pytest.fixture
def sample_evidence_list():
    return [
        _make_evidence('ev-1', 'self_report', 'I always start my day with coffee and planning.'),
        _make_evidence('ev-2', 'identity_statement', 'I am someone who never gives up.'),
        _make_evidence('ev-3', 'self_report', 'I learned from my mistakes and grew stronger.'),
        _make_evidence('ev-4', 'preference', 'I love reading science fiction books.'),
        _make_evidence('ev-5', 'goal_statement', 'I want to build something meaningful.'),
        _make_evidence('ev-6', 'self_report', 'I failed my first exam but studied harder.'),
        _make_evidence('ev-7', 'self_report', 'My family always supported me through tough times.'),
        _make_evidence('ev-8', 'identity_statement', 'I am the kind of person who helps others.'),
    ]


# ---------------------------------------------------------------------------
# NarrativeObject type tests
# ---------------------------------------------------------------------------


class TestNarrativeObject:
    def test_creation(self):
        no = NarrativeObject(
            identifier='narr-1',
            narrative_type='career',
            title='Career Ambition',
            summary='I strive for excellence in my career.',
            confidence=0.8,
            influence_score=0.7,
        )
        assert no.identifier == 'narr-1'
        assert no.narrative_type == 'career'
        assert no.confidence == 0.8
        assert no.influence_score == 0.7

    def test_frozen(self, sample_narrative):
        with pytest.raises(AttributeError):
            sample_narrative.confidence = 0.9  # type: ignore[misc]

    def test_frozen_identifier(self, sample_narrative):
        with pytest.raises(AttributeError):
            sample_narrative.identifier = 'narr-new'  # type: ignore[misc]

    def test_defaults(self):
        no = NarrativeObject()
        assert no.identifier == ''
        assert no.narrative_type == 'self'
        assert no.title == ''
        assert no.summary == ''
        assert no.confidence == 0.0
        assert no.influence_score == 0.0
        assert no.template == ''
        assert no.lifecycle_state == 'candidate'
        assert no.specification_version == '1.0.0'

    def test_timestamp_auto(self):
        no = NarrativeObject()
        assert isinstance(no.creation_timestamp, datetime)
        assert no.creation_timestamp.tzinfo is not None

    def test_tuples_are_immutable(self, sample_narrative):
        assert isinstance(sample_narrative.supporting_evidence, tuple)
        assert isinstance(sample_narrative.core_assumptions, tuple)

    def test_emotional_associations(self):
        no = NarrativeObject(
            emotional_associations=('fear', 'hope', 'determination'),
        )
        assert len(no.emotional_associations) == 3

    def test_related_narratives(self):
        no = NarrativeObject(
            related_narratives=('narr-1', 'narr-2'),
        )
        assert no.related_narratives == ('narr-1', 'narr-2')


# ---------------------------------------------------------------------------
# NarrativeEdge / NarrativeNetwork type tests
# ---------------------------------------------------------------------------


class TestNarrativeEdge:
    def test_creation(self):
        edge = NarrativeEdge(
            source_id='narr-1',
            target_id='narr-2',
            relationship='supports',
            confidence=0.8,
        )
        assert edge.source_id == 'narr-1'
        assert edge.relationship == 'supports'

    def test_frozen(self):
        edge = NarrativeEdge(source_id='a', target_id='b', relationship='r')
        with pytest.raises(AttributeError):
            edge.confidence = 0.9  # type: ignore[misc]

    def test_defaults(self):
        edge = NarrativeEdge()
        assert edge.source_id == ''
        assert edge.confidence == 0.5


class TestNarrativeNetwork:
    def test_creation(self):
        net = NarrativeNetwork()
        assert net.nodes == {}
        assert net.edges == ()

    def test_frozen(self):
        net = NarrativeNetwork()
        with pytest.raises(AttributeError):
            net.nodes = {}  # type: ignore[misc]


# ---------------------------------------------------------------------------
# NarrativeExtractionResult tests
# ---------------------------------------------------------------------------


class TestNarrativeExtractionResult:
    def test_creation(self):
        result = NarrativeExtractionResult()
        assert result.narratives == ()
        assert result.total_extracted == 0
        assert result.by_category == {}

    def test_frozen(self):
        result = NarrativeExtractionResult()
        with pytest.raises(AttributeError):
            result.total_extracted = 5  # type: ignore[misc]

    def test_timestamp_auto(self):
        result = NarrativeExtractionResult()
        assert isinstance(result.processing_timestamp, datetime)


# ---------------------------------------------------------------------------
# NarrativeExtractionEngine tests
# ---------------------------------------------------------------------------


class TestNarrativeExtractionEngine:
    def test_process_returns_result(self, narrative_engine, sample_evidence_list):
        result = narrative_engine.process(sample_evidence_list)
        assert isinstance(result, NarrativeExtractionResult)

    def test_extracts_narratives(self, narrative_engine, sample_evidence_list):
        result = narrative_engine.process(sample_evidence_list)
        assert result.total_extracted > 0

    def test_all_have_identifiers(self, narrative_engine, sample_evidence_list):
        result = narrative_engine.process(sample_evidence_list)
        for no in result.narratives:
            assert no.identifier
            assert isinstance(no.identifier, str)

    def test_all_have_categories(self, narrative_engine, sample_evidence_list):
        result = narrative_engine.process(sample_evidence_list)
        for no in result.narratives:
            assert no.narrative_type in NARRATIVE_CATEGORIES

    def test_by_category_counts(self, narrative_engine, sample_evidence_list):
        result = narrative_engine.process(sample_evidence_list)
        assert isinstance(result.by_category, dict)
        total_from_counts = sum(result.by_category.values())
        assert total_from_counts == result.total_extracted

    def test_network_built(self, narrative_engine, sample_evidence_list):
        result = narrative_engine.process(sample_evidence_list)
        assert isinstance(result.network, NarrativeNetwork)

    def test_empty_input(self, narrative_engine):
        result = narrative_engine.process([])
        assert result.total_extracted == 0
        assert len(result.narratives) == 0

    def test_determinism(self, narrative_engine, sample_evidence_list):
        """Same input → same output (deterministic pipeline)."""
        r1 = narrative_engine.process(sample_evidence_list)
        r2 = narrative_engine.process(sample_evidence_list)
        assert r1.total_extracted == r2.total_extracted
        assert len(r1.narratives) == len(r2.narratives)
        for n1, n2 in zip(r1.narratives, r2.narratives):
            assert n1.narrative_type == n2.narrative_type
            assert n1.title == n2.title
            assert n1.lifecycle_state == n2.lifecycle_state

    def test_template_detection_growth(self, narrative_engine):
        evidence = [
            _make_evidence('ev-1', 'self_report', 'I learned from my mistakes and grew.'),
            _make_evidence('ev-2', 'self_report', 'I overcame the challenge and became stronger.'),
            _make_evidence('ev-3', 'self_report', 'I developed resilience through adversity.'),
        ]
        result = narrative_engine.process(evidence)
        templates = [no.template for no in result.narratives]
        assert 'growth' in templates

    def test_template_detection_failure(self, narrative_engine):
        evidence = [
            _make_evidence('ev-1', 'self_report', 'I failed the exam and lost my confidence.'),
            _make_evidence('ev-2', 'self_report', 'I could not succeed and felt like a failure.'),
            _make_evidence('ev-3', 'self_report', 'I always fail at these things.'),
        ]
        result = narrative_engine.process(evidence)
        templates = [no.template for no in result.narratives]
        assert 'failure' in templates

    def test_influence_scores_assigned(self, narrative_engine, sample_evidence_list):
        result = narrative_engine.process(sample_evidence_list)
        for no in result.narratives:
            assert 0.0 <= no.influence_score <= 1.0

    def test_confidence_in_range(self, narrative_engine, sample_evidence_list):
        result = narrative_engine.process(sample_evidence_list)
        for no in result.narratives:
            assert 0.0 <= no.confidence <= 1.0

    def test_lifecycle_state_progression(self, narrative_engine):
        """Multiple evidence should progress lifecycle state beyond candidate."""
        evidence = [
            _make_evidence('ev-1', 'self_report', 'I always help my friends in need.'),
            _make_evidence('ev-2', 'self_report', 'I helped a friend move last week.'),
            _make_evidence('ev-3', 'self_report', 'I took care of my neighbor when she was sick.'),
        ]
        result = narrative_engine.process(evidence)
        states = [no.lifecycle_state for no in result.narratives]
        # At least one should have progressed beyond candidate
        assert any(s != 'candidate' for s in states)

    def test_process_with_knowledge_objects(self, narrative_engine, sample_evidence_list):
        """Process should accept optional knowledge objects."""
        result = narrative_engine.process(sample_evidence_list, knowledge_objects=[])
        assert isinstance(result, NarrativeExtractionResult)

    def test_result_timestamp(self, narrative_engine, sample_evidence_list):
        result = narrative_engine.process(sample_evidence_list)
        assert isinstance(result.processing_timestamp, datetime)

    def test_default_ai_router_is_none(self):
        """Engine works without ai_router (default None)."""
        engine = NarrativeExtractionEngine()
        assert engine._ai_router is None
        evidence = [_make_evidence(f'ev-{i}', 'self_report', f'Text {i}') for i in range(3)]
        result = engine.process(evidence)
        assert isinstance(result, NarrativeExtractionResult)

    def test_with_ai_router_parameter(self):
        """Engine accepts ai_router parameter."""
        mock_router = object()
        engine = NarrativeExtractionEngine(ai_router=mock_router)
        assert engine._ai_router is mock_router

    def test_llm_fallback_on_running_loop(self):
        """When event loop is running, LLM path returns None and falls back to rule-based."""
        import asyncio

        async def _run():
            engine = NarrativeExtractionEngine(ai_router=object())
            evidence = [_make_evidence(f'ev-{i}', 'self_report', f'Text {i}') for i in range(6)]
            result = engine.process(evidence)
            assert isinstance(result, NarrativeExtractionResult)
            return result

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# NarrativeNetworkBuilder tests
# ---------------------------------------------------------------------------


class TestNarrativeNetworkBuilder:
    def test_add_narrative(self, network_builder, sample_narrative):
        network_builder.add_narrative(sample_narrative)
        assert network_builder.node_count() == 1

    def test_add_replaces(self, network_builder, sample_narrative):
        network_builder.add_narrative(sample_narrative)
        updated = NarrativeObject(
            identifier='narr-test-001',
            narrative_type='growth',
            title='Updated Title',
            summary='Updated.',
        )
        network_builder.add_narrative(updated)
        assert network_builder.node_count() == 1
        node = network_builder.get_narrative('narr-test-001')
        assert node is not None
        assert node.title == 'Updated Title'

    def test_get_narrative(self, network_builder, sample_narrative):
        network_builder.add_narrative(sample_narrative)
        retrieved = network_builder.get_narrative('narr-test-001')
        assert retrieved is not None
        assert retrieved.identifier == 'narr-test-001'

    def test_get_narrative_nonexistent(self, network_builder):
        assert network_builder.get_narrative('nonexistent') is None

    def test_connect(self, network_builder):
        n1 = NarrativeObject(identifier='narr-1', title='A')
        n2 = NarrativeObject(identifier='narr-2', title='B')
        network_builder.add_narrative(n1)
        network_builder.add_narrative(n2)
        network_builder.connect('narr-1', 'narr-2', 'supports', 0.8)
        assert network_builder.edge_count() == 1

    def test_connect_nonexistent_source(self, network_builder):
        n = NarrativeObject(identifier='narr-1', title='A')
        network_builder.add_narrative(n)
        with pytest.raises(ValueError, match='Source'):
            network_builder.connect('nonexistent', 'narr-1', 'supports')

    def test_connect_nonexistent_target(self, network_builder):
        n = NarrativeObject(identifier='narr-1', title='A')
        network_builder.add_narrative(n)
        with pytest.raises(ValueError, match='Target'):
            network_builder.connect('narr-1', 'nonexistent', 'supports')

    def test_find_dominant(self, network_builder):
        n1 = NarrativeObject(
            identifier='narr-1', title='Dominant',
            influence_score=0.8, confidence=0.7,
        )
        n2 = NarrativeObject(
            identifier='narr-2', title='Weak',
            influence_score=0.1, confidence=0.1,
        )
        network_builder.add_narrative(n1)
        network_builder.add_narrative(n2)
        dominant = network_builder.find_dominant()
        assert len(dominant) == 1
        assert dominant[0].identifier == 'narr-1'

    def test_find_dominant_sorted(self, network_builder):
        n1 = NarrativeObject(
            identifier='narr-1', title='A',
            influence_score=0.6, confidence=0.5,
        )
        n2 = NarrativeObject(
            identifier='narr-2', title='B',
            influence_score=0.9, confidence=0.9,
        )
        network_builder.add_narrative(n1)
        network_builder.add_narrative(n2)
        dominant = network_builder.find_dominant()
        assert dominant[0].identifier == 'narr-2'

    def test_find_latent(self, network_builder):
        n1 = NarrativeObject(
            identifier='narr-1', title='Latent',
            supporting_evidence=('ev-1',),
            lifecycle_state='candidate',
        )
        n2 = NarrativeObject(
            identifier='narr-2', title='Active',
            supporting_evidence=('ev-1', 'ev-2', 'ev-3'),
            lifecycle_state='validated',
        )
        n3 = NarrativeObject(
            identifier='narr-3', title='Archived',
            supporting_evidence=('ev-1',),
            lifecycle_state='archived',
        )
        network_builder.add_narrative(n1)
        network_builder.add_narrative(n2)
        network_builder.add_narrative(n3)
        latent = network_builder.find_latent()
        assert len(latent) == 1
        assert latent[0].identifier == 'narr-1'

    def test_get_supporting(self, network_builder):
        n1 = NarrativeObject(identifier='narr-1', title='A')
        n2 = NarrativeObject(identifier='narr-2', title='B')
        n3 = NarrativeObject(identifier='narr-3', title='C')
        network_builder.add_narrative(n1)
        network_builder.add_narrative(n2)
        network_builder.add_narrative(n3)
        network_builder.connect('narr-2', 'narr-1', 'supports')
        network_builder.connect('narr-3', 'narr-1', 'contradicts')

        supporting = network_builder.get_supporting('narr-1')
        assert len(supporting) == 1
        assert supporting[0].identifier == 'narr-2'

    def test_get_conflicting(self, network_builder):
        n1 = NarrativeObject(identifier='narr-1', title='A')
        n2 = NarrativeObject(identifier='narr-2', title='B')
        n3 = NarrativeObject(identifier='narr-3', title='C')
        network_builder.add_narrative(n1)
        network_builder.add_narrative(n2)
        network_builder.add_narrative(n3)
        network_builder.connect('narr-2', 'narr-1', 'supports')
        network_builder.connect('narr-3', 'narr-1', 'contradicts')

        conflicting = network_builder.get_conflicting('narr-1')
        assert len(conflicting) == 1
        assert conflicting[0].identifier == 'narr-3'

    def test_get_by_type(self, network_builder):
        n1 = NarrativeObject(identifier='narr-1', narrative_type='growth', title='A')
        n2 = NarrativeObject(identifier='narr-2', narrative_type='career', title='B')
        n3 = NarrativeObject(identifier='narr-3', narrative_type='growth', title='C')
        network_builder.add_narrative(n1)
        network_builder.add_narrative(n2)
        network_builder.add_narrative(n3)

        growth = network_builder.get_by_type('growth')
        assert len(growth) == 2

    def test_get_by_template(self, network_builder):
        n1 = NarrativeObject(identifier='narr-1', template='hero', title='A')
        n2 = NarrativeObject(identifier='narr-2', template='victim', title='B')
        n3 = NarrativeObject(identifier='narr-3', template='hero', title='C')
        network_builder.add_narrative(n1)
        network_builder.add_narrative(n2)
        network_builder.add_narrative(n3)

        heroes = network_builder.get_by_template('hero')
        assert len(heroes) == 2

    def test_remove_narrative(self, network_builder):
        n1 = NarrativeObject(identifier='narr-1', title='A')
        n2 = NarrativeObject(identifier='narr-2', title='B')
        network_builder.add_narrative(n1)
        network_builder.add_narrative(n2)
        network_builder.connect('narr-1', 'narr-2', 'supports')

        assert network_builder.remove_narrative('narr-1') is True
        assert network_builder.node_count() == 1
        assert network_builder.edge_count() == 0

    def test_remove_nonexistent(self, network_builder):
        assert network_builder.remove_narrative('nonexistent') is False

    def test_empty_network(self, network_builder):
        assert network_builder.node_count() == 0
        assert network_builder.edge_count() == 0
        assert network_builder.all_narratives() == []
        assert network_builder.all_edges() == []


# ---------------------------------------------------------------------------
# NarrativeDynamicsAnalyzer tests
# ---------------------------------------------------------------------------


class TestNarrativeDynamicsAnalyzer:
    def test_analyze_drift(self, dynamics_analyzer, sample_narrative):
        evidence = [_make_evidence(f'ev-{i}', 'self_report', f'Text {i}') for i in range(5)]
        drift = dynamics_analyzer.analyze_drift(sample_narrative, evidence)
        assert isinstance(drift, NarrativeDrift)
        assert drift.narrative_id == 'narr-test-001'
        assert 0.0 <= drift.overall_drift <= 1.0
        assert 0.0 <= drift.evidence_mismatch_score <= 1.0
        assert 0.0 <= drift.behavior_mismatch_score <= 1.0
        assert 0.0 <= drift.contradiction_accumulation <= 1.0

    def test_analyze_drift_no_contradictions(self, dynamics_analyzer):
        no = NarrativeObject(
            identifier='narr-clean',
            supporting_evidence=('ev-1', 'ev-2'),
            contradictory_evidence=(),
        )
        drift = dynamics_analyzer.analyze_drift(no, [])
        assert drift.overall_drift == 0.0

    def test_analyze_drift_high_contradictions(self, dynamics_analyzer):
        no = NarrativeObject(
            identifier='narr-drift',
            supporting_evidence=('ev-1',),
            contradictory_evidence=('ev-2', 'ev-3', 'ev-4'),
        )
        drift = dynamics_analyzer.analyze_drift(no, [])
        assert drift.overall_drift > 0.3

    def test_analyze_gravity(self, dynamics_analyzer, sample_narrative):
        evidence = [_make_evidence(f'ev-{i}', 'self_report', f'Text {i}') for i in range(5)]
        gravity = dynamics_analyzer.analyze_gravity(sample_narrative, evidence)
        assert isinstance(gravity, NarrativeGravity)
        assert gravity.narrative_id == 'narr-test-001'
        assert 0.0 <= gravity.overall_gravity <= 1.0
        assert 0.0 <= gravity.repetition_strength <= 1.0
        assert 0.0 <= gravity.emotional_intensity <= 1.0
        assert 0.0 <= gravity.identity_coupling <= 1.0
        assert 0.0 <= gravity.behavioral_influence <= 1.0

    def test_analyze_gravity_empty_narrative(self, dynamics_analyzer):
        no = NarrativeObject(identifier='narr-empty')
        gravity = dynamics_analyzer.analyze_gravity(no, [])
        assert gravity.overall_gravity == 0.0

    def test_analyze_gravity_high_emotional(self, dynamics_analyzer):
        no = NarrativeObject(
            identifier='narr-emotional',
            supporting_evidence=('ev-1', 'ev-2'),
            emotional_associations=('fear', 'anger', 'sadness', 'hope', 'despair'),
            identity_implications=('I am broken.', 'This defines me.'),
            behavioral_consequences=('I avoid people.', 'I overwork.'),
        )
        gravity = dynamics_analyzer.analyze_gravity(no, [_make_evidence(f'ev-{i}') for i in range(5)])
        assert gravity.emotional_intensity == 1.0
        assert gravity.identity_coupling == 0.5

    def test_detect_fusion(self, dynamics_analyzer, sample_narrative):
        identity_components = [
            type('Comp', (), {'statement': 'I am resilient.'})(),
            type('Comp', (), {'statement': 'I am strong.'})(),
        ]
        fusion = dynamics_analyzer.detect_fusion(sample_narrative, identity_components)
        assert isinstance(fusion, float)
        assert 0.0 <= fusion <= 1.0
        assert fusion > 0.0

    def test_detect_fusion_no_identity_implications(self, dynamics_analyzer):
        no = NarrativeObject(identifier='narr-no-impl')
        fusion = dynamics_analyzer.detect_fusion(no, [])
        assert fusion == 0.0

    def test_detect_fusion_no_components(self, dynamics_analyzer, sample_narrative):
        fusion = dynamics_analyzer.detect_fusion(sample_narrative, [])
        assert fusion == 0.0

    def test_detect_rigidity(self, dynamics_analyzer, sample_narrative):
        rigidity = dynamics_analyzer.detect_rigidity(sample_narrative, [])
        assert isinstance(rigidity, float)
        assert 0.0 <= rigidity <= 1.0

    def test_detect_rigidity_with_revisions(self, dynamics_analyzer):
        no = NarrativeObject(
            identifier='narr-revised',
            confidence=0.5,
            supporting_evidence=('ev-1', 'ev-2'),
            contradictory_evidence=(),
        )
        revisions = [{'revision': 1}, {'revision': 2}, {'revision': 3}]
        rigidity = dynamics_analyzer.detect_rigidity(no, revisions)
        # More revisions → less rigid
        assert rigidity < 0.8

    def test_detect_rigidity_high_confidence_no_revisions(self, dynamics_analyzer):
        no = NarrativeObject(
            identifier='narr-rigid',
            confidence=0.95,
            supporting_evidence=('ev-1', 'ev-2', 'ev-3'),
            contradictory_evidence=('ev-4',),
        )
        rigidity = dynamics_analyzer.detect_rigidity(no, [])
        # High confidence + no revisions + contradictions = rigid
        assert rigidity > 0.5


# ---------------------------------------------------------------------------
# Narrative categories and templates tests
# ---------------------------------------------------------------------------


class TestNarrativeCategoriesAndTemplates:
    def test_categories_list(self):
        assert 'self' in NARRATIVE_CATEGORIES
        assert 'identity' in NARRATIVE_CATEGORIES
        assert 'growth' in NARRATIVE_CATEGORIES
        assert 'career' in NARRATIVE_CATEGORIES
        assert 'purpose' in NARRATIVE_CATEGORIES
        assert len(NARRATIVE_CATEGORIES) > 15

    def test_templates_list(self):
        assert 'success' in NARRATIVE_TEMPLATES
        assert 'failure' in NARRATIVE_TEMPLATES
        assert 'growth' in NARRATIVE_TEMPLATES
        assert 'hero' in NARRATIVE_TEMPLATES
        assert 'victim' in NARRATIVE_TEMPLATES
        assert len(NARRATIVE_TEMPLATES) > 10

    def test_validation_statuses(self):
        assert 'candidate' in NARRATIVE_VALIDATION_STATUSES
        assert 'provisional' in NARRATIVE_VALIDATION_STATUSES
        assert 'validated' in NARRATIVE_VALIDATION_STATUSES
        assert 'dormant' in NARRATIVE_VALIDATION_STATUSES
        assert 'archived' in NARRATIVE_VALIDATION_STATUSES


# ---------------------------------------------------------------------------
# Dominant vs latent narrative detection tests
# ---------------------------------------------------------------------------


class TestDominantVsLatent:
    def test_dominant_threshold(self, network_builder):
        """Dominant narratives must meet influence and confidence thresholds."""
        n1 = NarrativeObject(
            identifier='narr-1', title='Strong',
            influence_score=0.5, confidence=0.5,
        )
        n2 = NarrativeObject(
            identifier='narr-2', title='Weak Influence',
            influence_score=0.1, confidence=0.8,
        )
        n3 = NarrativeObject(
            identifier='narr-3', title='Weak Confidence',
            influence_score=0.8, confidence=0.1,
        )
        network_builder.add_narrative(n1)
        network_builder.add_narrative(n2)
        network_builder.add_narrative(n3)

        dominant = network_builder.find_dominant()
        assert len(dominant) == 1
        assert dominant[0].identifier == 'narr-1'

    def test_latent_excludes_archived(self, network_builder):
        """Latent narratives should exclude archived ones."""
        n1 = NarrativeObject(
            identifier='narr-1', title='Archived',
            supporting_evidence=('ev-1',),
            lifecycle_state='archived',
        )
        n2 = NarrativeObject(
            identifier='narr-2', title='Contradicted',
            supporting_evidence=('ev-1',),
            lifecycle_state='contradicted',
        )
        network_builder.add_narrative(n1)
        network_builder.add_narrative(n2)

        latent = network_builder.find_latent()
        assert len(latent) == 0
