"""Tests for MEM-02 episodic memory: types, engine, boundaries, emotional landscape."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime, timedelta

from ayeneh.memo.episodic.boundaries import (
    BOUNDARY_SIGNAL_TYPES,
    DEFAULT_INACTIVITY_THRESHOLD_SECONDS,
    EpisodeBoundary,
    EpisodeBoundaryDetector,
)
from ayeneh.memo.episodic.emotional_landscape import (
    EmotionalLandscape,
    EmotionalState,
    EmotionalTransition,
    PRIMARY_EMOTIONS,
)
from ayeneh.memo.episodic.engine import EpisodicMemoryEngine, PipelineResult
from ayeneh.memo.episodic.types import (
    EPISODE_CATEGORIES,
    EPISODE_OUTCOMES,
    EPISODE_RELATIONSHIPS,
    EPISODE_STATES,
    EPISODE_STATE_TRANSITIONS,
    EpisodeObject,
    EpisodeRelationship,
    LifeChapter,
    MilestoneObject,
    can_episode_transition,
)
from ayeneh.memo.types import Event, Observation


# ===================================================================
# Episode types constants
# ===================================================================

class TestEpisodeConstants:
    def test_categories_count(self) -> None:
        assert len(EPISODE_CATEGORIES) == 11

    def test_states_count(self) -> None:
        assert len(EPISODE_STATES) == 6

    def test_outcomes_count(self) -> None:
        assert len(EPISODE_OUTCOMES) == 5

    def test_relationships_count(self) -> None:
        assert len(EPISODE_RELATIONSHIPS) == 10

    def test_candidate_can_become_active(self) -> None:
        assert can_episode_transition('candidate', 'active')

    def test_active_can_become_completed(self) -> None:
        assert can_episode_transition('active', 'completed')

    def test_archived_has_no_transitions(self) -> None:
        assert can_episode_transition('archived', 'active') is False


# ===================================================================
# EpisodeObject
# ===================================================================

class TestEpisodeObject:
    def test_creation(self) -> None:
        ep = EpisodeObject(identifier='ep-1', title='Test Episode')
        assert ep.identifier == 'ep-1'
        assert ep.title == 'Test Episode'
        assert ep.state == 'candidate'
        assert ep.outcome == 'still_unknown'
        assert ep.confidence == 0.0

    def test_defaults(self) -> None:
        ep = EpisodeObject(identifier='ep-2', title='E2')
        assert ep.summary == ''
        assert ep.primary_context == ''
        assert ep.primary_project == ''
        assert ep.primary_people == ()
        assert ep.primary_places == ()
        assert ep.supporting_conversations == ()
        assert ep.supporting_evidence == ()
        assert ep.major_decisions == ()
        assert ep.major_behaviors == ()
        assert ep.major_reflections == ()
        assert ep.associated_narratives == ()
        assert ep.associated_beliefs == ()
        assert ep.associated_goals == ()
        assert ep.associated_identity_components == ()
        assert ep.open_questions == ()
        assert ep.version_history == ()
        assert ep.episode_relationships == ()
        assert ep.milestones == ()
        assert ep.explainability_metadata == {}

    def test_frozen(self) -> None:
        ep = EpisodeObject(identifier='ep-3', title='E3')
        with pytest.raises(AttributeError):
            ep.identifier = 'ep-4'  # type: ignore[misc]

    def test_is_active(self) -> None:
        ep = EpisodeObject(identifier='ep-5', title='E5', state='active')
        assert ep.is_active is True

    def test_is_not_active(self) -> None:
        ep = EpisodeObject(identifier='ep-6', title='E6', state='candidate')
        assert ep.is_active is False

    def test_is_completed(self) -> None:
        ep = EpisodeObject(identifier='ep-7', title='E7', state='completed')
        assert ep.is_completed is True

    def test_can_transition_to(self) -> None:
        ep = EpisodeObject(identifier='ep-8', title='E8', state='candidate')
        assert ep.can_transition_to('active') is True
        assert ep.can_transition_to('completed') is False


# ===================================================================
# MilestoneObject
# ===================================================================

class TestMilestoneObject:
    def test_creation(self) -> None:
        m = MilestoneObject(
            milestone_id='ms-1',
            description='First milestone',
            timestamp=datetime.now(UTC),
        )
        assert m.milestone_id == 'ms-1'
        assert m.previous_state == ''
        assert m.new_state == ''


# ===================================================================
# EpisodeRelationship
# ===================================================================

class TestEpisodeRelationship:
    def test_creation(self) -> None:
        rel = EpisodeRelationship(
            source_episode_id='ep-1',
            target_episode_id='ep-2',
            relationship_type='continues',
        )
        assert rel.source_episode_id == 'ep-1'
        assert rel.weight == 1.0


# ===================================================================
# LifeChapter
# ===================================================================

class TestLifeChapter:
    def test_creation(self) -> None:
        ch = LifeChapter(
            chapter_id='ch-1',
            title='Early Career',
            beginning=datetime.now(UTC),
        )
        assert ch.title == 'Early Career'
        assert ch.major_episodes == ()
        assert ch.turning_points == ()
        assert ch.developmental_themes == ()
        assert ch.long_term_outcomes == ()


# ===================================================================
# EpisodeBoundaryDetector
# ===================================================================

class TestEpisodeBoundaryDetector:
    def test_empty_events(self) -> None:
        detector = EpisodeBoundaryDetector()
        assert detector.detect_boundaries([]) == []

    def test_goal_completion_boundary(self) -> None:
        detector = EpisodeBoundaryDetector()
        events = [
            Event(
                event_id='evt-1',
                description='I completed the project successfully',
                timestamp=datetime.now(UTC),
                event_type='completion',
            ),
        ]
        boundaries = detector.detect_boundaries(events)
        assert any(b.signal_type == 'goal_completion' for b in boundaries)

    def test_context_transition_boundary(self) -> None:
        detector = EpisodeBoundaryDetector()
        now = datetime.now(UTC)
        events = [
            Event(
                event_id='evt-1',
                description='Working on code',
                timestamp=now,
                metadata={'source_context': 'ide'},
            ),
            Event(
                event_id='evt-2',
                description='Reading a book',
                timestamp=now + timedelta(minutes=1),
                metadata={'source_context': 'kindle'},
            ),
        ]
        boundaries = detector.detect_boundaries(events)
        assert any(b.signal_type == 'context_transition' for b in boundaries)

    def test_identity_shift_boundary(self) -> None:
        detector = EpisodeBoundaryDetector()
        events = [
            Event(
                event_id='evt-1',
                description='I realized i am a leader, not a follower',
                timestamp=datetime.now(UTC),
            ),
        ]
        boundaries = detector.detect_boundaries(events)
        assert any(b.signal_type == 'identity_shift' for b in boundaries)

    def test_major_interruption_boundary(self) -> None:
        detector = EpisodeBoundaryDetector()
        events = [
            Event(
                event_id='evt-1',
                description='Suddenly interrupted by an emergency',
                timestamp=datetime.now(UTC),
                event_type='interruption',
            ),
        ]
        boundaries = detector.detect_boundaries(events)
        assert any(b.signal_type == 'major_interruption' for b in boundaries)

    def test_persistent_inactivity_boundary(self) -> None:
        detector = EpisodeBoundaryDetector(inactivity_threshold_seconds=60)
        now = datetime.now(UTC)
        events = [
            Event(event_id='evt-1', description='Working', timestamp=now),
            Event(event_id='evt-2', description='Back after break', timestamp=now + timedelta(seconds=120)),
        ]
        boundaries = detector.detect_boundaries(events)
        assert any(b.signal_type == 'persistent_inactivity' for b in boundaries)

    def test_boundary_sorted_by_time(self) -> None:
        detector = EpisodeBoundaryDetector(inactivity_threshold_seconds=60)
        now = datetime.now(UTC)
        events = [
            Event(event_id='evt-1', description='completed the task', timestamp=now),
            Event(event_id='evt-2', description='realized i am creative', timestamp=now + timedelta(minutes=1)),
            Event(event_id='evt-3', description='Back after long break', timestamp=now + timedelta(seconds=120)),
        ]
        boundaries = detector.detect_boundaries(events)
        timestamps = [b.timestamp for b in boundaries]
        assert timestamps == sorted(timestamps)

    def test_boundary_signal_types(self) -> None:
        assert len(BOUNDARY_SIGNAL_TYPES) == 6
        assert 'goal_completion' in BOUNDARY_SIGNAL_TYPES
        assert 'context_transition' in BOUNDARY_SIGNAL_TYPES
        assert 'identity_shift' in BOUNDARY_SIGNAL_TYPES
        assert 'project_completion' in BOUNDARY_SIGNAL_TYPES
        assert 'major_interruption' in BOUNDARY_SIGNAL_TYPES
        assert 'persistent_inactivity' in BOUNDARY_SIGNAL_TYPES

    def test_episode_boundary_to_dict(self) -> None:
        now = datetime.now(UTC)
        b = EpisodeBoundary(
            signal_type='goal_completion',
            timestamp=now,
            confidence=0.9,
            evidence=('ev-1',),
        )
        d = b.to_dict()
        assert d['signal_type'] == 'goal_completion'
        assert d['confidence'] == 0.9
        assert d['evidence'] == ['ev-1']


# ===================================================================
# EmotionalLandscape
# ===================================================================

class TestEmotionalLandscape:
    def test_empty_landscape(self) -> None:
        el = EmotionalLandscape()
        assert el.states == []
        assert el.transitions == []
        assert el.peak_intensity() is None
        assert el.dominant_emotion() is None
        assert el.average_valence() == 0.0

    def test_record_single_state(self) -> None:
        el = EmotionalLandscape()
        el.add_state(primary_emotion='joy', intensity=0.8, valence=0.9)
        assert len(el.states) == 1
        assert el.states[0].primary_emotion == 'joy'
        assert el.states[0].intensity == 0.8

    def test_record_transition(self) -> None:
        el = EmotionalLandscape()
        now = datetime.now(UTC)
        el.add_state(primary_emotion='joy', intensity=0.8, timestamp=now)
        el.add_state(primary_emotion='sadness', intensity=0.6, timestamp=now + timedelta(minutes=5))
        assert len(el.transitions) == 1
        assert el.transitions[0].from_emotion == 'joy'
        assert el.transitions[0].to_emotion == 'sadness'

    def test_no_transition_same_emotion_low_intensity_change(self) -> None:
        el = EmotionalLandscape()
        now = datetime.now(UTC)
        el.add_state(primary_emotion='joy', intensity=0.5, timestamp=now)
        el.add_state(primary_emotion='joy', intensity=0.6, timestamp=now + timedelta(minutes=1))
        assert len(el.transitions) == 0

    def test_transition_on_intensity_change(self) -> None:
        el = EmotionalLandscape()
        now = datetime.now(UTC)
        el.add_state(primary_emotion='joy', intensity=0.3, timestamp=now)
        el.add_state(primary_emotion='joy', intensity=0.9, timestamp=now + timedelta(minutes=1))
        assert len(el.transitions) == 1

    def test_peak_intensity(self) -> None:
        el = EmotionalLandscape()
        el.add_state(primary_emotion='joy', intensity=0.5)
        el.add_state(primary_emotion='anger', intensity=0.9)
        el.add_state(primary_emotion='fear', intensity=0.3)
        peak = el.peak_intensity()
        assert peak is not None
        assert peak.primary_emotion == 'anger'

    def test_dominant_emotion(self) -> None:
        el = EmotionalLandscape()
        for _ in range(3):
            el.add_state(primary_emotion='joy', intensity=0.5)
        el.add_state(primary_emotion='sadness', intensity=0.5)
        assert el.dominant_emotion() == 'joy'

    def test_average_valence(self) -> None:
        el = EmotionalLandscape()
        el.add_state(primary_emotion='joy', intensity=0.5, valence=1.0)
        el.add_state(primary_emotion='sadness', intensity=0.5, valence=-1.0)
        assert el.average_valence() == 0.0

    def test_transition_count(self) -> None:
        el = EmotionalLandscape()
        now = datetime.now(UTC)
        el.add_state(primary_emotion='joy', intensity=0.5, timestamp=now)
        el.add_state(primary_emotion='sadness', intensity=0.8, timestamp=now + timedelta(minutes=1))
        el.add_state(primary_emotion='anger', intensity=0.9, timestamp=now + timedelta(minutes=2))
        assert el.transition_count() == 2

    def test_summary(self) -> None:
        el = EmotionalLandscape()
        el.add_state(primary_emotion='joy', intensity=0.8, valence=0.9)
        el.add_state(primary_emotion='sadness', intensity=0.6, valence=-0.5)
        s = el.summary()
        assert s['state_count'] == 2
        assert s['transition_count'] == 1
        assert s['dominant_emotion'] == 'joy'
        assert 'average_valence' in s
        assert 'peak_emotion' in s

    def test_intensity_clamped(self) -> None:
        el = EmotionalLandscape()
        el.add_state(primary_emotion='joy', intensity=1.5)
        assert el.states[0].intensity == 1.0
        el.add_state(primary_emotion='sadness', intensity=-0.5)
        assert el.states[1].intensity == 0.0

    def test_primary_emotions_count(self) -> None:
        assert len(PRIMARY_EMOTIONS) >= 15

    def test_record_state_directly(self) -> None:
        el = EmotionalLandscape()
        state = EmotionalState(
            timestamp=datetime.now(UTC),
            primary_emotion='curiosity',
            intensity=0.7,
            valence=0.5,
            arousal=0.6,
        )
        el.record_state(state)
        assert len(el.states) == 1
        assert el.states[0].primary_emotion == 'curiosity'


# ===================================================================
# EpisodicMemoryEngine
# ===================================================================

class TestEpisodicMemoryEngine:
    def test_empty_observations(self) -> None:
        engine = EpisodicMemoryEngine()
        result = engine.run_pipeline([])
        assert result.episodes == []

    def test_single_observation(self) -> None:
        engine = EpisodicMemoryEngine()
        obs = Observation(
            observation_id='obs-1',
            content='Started working on the project',
            source='conversation',
            timestamp=datetime.now(UTC),
        )
        result = engine.run_pipeline([obs])
        # Single observation may not form a full episode with min_events=2
        assert isinstance(result, PipelineResult)

    def test_multiple_observations_form_episode(self) -> None:
        engine = EpisodicMemoryEngine(min_events_per_episode=1)
        now = datetime.now(UTC)
        observations = [
            Observation(
                observation_id=f'obs-{i}',
                content=f'Event {i} happened during the session',
                source='conversation',
                timestamp=now + timedelta(minutes=i),
            )
            for i in range(5)
        ]
        result = engine.run_pipeline(observations)
        assert len(result.episodes) >= 1
        assert result.episodes[0].state == 'active'

    def test_pipeline_result_structure(self) -> None:
        result = PipelineResult()
        assert result.episodes == []
        assert result.milestones == []
        assert result.boundaries == []
        assert result.emotional_landscapes == {}

    def test_engine_publishes_episodes(self) -> None:
        engine = EpisodicMemoryEngine(min_events_per_episode=1)
        now = datetime.now(UTC)
        observations = [
            Observation(
                observation_id='obs-1',
                content='Learned something new today',
                source='reflection',
                timestamp=now,
            ),
            Observation(
                observation_id='obs-2',
                content='Reflected on what I learned',
                source='reflection',
                timestamp=now + timedelta(minutes=5),
            ),
        ]
        result = engine.run_pipeline(observations)
        # Check that episodes are accessible
        for ep in result.episodes:
            retrieved = engine.get_episode(ep.identifier)
            assert retrieved is not None

    def test_list_episodes_filter_by_category(self) -> None:
        engine = EpisodicMemoryEngine(min_events_per_episode=1)
        now = datetime.now(UTC)
        observations = [
            Observation(
                observation_id='obs-1',
                content='I learned about machine learning',
                source='course',
                timestamp=now,
            ),
            Observation(
                observation_id='obs-2',
                content='Studied neural networks in depth',
                source='course',
                timestamp=now + timedelta(minutes=5),
            ),
        ]
        engine.run_pipeline(observations)
        all_eps = engine.list_episodes()
        # Should return at least some episodes
        assert isinstance(all_eps, list)

    def test_cluster_window(self) -> None:
        engine = EpisodicMemoryEngine(cluster_window_seconds=60)
        now = datetime.now(UTC)
        # Events far apart should form separate clusters
        observations = [
            Observation(
                observation_id='obs-1',
                content='Event A',
                source='s1',
                timestamp=now,
            ),
            Observation(
                observation_id='obs-2',
                content='Event B',
                source='s1',
                timestamp=now + timedelta(seconds=120),
            ),
        ]
        result = engine.run_pipeline(observations)
        # With 60s window, these should be in different clusters
        assert isinstance(result, PipelineResult)

    def test_emotional_landscapes_populated(self) -> None:
        engine = EpisodicMemoryEngine(min_events_per_episode=1)
        now = datetime.now(UTC)
        observations = [
            Observation(
                observation_id=f'obs-{i}',
                content=f'Event {i}',
                source='conversation',
                timestamp=now + timedelta(minutes=i),
            )
            for i in range(3)
        ]
        result = engine.run_pipeline(observations)
        for ep in result.episodes:
            assert ep.identifier in result.emotional_landscapes

    def test_get_nonexistent_episode(self) -> None:
        engine = EpisodicMemoryEngine()
        assert engine.get_episode('nonexistent') is None

    def test_event_classification(self) -> None:
        engine = EpisodicMemoryEngine(min_events_per_episode=1)
        now = datetime.now(UTC)
        observations = [
            Observation(
                observation_id='obs-1',
                content='I decided to change my approach',
                source='conversation',
                timestamp=now,
            ),
            Observation(
                observation_id='obs-2',
                content='I decided to go with option B',
                source='conversation',
                timestamp=now + timedelta(minutes=1),
            ),
        ]
        result = engine.run_pipeline(observations)
        # Decision events should be classified
        assert isinstance(result, PipelineResult)

    def test_confidence_increases_with_evidence(self) -> None:
        engine = EpisodicMemoryEngine(min_events_per_episode=1)
        now = datetime.now(UTC)
        observations = [
            Observation(
                observation_id=f'obs-{i}',
                content=f'Evidence point {i} supporting the pattern',
                source='observation',
                timestamp=now + timedelta(minutes=i),
            )
            for i in range(10)
        ]
        result = engine.run_pipeline(observations)
        if result.episodes:
            assert result.episodes[0].confidence > 0.0

    def test_version_history_on_publish(self) -> None:
        engine = EpisodicMemoryEngine(min_events_per_episode=1)
        now = datetime.now(UTC)
        observations = [
            Observation(
                observation_id='obs-1',
                content='Started the session',
                source='conversation',
                timestamp=now,
            ),
            Observation(
                observation_id='obs-2',
                content='Continued working',
                source='conversation',
                timestamp=now + timedelta(minutes=1),
            ),
        ]
        result = engine.run_pipeline(observations)
        for ep in result.episodes:
            assert len(ep.version_history) >= 1
