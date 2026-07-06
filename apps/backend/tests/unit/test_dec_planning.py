"""Tests for the DEC-03 Planning Engine."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.dec.planning.types import (
    DEPENDENCY_TYPES,
    PLAN_LIFECYCLE,
    PLANNING_HORIZONS,
    TASK_STATUSES,
    PlanObject,
    PlanResult,
    PlanRiskAssessment,
    ScheduleSlot,
    TaskDependency,
)
from ayeneh.dec.planning.engine import PlanningEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return PlanningEngine()


@pytest.fixture
def sample_goal():
    return {
        'goal_id': 'g1',
        'description': 'Build a personal website',
        'priority': 0.7,
        'associated_values': ['creativity', 'self-expression'],
    }


@pytest.fixture
def sample_context():
    return {
        'planning_horizon': 'weekly',
        'time_constraints': ['Available evenings only'],
        'resource_constraints': ['Limited to 10 hours per week'],
    }


@pytest.fixture
def sample_tasks():
    return [
        {
            'task_id': 't1',
            'name': 'Design wireframes',
            'description': 'Create initial wireframes',
            'estimated_hours': 3.0,
            'priority': 0.8,
        },
        {
            'task_id': 't2',
            'name': 'Implement frontend',
            'description': 'Build the HTML/CSS/JS',
            'estimated_hours': 8.0,
            'priority': 0.7,
            'dependencies': ['t1'],
        },
        {
            'task_id': 't3',
            'name': 'Deploy',
            'description': 'Deploy to hosting',
            'estimated_hours': 1.0,
            'priority': 0.6,
            'dependencies': ['t2'],
        },
    ]


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestPlanningTypes:
    """Tests for DEC-03 type definitions."""

    def test_planning_horizons_count(self):
        assert len(PLANNING_HORIZONS) == 6

    def test_dependency_types_count(self):
        assert len(DEPENDENCY_TYPES) == 5

    def test_task_statuses_count(self):
        assert len(TASK_STATUSES) == 6

    def test_plan_lifecycle_count(self):
        assert len(PLAN_LIFECYCLE) == 6

    def test_plan_object_creation(self):
        obj = PlanObject(plan_id='p-1')
        assert obj.plan_id == 'p-1'
        assert obj.planning_horizon == 'daily'
        assert obj.creation_timestamp is not None

    def test_plan_object_frozen(self):
        obj = PlanObject(plan_id='p-1')
        with pytest.raises(AttributeError):
            obj.plan_id = 'changed'  # type: ignore[misc]

    def test_plan_result_defaults(self):
        r = PlanResult()
        assert r.plan.plan_id == ''
        assert r.schedule == ()
        assert r.critical_path == ()

    def test_schedule_slot_creation(self):
        s = ScheduleSlot(
            slot_id='s-1',
            task_id='t-1',
            start_offset_hours=0.0,
            duration_hours=2.0,
        )
        assert s.duration_hours == 2.0

    def test_task_dependency_creation(self):
        d = TaskDependency(
            dependency_id='d-1',
            source_task='t1',
            target_task='t2',
            dependency_type='sequential',
        )
        assert d.dependency_type == 'sequential'

    def test_plan_risk_assessment_creation(self):
        r = PlanRiskAssessment(
            risk_id='r-1',
            description='Scope creep',
            probability=0.4,
            impact=0.6,
        )
        assert r.probability == 0.4


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestPlanningEngine:
    """Tests for the DEC-03 PlanningEngine."""

    def test_engine_initialization(self):
        engine = PlanningEngine()
        assert engine._plans == {}

    def test_engine_with_ai_router(self):
        router = {'provider': 'test'}
        engine = PlanningEngine(ai_router=router)
        assert engine._ai_router == router

    def test_process_basic(self, engine, sample_goal):
        result = engine.process(sample_goal)
        assert isinstance(result, PlanResult)
        assert result.plan.associated_goal == 'g1'

    def test_process_with_context(
        self, engine, sample_goal, sample_context,
    ):
        result = engine.process(sample_goal, context=sample_context)
        assert isinstance(result, PlanResult)
        assert result.plan.planning_horizon == 'weekly'

    def test_process_with_tasks(
        self, engine, sample_goal, sample_tasks,
    ):
        result = engine.process(
            sample_goal, existing_tasks=sample_tasks,
        )
        assert isinstance(result, PlanResult)
        assert len(result.plan.tasks) == 3

    def test_process_full(
        self, engine, sample_goal, sample_context, sample_tasks,
    ):
        result = engine.process(
            sample_goal,
            context=sample_context,
            existing_tasks=sample_tasks,
        )
        assert isinstance(result, PlanResult)
        assert len(result.plan.milestones) > 0
        assert len(result.schedule) > 0
        assert result.plan.estimated_duration > 0

    def test_process_produces_milestones(
        self, engine, sample_goal,
    ):
        result = engine.process(sample_goal)
        assert len(result.plan.milestones) >= 3

    def test_process_produces_schedule(
        self, engine, sample_goal,
    ):
        result = engine.process(sample_goal)
        assert len(result.schedule) > 0
        for slot in result.schedule:
            assert isinstance(slot, ScheduleSlot)

    def test_process_produces_risks(
        self, engine, sample_goal,
    ):
        result = engine.process(sample_goal)
        assert isinstance(result.risks, tuple)

    def test_process_produces_critical_path(
        self, engine, sample_goal,
    ):
        result = engine.process(sample_goal)
        assert isinstance(result.critical_path, tuple)

    def test_process_produces_summary(
        self, engine, sample_goal,
    ):
        result = engine.process(sample_goal)
        assert result.summary != ''
        assert 'Build a personal website' in result.summary

    def test_process_produces_processing_metadata(
        self, engine, sample_goal,
    ):
        result = engine.process(sample_goal)
        assert 'task_count' in result.processing_metadata
        assert 'milestone_count' in result.processing_metadata
        assert 'total_duration' in result.processing_metadata

    def test_process_estimated_duration(
        self, engine, sample_goal, sample_tasks,
    ):
        result = engine.process(
            sample_goal, existing_tasks=sample_tasks,
        )
        assert result.plan.estimated_duration == 12.0

    def test_process_dependencies(
        self, engine, sample_goal, sample_tasks,
    ):
        result = engine.process(
            sample_goal, existing_tasks=sample_tasks,
        )
        assert len(result.plan.dependencies) > 0

    def test_get_plan(self, engine, sample_goal):
        result = engine.process(sample_goal)
        plan_id = result.plan.plan_id
        retrieved = engine.get_plan(plan_id)
        assert retrieved is not None
        assert retrieved.plan_id == plan_id

    def test_get_plan_not_found(self, engine):
        assert engine.get_plan('nonexistent') is None

    def test_get_all_plans(self, engine, sample_goal):
        engine.process(sample_goal)
        all_plans = engine.get_all_plans()
        assert len(all_plans) >= 1

    def test_process_deterministic(self, engine, sample_goal):
        r1 = engine.process(sample_goal)
        r2 = engine.process(sample_goal)
        assert r1.plan.associated_goal == r2.plan.associated_goal
        assert r1.plan.estimated_duration == r2.plan.estimated_duration

    def test_process_no_tasks(self, engine, sample_goal):
        result = engine.process(sample_goal)
        assert isinstance(result, PlanResult)
        assert len(result.plan.tasks) > 0

    def test_process_confidence_range(self, engine, sample_goal):
        result = engine.process(sample_goal)
        assert 0.0 <= result.plan.confidence <= 1.0
