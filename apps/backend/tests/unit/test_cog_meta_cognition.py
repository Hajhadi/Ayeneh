"""Tests for the COG-16 Meta-Cognition pipeline."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.cog.meta_cognition.types import (
    AWARENESS_LEVELS,
    META_COGNITIVE_LIFECYCLE_STATES,
    AwarenessEvent,
    CognitiveTransparency,
    MetaCognitiveObject,
    ObserverEpisode,
)
from ayeneh.cog.meta_cognition.engine import (
    MetaCognitionEngine,
    MetaCognitionResult,
)
from ayeneh.cog.meta_cognition.awareness import (
    AwarenessLevelTracker,
    DeIdentificationTracker,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def meta_engine():
    return MetaCognitionEngine()


@pytest.fixture
def awareness_tracker():
    return AwarenessLevelTracker()


@pytest.fixture
def de_id_tracker():
    return DeIdentificationTracker()


@pytest.fixture
def sample_evidence():
    return [
        {'identifier': 'ev-1', 'type': 'meta_cognitive_report', 'text': 'I notice that I often avoid conflict'},
        {'identifier': 'ev-2', 'type': 'observation', 'text': 'The weather is nice'},
        {'identifier': 'ev-3', 'type': 'self_report', 'text': 'I feel anxious about the future'},
    ]


@pytest.fixture
def sample_reflections():
    return [
        {'identifier': 'ref-1', 'text': 'I realise that my thinking patterns affect my behaviour', 'reflection': 'Realisation about patterns'},
        {'identifier': 'ref-2', 'text': 'Looking back, I can see how my beliefs shaped my decisions'},
    ]


@pytest.fixture
def sample_narratives():
    return [
        {'identifier': 'narr-1', 'text': 'I am someone who overcomes challenges'},
    ]


@pytest.fixture
def sample_beliefs():
    return [
        {'identifier': 'b-1', 'belief_statement': 'Hard work always pays off'},
    ]


@pytest.fixture
def sample_identity():
    return [
        {'identifier': 'id-1', 'identity_statement': 'I am resilient'},
    ]


@pytest.fixture
def sample_awareness_events():
    return [
        AwarenessEvent(event_id='ae-1', recognized_process='avoidance pattern', awareness_level=1),
        AwarenessEvent(event_id='ae-2', recognized_process='thinking trap', awareness_level=2),
        AwarenessEvent(event_id='ae-3', recognized_process='emotional trigger', awareness_level=3),
        AwarenessEvent(event_id='ae-4', recognized_process='observing thoughts', awareness_level=4),
    ]


@pytest.fixture
def sample_meta_objects():
    return [
        MetaCognitiveObject(
            identifier='mco-1',
            observed_cognitive_process='avoidance pattern',
            awareness_description='I avoid conflict situations',
            awareness_level=1,
            confidence=0.4,
            stability=0.3,
        ),
        MetaCognitiveObject(
            identifier='mco-2',
            observed_cognitive_process='thinking trap',
            awareness_description='I catch myself catastrophising',
            awareness_level=3,
            confidence=0.7,
            stability=0.6,
        ),
        MetaCognitiveObject(
            identifier='mco-3',
            observed_cognitive_process='observer mode',
            awareness_description='I observe my thoughts without engaging',
            awareness_level=5,
            confidence=0.9,
            stability=0.8,
        ),
    ]


# ---------------------------------------------------------------------------
# MetaCognitiveObject tests
# ---------------------------------------------------------------------------


class TestMetaCognitiveObject:
    def test_creation(self):
        obj = MetaCognitiveObject(
            identifier='mco-1',
            observed_cognitive_process='avoidance',
            awareness_description='I avoid conflict',
        )
        assert obj.identifier == 'mco-1'
        assert obj.observed_cognitive_process == 'avoidance'
        assert obj.awareness_description == 'I avoid conflict'

    def test_defaults(self):
        obj = MetaCognitiveObject(identifier='mco-2', observed_cognitive_process='test', awareness_description='test')
        assert obj.awareness_level == 0
        assert obj.confidence == 0.0
        assert obj.stability == 0.0
        assert obj.lifecycle_state == 'candidate'
        assert obj.specification_version == '1.0.0'

    def test_frozen(self):
        obj = MetaCognitiveObject(identifier='mco-3', observed_cognitive_process='test', awareness_description='test')
        with pytest.raises(AttributeError):
            obj.awareness_level = 3  # type: ignore[misc]

    def test_tuples(self):
        obj = MetaCognitiveObject(
            identifier='mco-4',
            observed_cognitive_process='test',
            awareness_description='test',
            supporting_evidence=('ev-1', 'ev-2'),
            associated_reflections=('ref-1',),
        )
        assert len(obj.supporting_evidence) == 2
        assert len(obj.associated_reflections) == 1


# ---------------------------------------------------------------------------
# AwarenessEvent tests
# ---------------------------------------------------------------------------


class TestAwarenessEvent:
    def test_creation(self):
        event = AwarenessEvent(event_id='ae-1', recognized_process='thinking pattern')
        assert event.event_id == 'ae-1'
        assert event.recognized_process == 'thinking pattern'

    def test_defaults(self):
        event = AwarenessEvent(event_id='ae-2', recognized_process='test')
        assert event.awareness_level == 1
        assert isinstance(event.timestamp, datetime)

    def test_frozen(self):
        event = AwarenessEvent(event_id='ae-3', recognized_process='test')
        with pytest.raises(AttributeError):
            event.awareness_level = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ObserverEpisode tests
# ---------------------------------------------------------------------------


class TestObserverEpisode:
    def test_creation(self):
        ep = ObserverEpisode(episode_id='ep-1', duration_s=120.0, context='therapy')
        assert ep.episode_id == 'ep-1'
        assert ep.duration_s == 120.0
        assert ep.context == 'therapy'

    def test_defaults(self):
        ep = ObserverEpisode(episode_id='ep-2')
        assert ep.duration_s == 0.0
        assert ep.recovery_following_loss is False

    def test_frozen(self):
        ep = ObserverEpisode(episode_id='ep-3')
        with pytest.raises(AttributeError):
            ep.duration_s = 60.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CognitiveTransparency tests
# ---------------------------------------------------------------------------


class TestCognitiveTransparency:
    def test_creation(self):
        ct = CognitiveTransparency(
            narrative_visibility=0.8,
            belief_visibility=0.6,
            overall_transparency=0.7,
        )
        assert ct.narrative_visibility == 0.8
        assert ct.belief_visibility == 0.6
        assert ct.overall_transparency == 0.7

    def test_defaults(self):
        ct = CognitiveTransparency()
        assert ct.narrative_visibility == 0.0
        assert ct.overall_transparency == 0.0

    def test_frozen(self):
        ct = CognitiveTransparency()
        with pytest.raises(AttributeError):
            ct.overall_transparency = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MetaCognitionEngine tests
# ---------------------------------------------------------------------------


class TestMetaCognitionEngine:
    def test_process_returns_result(self, meta_engine, sample_evidence):
        result = meta_engine.process(sample_evidence)
        assert isinstance(result, MetaCognitionResult)

    def test_objects_extracted(self, meta_engine, sample_evidence):
        result = meta_engine.process(sample_evidence)
        assert result.total_extracted >= 0

    def test_objects_have_identifiers(self, meta_engine, sample_evidence):
        result = meta_engine.process(sample_evidence)
        for obj in result.objects:
            assert obj.identifier
            assert isinstance(obj.identifier, str)

    def test_objects_have_valid_awareness_level(self, meta_engine, sample_evidence):
        result = meta_engine.process(sample_evidence)
        for obj in result.objects:
            assert obj.awareness_level in AWARENESS_LEVELS

    def test_objects_are_provisional(self, meta_engine, sample_evidence):
        result = meta_engine.process(sample_evidence)
        for obj in result.objects:
            assert obj.lifecycle_state == 'provisional'

    def test_awareness_levels_tracked(self, meta_engine, sample_evidence):
        result = meta_engine.process(sample_evidence)
        assert isinstance(result.awareness_levels, dict)

    def test_transparency_computed(self, meta_engine, sample_evidence):
        result = meta_engine.process(sample_evidence)
        assert isinstance(result.transparency, CognitiveTransparency)
        assert 0.0 <= result.transparency.overall_transparency <= 1.0

    def test_de_identification_computed(self, meta_engine, sample_evidence):
        result = meta_engine.process(sample_evidence)
        assert isinstance(result.de_identification, dict)

    def test_with_reflections(self, meta_engine, sample_evidence, sample_reflections):
        result = meta_engine.process(sample_evidence, reflections=sample_reflections)
        assert result.total_extracted >= 0

    def test_with_all_inputs(self, meta_engine, sample_evidence, sample_reflections,
                             sample_narratives, sample_beliefs, sample_identity):
        result = meta_engine.process(
            sample_evidence,
            reflections=sample_reflections,
            narratives=sample_narratives,
            beliefs=sample_beliefs,
            identity=sample_identity,
        )
        assert isinstance(result, MetaCognitionResult)

    def test_empty_evidence(self, meta_engine):
        result = meta_engine.process([])
        assert result.total_extracted == 0

    def test_processing_timestamp(self, meta_engine, sample_evidence):
        result = meta_engine.process(sample_evidence)
        assert isinstance(result.processing_timestamp, datetime)

    def test_meta_cognitive_keywords_detected(self, meta_engine):
        evidence = [
            {'identifier': 'ev-1', 'type': 'self_report', 'text': 'I notice that I am avoiding the conversation'},
        ]
        result = meta_engine.process(evidence)
        assert result.total_extracted > 0

    def test_non_meta_evidence_filtered(self, meta_engine):
        evidence = [
            {'identifier': 'ev-1', 'type': 'observation', 'text': 'The weather is nice today'},
        ]
        result = meta_engine.process(evidence)
        assert result.total_extracted == 0


# ---------------------------------------------------------------------------
# AwarenessLevelTracker tests
# ---------------------------------------------------------------------------


class TestAwarenessLevelTracker:
    def test_track_empty(self, awareness_tracker):
        result = awareness_tracker.track([])
        assert result['total_events'] == 0
        assert result['average_level'] == 0.0

    def test_track_events(self, awareness_tracker, sample_awareness_events):
        result = awareness_tracker.track(sample_awareness_events)
        assert result['total_events'] == 4
        assert result['average_level'] > 0.0
        assert result['highest_level'] == 4

    def test_level_distribution(self, awareness_tracker, sample_awareness_events):
        result = awareness_tracker.track(sample_awareness_events)
        dist = result['level_distribution']
        assert 1 in dist
        assert 2 in dist
        assert 3 in dist
        assert 4 in dist

    def test_progression(self, awareness_tracker, sample_awareness_events):
        result = awareness_tracker.track(sample_awareness_events)
        assert len(result['level_progression']) == 4

    def test_compute_average_level(self, awareness_tracker, sample_meta_objects):
        avg = awareness_tracker.compute_average_level(sample_meta_objects)
        assert 0.0 <= avg <= 5.0

    def test_compute_average_level_empty(self, awareness_tracker):
        avg = awareness_tracker.compute_average_level([])
        assert avg == 0.0

    def test_detect_level_progression(self, awareness_tracker, sample_meta_objects):
        progression = awareness_tracker.detect_level_progression(sample_meta_objects)
        assert len(progression) == 3
        assert progression[0]['awareness_level'] <= progression[-1]['awareness_level']

    def test_detect_level_progression_empty(self, awareness_tracker):
        progression = awareness_tracker.detect_level_progression([])
        assert progression == []


# ---------------------------------------------------------------------------
# DeIdentificationTracker tests
# ---------------------------------------------------------------------------


class TestDeIdentificationTracker:
    def test_track_empty(self, de_id_tracker):
        result = de_id_tracker.track([])
        assert result['total_objects'] == 0
        assert result['average_de_identification'] == 0.0

    def test_track_objects(self, de_id_tracker, sample_meta_objects):
        result = de_id_tracker.track(sample_meta_objects)
        assert result['total_objects'] == 3
        assert result['average_de_identification'] > 0.0

    def test_objects_with_observer(self, de_id_tracker, sample_meta_objects):
        result = de_id_tracker.track(sample_meta_objects)
        assert result['objects_with_observer'] >= 1  # mco-3 has level 5

    def test_level_distribution(self, de_id_tracker, sample_meta_objects):
        result = de_id_tracker.track(sample_meta_objects)
        dist = result['level_distribution']
        assert 1 in dist
        assert 3 in dist
        assert 5 in dist

    def test_compute_de_identification_score(self, de_id_tracker, sample_meta_objects):
        score = de_id_tracker.compute_de_identification_score(sample_meta_objects)
        assert 0.0 <= score <= 1.0

    def test_compute_de_identification_score_empty(self, de_id_tracker):
        score = de_id_tracker.compute_de_identification_score([])
        assert score == 0.0

    def test_higher_awareness_more_de_id(self, de_id_tracker):
        low = MetaCognitiveObject(
            identifier='low', observed_cognitive_process='test',
            awareness_description='test', awareness_level=1, confidence=0.3, stability=0.2,
        )
        high = MetaCognitiveObject(
            identifier='high', observed_cognitive_process='test',
            awareness_description='test', awareness_level=5, confidence=0.9, stability=0.8,
        )
        low_score = de_id_tracker.compute_de_identification_score([low])
        high_score = de_id_tracker.compute_de_identification_score([high])
        assert high_score > low_score
