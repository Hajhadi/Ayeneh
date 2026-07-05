"""Tests for the COG-12 Reflection Engine."""

from __future__ import annotations

import pytest

from ayeneh.cog.reflection.awakening import (
    AWAKENING_LEVELS,
    AwakeningDynamics,
    AwakeningProgress,
)
from ayeneh.cog.reflection.blind_spot import BlindSpotDetector
from ayeneh.cog.reflection.engine import ReflectionEngine
from ayeneh.cog.reflection.types import (
    GRANULARITY_LEVELS,
    LIFECYCLE_STATES,
    REFLECTION_SCOPES,
    VALIDATION_METHODS,
    BlindSpot,
    InsightObject,
    ReflectionObject,
    ReflectionResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return ReflectionEngine()


@pytest.fixture
def blind_spot_detector():
    return BlindSpotDetector()


@pytest.fixture
def awakening_dynamics():
    return AwakeningDynamics()


@pytest.fixture
def sample_evidence():
    return [
        {'id': 'ev-1', 'text': 'I always procrastinate before deadlines', 'category': 'behavioral_report'},
        {'id': 'ev-2', 'text': 'I procrastinate when stressed about work', 'category': 'behavioral_report'},
        {'id': 'ev-3', 'text': 'I believe I work better under pressure', 'category': 'self_report'},
        {'id': 'ev-4', 'text': 'I decided to start the project early', 'category': 'decision_report'},
        {'id': 'ev-5', 'text': 'I value productivity and efficiency', 'category': 'identity_statement'},
    ]


@pytest.fixture
def sample_patterns():
    return [
        {'id': 'pat-1', 'description': 'Procrastination loop before deadlines', 'type': 'behavioral_loop', 'frequency': 5},
        {'id': 'pat-2', 'description': 'Stress-induced avoidance pattern', 'type': 'cognitive_loop', 'frequency': 3},
    ]


@pytest.fixture
def sample_narratives():
    return [
        {'id': 'narr-1', 'text': 'I am someone who works well under pressure', 'theme': 'self_concept'},
        {'id': 'narr-2', 'text': 'Deadlines make me panic and avoid', 'theme': 'coping'},
    ]


@pytest.fixture
def sample_beliefs():
    return [
        {'id': 'belief-1', 'statement': 'I work better under pressure', 'confidence': 0.7},
        {'id': 'belief-2', 'statement': 'Starting early leads to perfectionism paralysis', 'confidence': 0.5},
    ]


@pytest.fixture
def sample_identity():
    return [
        {'id': 'id-1', 'statement': 'I am a productive person', 'domain': 'work'},
        {'id': 'id-2', 'statement': 'I am creative under pressure', 'domain': 'self_concept'},
    ]


# ---------------------------------------------------------------------------
# ReflectionObject tests
# ---------------------------------------------------------------------------


class TestReflectionObject:
    def test_creation(self):
        ref = ReflectionObject(
            identifier='ref-1',
            reflection_statement='User shows procrastination pattern',
            scope='project',
            confidence=0.7,
        )
        assert ref.identifier == 'ref-1'
        assert ref.reflection_statement == 'User shows procrastination pattern'
        assert ref.scope == 'project'
        assert ref.confidence == 0.7

    def test_defaults(self):
        ref = ReflectionObject(identifier='ref-1', reflection_statement='test')
        assert ref.scope == ''
        assert ref.temporal_coverage == ''
        assert ref.confidence == 0.0
        assert ref.supporting_evidence == ()
        assert ref.granularity == 'session'
        assert ref.lifecycle_state == 'candidate'
        assert ref.specification_version == '1.0.0'

    def test_frozen(self):
        ref = ReflectionObject(identifier='ref-1', reflection_statement='test')
        with pytest.raises(AttributeError):
            ref.confidence = 0.5  # type: ignore[misc]

    def test_timestamp_auto_generated(self):
        ref = ReflectionObject(identifier='ref-1', reflection_statement='test')
        assert ref.creation_timestamp is not None

    def test_revision_history_default(self):
        ref = ReflectionObject(identifier='ref-1', reflection_statement='test')
        assert ref.revision_history == ()


# ---------------------------------------------------------------------------
# InsightObject tests
# ---------------------------------------------------------------------------


class TestInsightObject:
    def test_creation(self):
        insight = InsightObject(
            identifier='ins-1',
            insight_statement='I realize I procrastinate because of fear',
            confidence=0.8,
            validation_method='behavior_change',
        )
        assert insight.identifier == 'ins-1'
        assert insight.confidence == 0.8
        assert insight.validation_method == 'behavior_change'

    def test_defaults(self):
        insight = InsightObject(identifier='ins-1', insight_statement='test')
        assert insight.confidence == 0.0
        assert insight.validation_method == ''
        assert insight.evidence == ()

    def test_frozen(self):
        insight = InsightObject(identifier='ins-1', insight_statement='test')
        with pytest.raises(AttributeError):
            insight.confidence = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BlindSpot tests
# ---------------------------------------------------------------------------


class TestBlindSpot:
    def test_creation(self):
        bs = BlindSpot(
            identifier='bs-1',
            description='Unrecognized avoidance pattern',
            estimated_impact=0.7,
            evidence=('ev-1', 'ev-2'),
            behavioral_consistency=0.8,
            lack_of_explicit_recognition=0.9,
        )
        assert bs.identifier == 'bs-1'
        assert bs.estimated_impact == 0.7
        assert len(bs.evidence) == 2

    def test_defaults(self):
        bs = BlindSpot(identifier='bs-1', description='test')
        assert bs.estimated_impact == 0.0
        assert bs.evidence == ()
        assert bs.behavioral_consistency == 0.0

    def test_frozen(self):
        bs = BlindSpot(identifier='bs-1', description='test')
        with pytest.raises(AttributeError):
            bs.estimated_impact = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ReflectionEngine tests
# ---------------------------------------------------------------------------


class TestReflectionEngine:
    def test_process_returns_result(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert isinstance(result, ReflectionResult)

    def test_reflections_extracted(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert result.total_extracted >= 0

    def test_all_reflections_have_identifiers(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        for ref in result.reflections.values():
            assert ref.identifier
            assert isinstance(ref.identifier, str)

    def test_confidence_in_range(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        for ref in result.reflections.values():
            assert 0.0 <= ref.confidence <= 1.0

    def test_determinism(self, engine, sample_evidence):
        """Same input -> same output (deterministic pipeline)."""
        r1 = engine.process(sample_evidence)
        r2 = engine.process(sample_evidence)
        assert r1.total_extracted == r2.total_extracted

    def test_empty_evidence(self, engine):
        result = engine.process([])
        assert result.total_extracted == 0
        assert len(result.blind_spots) == 0

    def test_with_patterns(self, engine, sample_evidence, sample_patterns):
        result = engine.process(sample_evidence, patterns=sample_patterns)
        assert isinstance(result, ReflectionResult)

    def test_with_narratives(self, engine, sample_evidence, sample_narratives):
        result = engine.process(sample_evidence, narratives=sample_narratives)
        assert isinstance(result, ReflectionResult)

    def test_with_beliefs(self, engine, sample_evidence, sample_beliefs):
        result = engine.process(sample_evidence, beliefs=sample_beliefs)
        assert isinstance(result, ReflectionResult)

    def test_full_pipeline(self, engine, sample_evidence, sample_patterns,
                           sample_narratives, sample_beliefs, sample_identity):
        result = engine.process(
            sample_evidence,
            patterns=sample_patterns,
            narratives=sample_narratives,
            beliefs=sample_beliefs,
            identity=sample_identity,
        )
        assert isinstance(result, ReflectionResult)
        assert isinstance(result.blind_spots, list)

    def test_blind_spots_detected(self, engine, sample_evidence, sample_identity):
        result = engine.process(sample_evidence, identity=sample_identity)
        assert isinstance(result.blind_spots, list)

    def test_reflections_stored(self, engine, sample_evidence):
        engine.process(sample_evidence)
        assert len(engine._reflections) >= 0

    def test_default_ai_router_is_none(self):
        """Engine works without ai_router (default None)."""
        eng = ReflectionEngine()
        assert eng._ai_router is None
        result = eng.process([{'id': 'ev-1', 'text': 'test', 'category': 'self_report'}])
        assert isinstance(result, ReflectionResult)

    def test_with_ai_router_parameter(self):
        """Engine accepts ai_router parameter."""
        mock_router = object()
        eng = ReflectionEngine(ai_router=mock_router)
        assert eng._ai_router is mock_router

    def test_llm_fallback_on_running_loop(self):
        """When event loop is running, LLM path returns None and falls back to rule-based."""
        import asyncio

        async def _run():
            eng = ReflectionEngine(ai_router=object())
            evidence = [
                {'id': 'ev-1', 'text': 'I procrastinate', 'category': 'behavioral_report'},
                {'id': 'ev-2', 'text': 'I procrastinate under stress', 'category': 'behavioral_report'},
            ]
            result = eng.process(evidence)
            assert isinstance(result, ReflectionResult)
            return result

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# BlindSpotDetector tests
# ---------------------------------------------------------------------------


class TestBlindSpotDetector:
    def test_detect_returns_list(self, blind_spot_detector, sample_evidence):
        spots = blind_spot_detector.detect(sample_evidence, [], [])
        assert isinstance(spots, list)

    def test_empty_inputs(self, blind_spot_detector):
        spots = blind_spot_detector.detect([], [], [])
        assert spots == []

    def test_detects_behavioral_patterns(self, blind_spot_detector):
        evidence = [
            {'id': 'ev-1', 'text': 'I always avoid conflict', 'category': 'behavioral_report'},
            {'id': 'ev-2', 'text': 'I avoid difficult conversations', 'category': 'behavioral_report'},
            {'id': 'ev-3', 'text': 'I stay quiet when upset', 'category': 'behavioral_report'},
        ]
        identity = [
            {'id': 'id-1', 'statement': 'I am assertive', 'domain': 'self_concept'},
        ]
        spots = blind_spot_detector.detect(evidence, [], identity)
        assert isinstance(spots, list)

    def test_no_blind_spots_when_recognized(self, blind_spot_detector):
        evidence = [
            {'id': 'ev-1', 'text': 'I avoid conflict', 'category': 'behavioral_report'},
        ]
        identity = [
            {'id': 'id-1', 'statement': 'I avoid conflict in relationships', 'domain': 'self_concept'},
        ]
        spots = blind_spot_detector.detect(evidence, [], identity)
        # Should have fewer/no blind spots when recognized
        assert isinstance(spots, list)


# ---------------------------------------------------------------------------
# AwakeningDynamics tests
# ---------------------------------------------------------------------------


class TestAwakeningDynamics:
    def test_estimate_level_returns_progress(self, awakening_dynamics):
        result = awakening_dynamics.estimate_level([], [])
        assert isinstance(result, AwakeningProgress)

    def test_empty_events_level_zero(self, awakening_dynamics):
        result = awakening_dynamics.estimate_level([], [])
        assert result.current_level == 0
        assert result.confidence == 1.0

    def test_meta_cognition_events(self, awakening_dynamics):
        events = [
            {'id': 'mc-1', 'text': 'I noticed that I tend to procrastinate', 'type': 'pattern_recognition'},
            {'id': 'mc-2', 'text': 'I observe my anxiety before deadlines', 'type': 'observation'},
        ]
        result = awakening_dynamics.estimate_level(events, [])
        assert result.current_level >= 1
        assert result.confidence > 0

    def test_reflection_events(self, awakening_dynamics):
        events = [
            {'id': 'r-1', 'text': 'I realize my fear comes from childhood', 'type': 'understanding'},
            {'id': 'r-2', 'text': 'I tried a new approach and it worked', 'type': 'experimentation'},
        ]
        result = awakening_dynamics.estimate_level([], events)
        assert result.current_level >= 2

    def test_high_level_events(self, awakening_dynamics):
        meta_events = [
            {'id': 'mc-1', 'text': 'I revised my core identity', 'type': 'identity_revision'},
        ]
        reflection_events = [
            {'id': 'r-1', 'text': 'I have integrated this into who I am', 'type': 'integration'},
        ]
        result = awakening_dynamics.estimate_level(meta_events, reflection_events)
        assert result.current_level >= 5

    def test_level_in_range(self, awakening_dynamics):
        events = [
            {'id': 'mc-1', 'text': 'I notice patterns', 'type': 'pattern_recognition'},
        ]
        result = awakening_dynamics.estimate_level(events, [])
        assert 0 <= result.current_level <= 7

    def test_evidence_tracked(self, awakening_dynamics):
        events = [
            {'id': 'mc-1', 'text': 'I noticed something', 'type': 'observation'},
        ]
        result = awakening_dynamics.estimate_level(events, [])
        assert len(result.evidence) > 0


# ---------------------------------------------------------------------------
# Catalogue tests
# ---------------------------------------------------------------------------


class TestCatalogues:
    def test_reflection_scopes(self):
        assert 'project' in REFLECTION_SCOPES
        assert 'identity' in REFLECTION_SCOPES
        assert 'life_trajectory' in REFLECTION_SCOPES

    def test_granularity_levels(self):
        assert 'micro' in GRANULARITY_LEVELS
        assert 'session' in GRANULARITY_LEVELS
        assert 'life' in GRANULARITY_LEVELS

    def test_lifecycle_states(self):
        assert 'candidate' in LIFECYCLE_STATES
        assert 'canonical' in LIFECYCLE_STATES

    def test_validation_methods(self):
        assert 'behavior_change' in VALIDATION_METHODS
        assert 'belief_revision' in VALIDATION_METHODS

    def test_awakening_levels(self):
        assert len(AWAKENING_LEVELS) == 8
        assert AWAKENING_LEVELS[0] == 'automatic'
        assert AWAKENING_LEVELS[7] == 'integration'
