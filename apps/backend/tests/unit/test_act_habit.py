"""Tests for the ACT-02 Habit Formation Engine."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.act.habit_formation.types import (
    CUE_CATEGORIES,
    HABIT_LIFECYCLE,
    HABIT_LIFECYCLE_TRANSITIONS,
    REINFORCEMENT_TYPES,
    CueInstance,
    HabitCompetition,
    HabitEcologyRelation,
    HabitObject,
    HabitPublication,
    HabitResult,
    HabitStrengthSnapshot,
    ReinforcementRecord,
)
from ayeneh.act.habit_formation.engine import HabitFormationEngine
from ayeneh.act.habit_formation.ecology import HabitEcology


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return HabitFormationEngine()


@pytest.fixture
def sample_request():
    return {
        'habit_id': 'habit-001',
        'associated_behavior': 'morning_meditation',
        'primary_cue': 'After waking up',
        'secondary_cues': ('caffeine_sound', 'sunlight'),
        'expected_reward': 'calm_focus',
        'current_status': 'proposed',
    }


@pytest.fixture
def sample_context():
    return {
        'associated_goal': 'goal-001',
        'primary_cue_category': 'Time',
        'primary_cue_strength': 0.6,
        'primary_cue_frequency': 0.7,
        'secondary_cue_strength': 0.3,
        'observation_frequency': 0.8,
        'behavioral_consistency': 0.7,
        'context_stability': 0.6,
        'observed_reinforcement': 0.5,
        'reinforcements': [
            {
                'reinforcement_id': 'r1',
                'reinforcement_type': 'positive_outcome',
                'intensity': 0.8,
                'description': 'Felt great after meditation',
            },
            {
                'reinforcement_id': 'r2',
                'reinforcement_type': 'intrinsic_satisfaction',
                'intensity': 0.7,
                'description': 'Inner peace',
            },
        ],
    }


# ---------------------------------------------------------------------------
# Tests: Types
# ---------------------------------------------------------------------------


class TestHabitLifecycle:
    def test_lifecycle_completeness(self):
        assert len(HABIT_LIFECYCLE) == 8
        assert 'proposed' in HABIT_LIFECYCLE
        assert 'retired' in HABIT_LIFECYCLE

    def test_all_statuses_have_transitions(self):
        for status in HABIT_LIFECYCLE:
            assert status in HABIT_LIFECYCLE_TRANSITIONS

    def test_retired_is_terminal(self):
        assert HABIT_LIFECYCLE_TRANSITIONS['retired'] == []

    def test_cue_categories(self):
        assert len(CUE_CATEGORIES) == 6
        assert 'Time' in CUE_CATEGORIES
        assert 'Location' in CUE_CATEGORIES
        assert 'EmotionalState' in CUE_CATEGORIES

    def test_reinforcement_types(self):
        assert len(REINFORCEMENT_TYPES) == 6
        assert 'positive_outcome' in REINFORCEMENT_TYPES


class TestHabitObject:
    def test_default_values(self):
        h = HabitObject(habit_id='h1')
        assert h.habit_id == 'h1'
        assert h.current_status == 'proposed'
        assert h.habit_strength == 0.0
        assert h.observed_reinforcement == 0.0
        assert h.secondary_cues == ()

    def test_frozen(self):
        h = HabitObject(habit_id='h1')
        with pytest.raises(AttributeError):
            h.habit_id = 'h2'

    def test_custom_values(self):
        h = HabitObject(
            habit_id='h1',
            associated_goal='g1',
            associated_behavior='reading',
            primary_cue='evening',
            habit_strength=0.7,
            current_status='developing',
        )
        assert h.associated_goal == 'g1'
        assert h.habit_strength == 0.7
        assert h.current_status == 'developing'


class TestCueInstance:
    def test_creation(self):
        c = CueInstance(
            cue_id='c1',
            cue_category='Time',
            cue_description='morning',
            cue_strength=0.5,
        )
        assert c.cue_category == 'Time'
        assert c.cue_strength == 0.5


class TestReinforcementRecord:
    def test_creation(self):
        r = ReinforcementRecord(
            reinforcement_id='r1',
            reinforcement_type='positive_outcome',
            intensity=0.8,
        )
        assert r.intensity == 0.8


class TestHabitCompetition:
    def test_creation(self):
        c = HabitCompetition(
            competition_id='c1',
            habit_a='h1',
            habit_b='h2',
            competition_type='competing',
        )
        assert c.habit_a == 'h1'


class TestHabitStrengthSnapshot:
    def test_creation(self):
        s = HabitStrengthSnapshot(
            snapshot_id='s1',
            strength_value=0.6,
            consistency_score=0.7,
        )
        assert s.strength_value == 0.6


class TestHabitEcologyRelation:
    def test_creation(self):
        r = HabitEcologyRelation(
            relation_id='r1',
            habit_a='h1',
            habit_b='h2',
            relation_type='supportive',
            strength=0.5,
        )
        assert r.relation_type == 'supportive'


class TestHabitPublication:
    def test_creation(self):
        p = HabitPublication(
            publication_id='p1',
            habit_id='h1',
            habit_status='stable',
            strength=0.8,
        )
        assert p.habit_status == 'stable'


class TestHabitResult:
    def test_creation(self):
        h = HabitObject(habit_id='h1')
        r = HabitResult(habit=h)
        assert r.habit.habit_id == 'h1'
        assert r.cue_instances == ()
        assert r.pipeline_phases_completed == ()


# ---------------------------------------------------------------------------
# Tests: Engine
# ---------------------------------------------------------------------------


class TestHabitFormationEngine:
    def test_init(self, engine):
        assert engine._habits == {}

    def test_process_basic(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert isinstance(result, HabitResult)
        assert result.habit.habit_id == 'habit-001'
        assert len(result.pipeline_phases_completed) == 7

    def test_process_creates_habit(self, engine, sample_request):
        engine.process(sample_request)
        assert 'habit-001' in engine._habits

    def test_process_cues_detected(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert len(result.cue_instances) >= 2

    def test_process_reinforcements_tracked(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert len(result.reinforcement_records) >= 2

    def test_process_strength_estimated(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert result.habit.habit_strength > 0.0
        assert len(result.strength_snapshots) == 1

    def test_process_publication_generated(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert len(result.publications) == 1
        assert result.publications[0].recommendation != ''

    def test_process_update_existing_habit(self, engine, sample_request, sample_context):
        engine.process(sample_request, sample_context)
        ctx2 = dict(sample_context)
        ctx2['observation_frequency'] = 0.9
        result = engine.process(sample_request, ctx2)
        assert len(result.habit.version_history) >= 1

    def test_get_habit(self, engine, sample_request):
        engine.process(sample_request)
        habit = engine.get_habit('habit-001')
        assert habit is not None
        assert habit.habit_id == 'habit-001'

    def test_get_habit_not_found(self, engine):
        assert engine.get_habit('nonexistent') is None

    def test_list_habits(self, engine, sample_request):
        engine.process(sample_request)
        habits = engine.list_habits()
        assert len(habits) == 1

    def test_validate_lifecycle_transition_valid(self, engine):
        assert engine.validate_lifecycle_transition(
            'proposed', 'initiated',
        )
        assert engine.validate_lifecycle_transition(
            'stable', 'weakening',
        )

    def test_validate_lifecycle_transition_invalid(self, engine):
        assert not engine.validate_lifecycle_transition(
            'proposed', 'stable',
        )
        assert not engine.validate_lifecycle_transition(
            'retired', 'initiated',
        )

    def test_process_invalid_status_defaults(self, engine):
        request = {
            'habit_id': 'habit-002',
            'current_status': 'invalid_status',
        }
        result = engine.process(request)
        assert result.habit.current_status == 'proposed'


# ---------------------------------------------------------------------------
# Tests: Ecology
# ---------------------------------------------------------------------------


class TestHabitEcology:
    def test_init(self):
        eco = HabitEcology()
        assert eco._relations == {}

    def test_register_relation(self):
        eco = HabitEcology()
        rel = eco.register_relation('h1', 'h2', 'supportive', 0.7)
        assert rel.relation_type == 'supportive'
        assert rel.strength == 0.7

    def test_register_invalid_type_defaults(self):
        eco = HabitEcology()
        rel = eco.register_relation('h1', 'h2', 'invalid', 0.5)
        assert rel.relation_type == 'neutral'

    def test_get_relations_for_habit(self):
        eco = HabitEcology()
        eco.register_relation('h1', 'h2', 'supportive')
        eco.register_relation('h1', 'h3', 'competing')
        eco.register_relation('h2', 'h3', 'neutral')
        rels = eco.get_relations_for_habit('h1')
        assert len(rels) == 2

    def test_get_relation(self):
        eco = HabitEcology()
        rel = eco.register_relation('h1', 'h2', 'supportive')
        found = eco.get_relation(rel.relation_id)
        assert found is not None

    def test_find_competitors(self):
        eco = HabitEcology()
        eco.register_relation('h1', 'h2', 'competing')
        eco.register_relation('h1', 'h3', 'supportive')
        competitors = eco.find_competitors('h1')
        assert 'h2' in competitors
        assert 'h3' not in competitors

    def test_find_supporters(self):
        eco = HabitEcology()
        eco.register_relation('h1', 'h2', 'supportive')
        eco.register_relation('h1', 'h3', 'mutually_reinforcing')
        eco.register_relation('h1', 'h4', 'competing')
        supporters = eco.find_supporters('h1')
        assert 'h2' in supporters
        assert 'h3' in supporters
        assert 'h4' not in supporters

    def test_find_resource_sharers(self):
        eco = HabitEcology()
        eco.register_relation('h1', 'h2', 'resource_sharing')
        eco.register_relation('h1', 'h3', 'supportive')
        sharers = eco.find_resource_sharers('h1')
        assert 'h2' in sharers
        assert 'h3' not in sharers

    def test_compute_ecology_score(self):
        eco = HabitEcology()
        eco.register_relation('h1', 'h2', 'supportive', 0.8)
        eco.register_relation('h1', 'h3', 'competing', 0.4)
        eco.register_relation('h1', 'h4', 'neutral', 0.0)
        score = eco.compute_ecology_score('h1')
        assert 'supportive_strength' in score
        assert 'competing_strength' in score
        assert 'net_support' in score
        assert score['net_support'] > 0

    def test_list_all_relations(self):
        eco = HabitEcology()
        eco.register_relation('h1', 'h2', 'supportive')
        eco.register_relation('h2', 'h3', 'competing')
        all_rels = eco.list_all_relations()
        assert len(all_rels) == 2

    def test_remove_relation(self):
        eco = HabitEcology()
        rel = eco.register_relation('h1', 'h2', 'supportive')
        assert eco.remove_relation(rel.relation_id) is True
        assert eco.get_relation(rel.relation_id) is None
        assert len(eco.get_relations_for_habit('h1')) == 0

    def test_remove_nonexistent(self):
        eco = HabitEcology()
        assert eco.remove_relation('nonexistent') is False
