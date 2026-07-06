"""Tests for the ACT-01 Execution Monitoring Engine."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.act.execution_monitoring.types import (
    DEVIATION_SEVERITY_LEVELS,
    EXECUTION_STATES,
    RESOURCE_CATEGORIES,
    VALID_STATE_TRANSITIONS,
    BehavioralFeedback,
    DeviationRecord,
    ExecutionObject,
    ExecutionProgress,
    ExecutionResult,
    ExecutionSnapshot,
    ResourceConsumption,
)
from ayeneh.act.execution_monitoring.engine import ExecutionMonitoringEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return ExecutionMonitoringEngine()


@pytest.fixture
def sample_request():
    return {
        'execution_id': 'exec-001',
        'associated_plan': 'plan-001',
        'associated_goal': 'goal-001',
        'current_state': 'prepared',
    }


@pytest.fixture
def sample_context():
    return {
        'progress_ratio': 0.3,
        'milestones_achieved': ('m1',),
        'milestones_pending': ('m2', 'm3'),
        'quality_score': 0.8,
        'velocity': 0.5,
        'consumed_resources': {'time': 2.0, 'cognitive_effort': 1.5},
        'resource_allocations': {
            'time': 10.0, 'cognitive_effort': 8.0,
            'emotional_energy': 5.0, 'social_capital': 3.0,
            'financial': 1.0, 'informational': 4.0,
        },
        'new_deviations': [
            {
                'deviation_id': 'dev-001',
                'deviation_type': 'schedule',
                'severity': 'minor',
                'description': 'Slight delay',
            },
        ],
        'executed_deviations': [],
    }


# ---------------------------------------------------------------------------
# Tests: Types
# ---------------------------------------------------------------------------


class TestExecutionStates:
    def test_states_list_completeness(self):
        assert len(EXECUTION_STATES) == 9
        assert 'prepared' in EXECUTION_STATES
        assert 'archived' in EXECUTION_STATES

    def test_all_states_have_transitions(self):
        for state in EXECUTION_STATES:
            assert state in VALID_STATE_TRANSITIONS

    def test_terminal_states(self):
        assert VALID_STATE_TRANSITIONS['archived'] == []
        assert VALID_STATE_TRANSITIONS['completed'] == ['archived']

    def test_deviation_severity_levels(self):
        assert len(DEVIATION_SEVERITY_LEVELS) == 5
        assert 'negligible' in DEVIATION_SEVERITY_LEVELS
        assert 'critical' in DEVIATION_SEVERITY_LEVELS

    def test_resource_categories(self):
        assert len(RESOURCE_CATEGORIES) == 6
        assert 'time' in RESOURCE_CATEGORIES
        assert 'cognitive_effort' in RESOURCE_CATEGORIES


class TestExecutionObject:
    def test_default_values(self):
        obj = ExecutionObject(execution_id='e1')
        assert obj.execution_id == 'e1'
        assert obj.current_state == 'prepared'
        assert obj.observed_progress == 0.0
        assert obj.execution_confidence == 0.0
        assert obj.risk_level == 0.0
        assert obj.detected_deviations == ()
        assert obj.version_history == ()

    def test_frozen_dataclass(self):
        obj = ExecutionObject(execution_id='e1')
        with pytest.raises(AttributeError):
            obj.execution_id = 'e2'

    def test_custom_values(self):
        obj = ExecutionObject(
            execution_id='e1',
            associated_plan='p1',
            associated_goal='g1',
            current_state='running',
            observed_progress=0.5,
            execution_confidence=0.8,
            risk_level=0.3,
        )
        assert obj.associated_plan == 'p1'
        assert obj.current_state == 'running'
        assert obj.observed_progress == 0.5


class TestDeviationRecord:
    def test_creation(self):
        d = DeviationRecord(
            deviation_id='d1',
            deviation_type='schedule',
            severity='minor',
            description='Test deviation',
        )
        assert d.deviation_id == 'd1'
        assert d.severity == 'minor'

    def test_frozen(self):
        d = DeviationRecord(deviation_id='d1')
        with pytest.raises(AttributeError):
            d.deviation_id = 'd2'


class TestResourceConsumption:
    def test_creation(self):
        r = ResourceConsumption(
            resource_type='time',
            allocated=10.0,
            consumed=3.0,
            remaining=7.0,
            efficiency=0.3,
        )
        assert r.allocated == 10.0
        assert r.remaining == 7.0


class TestExecutionProgress:
    def test_creation(self):
        p = ExecutionProgress(
            progress_id='p1',
            completion_ratio=0.5,
        )
        assert p.completion_ratio == 0.5
        assert p.quality_score == 0.0


class TestBehavioralFeedback:
    def test_creation(self):
        f = BehavioralFeedback(
            feedback_id='f1',
            feedback_type='warning',
            message='Test',
            severity='warning',
            actionable=True,
        )
        assert f.actionable is True
        assert f.feedback_type == 'warning'


class TestExecutionSnapshot:
    def test_creation(self):
        s = ExecutionSnapshot(
            snapshot_id='s1',
            state='running',
            progress=0.5,
        )
        assert s.state == 'running'


class TestExecutionResult:
    def test_creation(self):
        obj = ExecutionObject(execution_id='e1')
        r = ExecutionResult(execution=obj)
        assert r.execution.execution_id == 'e1'
        assert r.deviations_detected == ()
        assert r.pipeline_phases_completed == ()


# ---------------------------------------------------------------------------
# Tests: Engine
# ---------------------------------------------------------------------------


class TestExecutionMonitoringEngine:
    def test_init(self, engine):
        assert engine._executions == {}

    def test_process_basic(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert isinstance(result, ExecutionResult)
        assert result.execution.execution_id == 'exec-001'
        assert len(result.pipeline_phases_completed) == 7

    def test_process_creates_execution(self, engine, sample_request):
        result = engine.process(sample_request)
        assert 'exec-001' in engine._executions

    def test_process_default_state(self, engine, sample_request):
        result = engine.process(sample_request)
        assert result.execution.current_state == 'prepared'

    def test_process_progress_observed(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert result.execution.observed_progress == 0.3

    def test_process_deviations_detected(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert len(result.deviations_detected) >= 1

    def test_process_resources_tracked(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert len(result.resource_report) == 6

    def test_process_feedback_generated(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert len(result.feedback) >= 1

    def test_process_state_transition(self, engine):
        request = {
            'execution_id': 'exec-002',
            'current_state': 'initialized',
        }
        context = {'target_state': 'running'}
        result = engine.process(request, context)
        assert 'initialized->running' == result.state_transition

    def test_process_invalid_state_transition(self, engine):
        request = {
            'execution_id': 'exec-003',
            'current_state': 'prepared',
        }
        context = {'target_state': 'completed'}
        result = engine.process(request, context)
        assert 'prepared->prepared' == result.state_transition

    def test_process_critical_deviations_block(self, engine):
        request = {
            'execution_id': 'exec-004',
            'current_state': 'running',
        }
        context = {
            'new_deviations': [
                {'severity': 'critical', 'description': 'Major issue'},
                {'severity': 'critical', 'description': 'Another issue'},
            ],
        }
        result = engine.process(request, context)
        assert result.execution.current_state == 'blocked'

    def test_process_completion_feedback(self, engine):
        request = {'execution_id': 'exec-005'}
        context = {'progress_ratio': 1.0}
        result = engine.process(request, context)
        types = [f.feedback_type for f in result.feedback]
        assert 'celebration' in types

    def test_get_execution(self, engine, sample_request):
        engine.process(sample_request)
        exec_obj = engine.get_execution('exec-001')
        assert exec_obj is not None
        assert exec_obj.execution_id == 'exec-001'

    def test_get_execution_not_found(self, engine):
        assert engine.get_execution('nonexistent') is None

    def test_list_executions(self, engine, sample_request):
        engine.process(sample_request)
        executions = engine.list_executions()
        assert len(executions) == 1

    def test_validate_state_transition_valid(self, engine):
        assert engine.validate_state_transition('prepared', 'initialized')
        assert engine.validate_state_transition('running', 'completed')

    def test_validate_state_transition_invalid(self, engine):
        assert not engine.validate_state_transition('prepared', 'completed')
        assert not engine.validate_state_transition('archived', 'running')

    def test_version_history_updated(self, engine):
        request = {
            'execution_id': 'exec-006',
            'current_state': 'initialized',
        }
        context = {'target_state': 'running'}
        engine.process(request, context)
        exec_obj = engine.get_execution('exec-006')
        assert len(exec_obj.version_history) >= 1
