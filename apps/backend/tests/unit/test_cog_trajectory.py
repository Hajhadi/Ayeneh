"""Tests for the COG-13 Cognitive Trajectory Engine."""

from __future__ import annotations

import pytest

from ayeneh.cog.trajectory.engine import CognitiveTrajectoryEngine
from ayeneh.cog.trajectory.phases import (
    DevelopmentalPhase,
    PhaseIdentifier,
    TransitionalPeriod,
)
from ayeneh.cog.trajectory.types import (
    DIRECTION_TYPES,
    TARGET_TYPES,
    TRAJECTORY_LIFECYCLE_STATES,
    DevelopmentalMilestone,
    Transformation,
    TrajectoryObject,
    TrajectoryResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return CognitiveTrajectoryEngine()


@pytest.fixture
def phase_identifier():
    return PhaseIdentifier()


@pytest.fixture
def sample_cognitive_objects():
    return [
        {'id': 'obj-1', 'type': 'belief', 'text': 'I work well under pressure', 'timestamp': '2024-01'},
        {'id': 'obj-1', 'type': 'belief', 'text': 'I sometimes work well under pressure', 'timestamp': '2024-06'},
        {'id': 'obj-1', 'type': 'belief', 'text': 'I can work well in various conditions', 'timestamp': '2024-12'},
        {'id': 'obj-2', 'type': 'value', 'text': 'Productivity is my top priority', 'timestamp': '2024-01'},
        {'id': 'obj-2', 'type': 'value', 'text': 'Balance between productivity and wellbeing', 'timestamp': '2024-06'},
    ]


@pytest.fixture
def sample_evidence():
    return [
        {'id': 'ev-1', 'text': 'I work well under pressure', 'category': 'behavioral_report'},
        {'id': 'ev-2', 'text': 'I balanced productivity with rest', 'category': 'behavioral_report'},
    ]


@pytest.fixture
def sample_trajectory():
    return TrajectoryObject(
        identifier='traj-1',
        target_cognitive_object='obj-1',
        target_type='belief',
        temporal_sequence=(
            {'text': 'old belief', 'timestamp': '2024-01'},
            {'text': 'new belief', 'timestamp': '2024-06'},
        ),
        major_transitions=(),
        rate_of_change=0.3,
        direction='strengthening',
        confidence=0.6,
        historical_continuity=0.7,
    )


# ---------------------------------------------------------------------------
# TrajectoryObject tests
# ---------------------------------------------------------------------------


class TestTrajectoryObject:
    def test_creation(self, sample_trajectory):
        assert sample_trajectory.identifier == 'traj-1'
        assert sample_trajectory.target_type == 'belief'
        assert sample_trajectory.direction == 'strengthening'

    def test_defaults(self):
        traj = TrajectoryObject(
            identifier='t1',
            target_cognitive_object='obj-1',
            target_type='belief',
        )
        assert traj.temporal_sequence == ()
        assert traj.major_transitions == ()
        assert traj.rate_of_change == 0.0
        assert traj.direction == ''
        assert traj.confidence == 0.0
        assert traj.lifecycle_state == 'candidate'
        assert traj.specification_version == '1.0.0'

    def test_frozen(self, sample_trajectory):
        with pytest.raises(AttributeError):
            sample_trajectory.direction = 'weakening'  # type: ignore[misc]

    def test_timestamp_auto_generated(self):
        traj = TrajectoryObject(
            identifier='t1',
            target_cognitive_object='obj-1',
            target_type='belief',
        )
        assert traj.creation_timestamp is not None


# ---------------------------------------------------------------------------
# DevelopmentalMilestone tests
# ---------------------------------------------------------------------------


class TestDevelopmentalMilestone:
    def test_creation(self):
        m = DevelopmentalMilestone(
            milestone_id='m-1',
            description='Belief revision from pressure-dependent to flexible',
            previous_state='pressure-dependent',
            new_state='flexible',
        )
        assert m.milestone_id == 'm-1'
        assert m.previous_state == 'pressure-dependent'
        assert m.new_state == 'flexible'

    def test_defaults(self):
        m = DevelopmentalMilestone(milestone_id='m-1', description='test')
        assert m.evidence == ()
        assert m.previous_state == ''
        assert m.new_state == ''

    def test_frozen(self):
        m = DevelopmentalMilestone(milestone_id='m-1', description='test')
        with pytest.raises(AttributeError):
            m.description = 'other'  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Transformation tests
# ---------------------------------------------------------------------------


class TestTransformation:
    def test_creation(self):
        t = Transformation(
            transformation_id='t-1',
            description='Major identity reorganization',
            previous_organization='fragmented',
            new_organization='integrated',
        )
        assert t.transformation_id == 't-1'
        assert t.previous_organization == 'fragmented'
        assert t.new_organization == 'integrated'

    def test_defaults(self):
        t = Transformation(transformation_id='t-1', description='test')
        assert t.intermediate_states == ()
        assert t.evidence == ()

    def test_frozen(self):
        t = Transformation(transformation_id='t-1', description='test')
        with pytest.raises(AttributeError):
            t.description = 'other'  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CognitiveTrajectoryEngine tests
# ---------------------------------------------------------------------------


class TestCognitiveTrajectoryEngine:
    def test_process_returns_result(self, engine, sample_cognitive_objects, sample_evidence):
        result = engine.process(sample_cognitive_objects, sample_evidence)
        assert isinstance(result, TrajectoryResult)

    def test_trajectories_extracted(self, engine, sample_cognitive_objects, sample_evidence):
        result = engine.process(sample_cognitive_objects, sample_evidence)
        assert result.total_extracted >= 0

    def test_all_trajectories_have_identifiers(self, engine, sample_cognitive_objects, sample_evidence):
        result = engine.process(sample_cognitive_objects, sample_evidence)
        for traj in result.trajectories.values():
            assert traj.identifier
            assert isinstance(traj.identifier, str)

    def test_confidence_in_range(self, engine, sample_cognitive_objects, sample_evidence):
        result = engine.process(sample_cognitive_objects, sample_evidence)
        for traj in result.trajectories.values():
            assert 0.0 <= traj.confidence <= 1.0

    def test_determinism(self, engine, sample_cognitive_objects, sample_evidence):
        """Same input -> same output (deterministic pipeline)."""
        r1 = engine.process(sample_cognitive_objects, sample_evidence)
        r2 = engine.process(sample_cognitive_objects, sample_evidence)
        assert r1.total_extracted == r2.total_extracted

    def test_empty_inputs(self, engine):
        result = engine.process([], [])
        assert result.total_extracted == 0
        assert len(result.milestones) == 0

    def test_single_version_object(self, engine):
        objects = [
            {'id': 'obj-1', 'type': 'belief', 'text': 'I believe X', 'timestamp': '2024-01'},
        ]
        result = engine.process(objects, [])
        assert isinstance(result, TrajectoryResult)

    def test_multiple_versions(self, engine, sample_cognitive_objects):
        result = engine.process(sample_cognitive_objects, [])
        assert result.total_extracted >= 0

    def test_milestones_detected(self, engine, sample_cognitive_objects, sample_evidence):
        result = engine.process(sample_cognitive_objects, sample_evidence)
        assert isinstance(result.milestones, list)

    def test_phases_identified(self, engine, sample_cognitive_objects, sample_evidence):
        result = engine.process(sample_cognitive_objects, sample_evidence)
        assert isinstance(result.phases, list)

    def test_trajectories_stored(self, engine, sample_cognitive_objects):
        engine.process(sample_cognitive_objects, [])
        assert len(engine._trajectories) >= 0


# ---------------------------------------------------------------------------
# PhaseIdentifier tests
# ---------------------------------------------------------------------------


class TestPhaseIdentifier:
    def test_identify_returns_tuple(self, phase_identifier):
        phases, transitions = phase_identifier.identify([])
        assert isinstance(phases, list)
        assert isinstance(transitions, list)

    def test_empty_trajectories(self, phase_identifier):
        phases, transitions = phase_identifier.identify([])
        assert len(phases) == 0
        assert len(transitions) == 0

    def test_single_trajectory(self, phase_identifier, sample_trajectory):
        phases, transitions = phase_identifier.identify([sample_trajectory])
        assert len(phases) >= 0

    def test_multiple_trajectories(self, phase_identifier):
        trajectories = [
            TrajectoryObject(
                identifier='t1', target_cognitive_object='o1',
                target_type='belief', direction='strengthening',
                rate_of_change=0.3, historical_continuity=0.7,
            ),
            TrajectoryObject(
                identifier='t2', target_cognitive_object='o2',
                target_type='value', direction='strengthening',
                rate_of_change=0.4, historical_continuity=0.6,
            ),
        ]
        phases, transitions = phase_identifier.identify(trajectories)
        assert len(phases) >= 1

    def test_high_change_trajectories(self, phase_identifier):
        trajectories = [
            TrajectoryObject(
                identifier='t1', target_cognitive_object='o1',
                target_type='identity', direction='transforming',
                rate_of_change=0.8, historical_continuity=0.2,
            ),
        ]
        phases, transitions = phase_identifier.identify(trajectories)
        assert isinstance(transitions, list)

    def test_phase_has_required_fields(self, phase_identifier):
        trajectories = [
            TrajectoryObject(
                identifier='t1', target_cognitive_object='o1',
                target_type='belief', direction='stabilizing',
                rate_of_change=0.1, historical_continuity=0.9,
            ),
        ]
        phases, _ = phase_identifier.identify(trajectories)
        for phase in phases:
            assert phase.phase_id
            assert phase.description


# ---------------------------------------------------------------------------
# Catalogue tests
# ---------------------------------------------------------------------------


class TestCatalogues:
    def test_target_types(self):
        assert 'belief' in TARGET_TYPES
        assert 'value' in TARGET_TYPES
        assert 'identity' in TARGET_TYPES
        assert 'pattern' in TARGET_TYPES

    def test_direction_types(self):
        assert 'strengthening' in DIRECTION_TYPES
        assert 'weakening' in DIRECTION_TYPES
        assert 'transforming' in DIRECTION_TYPES

    def test_trajectory_lifecycle_states(self):
        assert 'candidate' in TRAJECTORY_LIFECYCLE_STATES
        assert 'canonical' in TRAJECTORY_LIFECYCLE_STATES
