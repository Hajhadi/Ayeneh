"""Tests for the DEC-02 Goal Management Engine."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.dec.goal_management.types import (
    GOAL_CATEGORIES,
    GOAL_HIERARCHY_LEVELS,
    GOAL_LIFECYCLE,
    GoalConflict,
    GoalHierarchy,
    GoalObject,
    GoalResult,
)
from ayeneh.dec.goal_management.engine import GoalManagementEngine
from ayeneh.dec.goal_management.hierarchy import GoalHierarchyManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return GoalManagementEngine()


@pytest.fixture
def sample_goals():
    return [
        {
            'goal_id': 'g1',
            'description': 'Become proficient in AI',
            'category': 'career',
            'priority': 0.8,
            'current_status': 'active',
            'progress': 0.3,
            'confidence': 0.7,
            'associated_projects': ['ai-learning'],
            'supporting_evidence': ['completed course', 'daily practice'],
        },
        {
            'goal_id': 'g2',
            'description': 'Maintain financial stability',
            'category': 'financial',
            'priority': 0.7,
            'current_status': 'active',
            'progress': 0.5,
            'confidence': 0.8,
            'associated_projects': ['budget-tracking'],
        },
        {
            'goal_id': 'g3',
            'description': 'Build meaningful relationships',
            'category': 'relationship',
            'priority': 0.6,
            'current_status': 'planned',
            'progress': 0.1,
            'confidence': 0.5,
            'parent_goal': 'g1',
        },
    ]


@pytest.fixture
def sample_context():
    return {
        'active_projects': ['ai-learning', 'budget-tracking'],
        'available_resources': ['time', 'money'],
        'time_horizon': 'quarterly',
        'current_values': ['growth', 'stability'],
    }


@pytest.fixture
def hierarchy_manager():
    return GoalHierarchyManager()


@pytest.fixture
def sample_hierarchy():
    return GoalHierarchy(
        root_goals=('g1', 'g2'),
        parent_map={'g3': 'g1'},
        children_map={'g1': ('g3',)},
        level_map={
            'g1': 'domain_goal',
            'g2': 'domain_goal',
            'g3': 'project_goal',
        },
    )


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestGoalTypes:
    """Tests for DEC-02 type definitions."""

    def test_goal_categories_count(self):
        assert len(GOAL_CATEGORIES) == 10

    def test_goal_lifecycle_count(self):
        assert len(GOAL_LIFECYCLE) == 8

    def test_goal_hierarchy_levels_count(self):
        assert len(GOAL_HIERARCHY_LEVELS) == 6

    def test_goal_object_creation(self):
        obj = GoalObject(goal_id='g-1')
        assert obj.goal_id == 'g-1'
        assert obj.current_status == 'proposed'
        assert obj.creation_timestamp is not None

    def test_goal_object_frozen(self):
        obj = GoalObject(goal_id='g-1')
        with pytest.raises(AttributeError):
            obj.goal_id = 'changed'  # type: ignore[misc]

    def test_goal_hierarchy_defaults(self):
        h = GoalHierarchy()
        assert h.root_goals == ()
        assert h.parent_map == {}

    def test_goal_conflict_creation(self):
        c = GoalConflict(
            conflict_id='c-1',
            goal_a='g1',
            goal_b='g2',
            conflict_type='resource',
            severity=0.6,
        )
        assert c.severity == 0.6

    def test_goal_result_defaults(self):
        r = GoalResult()
        assert r.goals == ()
        assert r.conflicts == ()


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestGoalManagementEngine:
    """Tests for the DEC-02 GoalManagementEngine."""

    def test_engine_initialization(self):
        engine = GoalManagementEngine()
        assert engine._goals == {}

    def test_engine_with_ai_router(self):
        router = {'provider': 'test'}
        engine = GoalManagementEngine(ai_router=router)
        assert engine._ai_router == router

    def test_process_empty(self, engine):
        result = engine.process()
        assert isinstance(result, GoalResult)
        assert result.goals == ()

    def test_process_with_goals(self, engine, sample_goals):
        result = engine.process(existing_goals=sample_goals)
        assert isinstance(result, GoalResult)
        assert len(result.goals) == 3

    def test_process_with_context(
        self, engine, sample_goals, sample_context,
    ):
        result = engine.process(
            context=sample_context,
            existing_goals=sample_goals,
        )
        assert isinstance(result, GoalResult)

    def test_process_produces_hierarchy(
        self, engine, sample_goals,
    ):
        result = engine.process(existing_goals=sample_goals)
        assert isinstance(result.hierarchy, GoalHierarchy)
        assert len(result.hierarchy.level_map) == 3

    def test_process_detects_conflicts(
        self, engine, sample_goals,
    ):
        result = engine.process(existing_goals=sample_goals)
        assert isinstance(result.conflicts, tuple)

    def test_process_prioritizes_goals(
        self, engine, sample_goals,
    ):
        result = engine.process(existing_goals=sample_goals)
        assert len(result.priority_ranking) == 3
        # g1 has highest priority (0.8)
        assert result.priority_ranking[0] == 'g1'

    def test_process_produces_revision_suggestions(
        self, engine, sample_goals,
    ):
        result = engine.process(existing_goals=sample_goals)
        assert isinstance(result.revision_suggestions, tuple)

    def test_process_produces_planning_interface(
        self, engine, sample_goals,
    ):
        result = engine.process(existing_goals=sample_goals)
        assert 'active_count' in result.planning_interface
        assert 'ready_for_planning' in result.planning_interface

    def test_process_produces_processing_metadata(
        self, engine, sample_goals,
    ):
        result = engine.process(existing_goals=sample_goals)
        assert 'total_goals' in result.processing_metadata
        assert 'conflict_count' in result.processing_metadata

    def test_get_goal(self, engine, sample_goals):
        engine.process(existing_goals=sample_goals)
        goal = engine.get_goal('g1')
        assert goal is not None
        assert goal.goal_id == 'g1'

    def test_get_goal_not_found(self, engine):
        assert engine.get_goal('nonexistent') is None

    def test_get_all_goals(self, engine, sample_goals):
        engine.process(existing_goals=sample_goals)
        all_goals = engine.get_all_goals()
        assert len(all_goals) == 3

    def test_process_deterministic(self, engine, sample_goals):
        r1 = engine.process(existing_goals=sample_goals)
        r2 = engine.process(existing_goals=sample_goals)
        assert len(r1.goals) == len(r2.goals)

    def test_process_single_goal(self, engine):
        goals = [{'goal_id': 'g1', 'description': 'Test', 'priority': 0.5}]
        result = engine.process(existing_goals=goals)
        assert len(result.goals) == 1
        assert result.priority_ranking == ('g1',)


# ---------------------------------------------------------------------------
# Hierarchy manager tests
# ---------------------------------------------------------------------------


class TestGoalHierarchyManager:
    """Tests for the DEC-02 GoalHierarchyManager."""

    def test_load(self, hierarchy_manager, sample_hierarchy):
        hierarchy_manager.load(sample_hierarchy)
        assert len(hierarchy_manager._hierarchy.root_goals) == 2

    def test_validate_valid(self, hierarchy_manager, sample_hierarchy):
        hierarchy_manager.load(sample_hierarchy)
        errors = hierarchy_manager.validate()
        assert len(errors) == 0

    def test_validate_invalid_parent(self, hierarchy_manager):
        h = GoalHierarchy(
            root_goals=('g1',),
            parent_map={'g2': 'g1', 'g3': 'g1'},
            children_map={'g1': ('g2', 'g3')},
            level_map={'g1': 'domain_goal', 'g2': 'project_goal', 'g3': 'task'},
        )
        hierarchy_manager.load(h)
        errors = hierarchy_manager.validate()
        # g3 is 'task' under g1 which is 'domain_goal' — skips 'project_goal' and 'milestone'
        assert len(errors) > 0

    def test_get_ancestors(self, hierarchy_manager, sample_hierarchy):
        hierarchy_manager.load(sample_hierarchy)
        ancestors = hierarchy_manager.get_ancestors('g3')
        assert 'g1' in ancestors

    def test_get_ancestors_root(self, hierarchy_manager, sample_hierarchy):
        hierarchy_manager.load(sample_hierarchy)
        ancestors = hierarchy_manager.get_ancestors('g1')
        assert ancestors == ()

    def test_get_descendants(self, hierarchy_manager, sample_hierarchy):
        hierarchy_manager.load(sample_hierarchy)
        descendants = hierarchy_manager.get_descendants('g1')
        assert 'g3' in descendants

    def test_get_descendants_leaf(self, hierarchy_manager, sample_hierarchy):
        hierarchy_manager.load(sample_hierarchy)
        descendants = hierarchy_manager.get_descendants('g3')
        assert descendants == ()

    def test_get_depth(self, hierarchy_manager, sample_hierarchy):
        hierarchy_manager.load(sample_hierarchy)
        assert hierarchy_manager.get_depth('g1') == 0
        assert hierarchy_manager.get_depth('g3') == 1

    def test_get_goals_at_level(self, hierarchy_manager, sample_hierarchy):
        hierarchy_manager.load(sample_hierarchy)
        domain_goals = hierarchy_manager.get_goals_at_level('domain_goal')
        assert 'g1' in domain_goals
        assert 'g2' in domain_goals

    def test_get_level_counts(self, hierarchy_manager, sample_hierarchy):
        hierarchy_manager.load(sample_hierarchy)
        counts = hierarchy_manager.get_level_counts()
        assert counts['domain_goal'] == 2
        assert counts['project_goal'] == 1

    def test_get_max_depth(self, hierarchy_manager, sample_hierarchy):
        hierarchy_manager.load(sample_hierarchy)
        assert hierarchy_manager.get_max_depth() >= 1

    def test_get_path(self, hierarchy_manager, sample_hierarchy):
        hierarchy_manager.load(sample_hierarchy)
        path = hierarchy_manager.get_path('g3', 'g1')
        assert 'g3' in path
        assert 'g1' in path
