"""Tests for ACT-05 Autonomous Workflow Engine."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.act.autonomous_workflow.types import (
    WORKFLOW_PHASES,
    WORKFLOW_STATUSES,
    WORKFLOW_PRIORITIES,
    DEPENDENCY_TYPES,
    PHASE_VALID_TRANSITIONS,
    AdaptationRecord,
    ExecutionRecord,
    GoalNode,
    MonitoringCheckpoint,
    PlanningStep,
    StrategySelection,
    WorkflowObject,
    WorkflowResult,
)
from ayeneh.act.autonomous_workflow.engine import AutonomousWorkflowEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return AutonomousWorkflowEngine()


@pytest.fixture
def sample_goals():
    return [
        {
            'node_id': 'goal-1',
            'description': 'Complete daily reading',
            'priority': 0.8,
        },
        {
            'node_id': 'goal-2',
            'description': 'Review patterns',
            'priority': 0.5,
        },
    ]


@pytest.fixture
def sample_context():
    return {
        'workflow_id': 'wf-test-1',
        'dependencies': [{'type': 'blocking', 'target': 'goal-2'}],
        'responsible_modules': ['execution_monitoring', 'habit_formation'],
        'priority': 0.7,
    }


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestWorkflowTypes:
    """Tests for ACT-05 type definitions."""

    def test_workflow_phases_count(self):
        assert len(WORKFLOW_PHASES) == 8

    def test_workflow_phases_include_expected(self):
        expected = {
            'initialization', 'preparation', 'execution', 'monitoring',
            'adaptation', 'completion', 'maintenance', 'archival',
        }
        assert set(WORKFLOW_PHASES) == expected

    def test_workflow_statuses_count(self):
        assert len(WORKFLOW_STATUSES) == 6

    def test_workflow_priorities_count(self):
        assert len(WORKFLOW_PRIORITIES) == 5

    def test_dependency_types_count(self):
        assert len(DEPENDENCY_TYPES) == 5

    def test_phase_valid_transitions_covers_all_phases(self):
        for phase in WORKFLOW_PHASES:
            assert phase in PHASE_VALID_TRANSITIONS

    def test_archival_is_terminal(self):
        assert PHASE_VALID_TRANSITIONS['archival'] == []


class TestWorkflowDataclasses:
    """Tests for ACT-05 frozen dataclasses."""

    def test_goal_node_creation(self):
        node = GoalNode(node_id='g-1', goal_description='Test goal')
        assert node.node_id == 'g-1'
        assert node.goal_description == 'Test goal'
        assert node.priority == 0.0
        assert node.status == 'pending'

    def test_goal_node_immutability(self):
        node = GoalNode(node_id='g-1')
        with pytest.raises(AttributeError):
            node.node_id = 'g-2'  # type: ignore[misc]

    def test_strategy_selection_creation(self):
        ss = StrategySelection(selection_id='ss-1', strategy_name='balanced')
        assert ss.selection_id == 'ss-1'
        assert ss.confidence == 0.0
        assert ss.alternatives == ()

    def test_planning_step_creation(self):
        ps = PlanningStep(step_id='ps-1', description='Do something', order=0)
        assert ps.step_id == 'ps-1'
        assert ps.status == 'pending'
        assert ps.estimated_duration_ms == 0.0

    def test_execution_record_creation(self):
        er = ExecutionRecord(record_id='er-1', step_id='ps-1', status='completed')
        assert er.record_id == 'er-1'
        assert er.status == 'completed'
        assert er.error == ''

    def test_monitoring_checkpoint_creation(self):
        mc = MonitoringCheckpoint(checkpoint_id='mc-1', progress=0.5)
        assert mc.checkpoint_id == 'mc-1'
        assert mc.health_status == 'healthy'
        assert mc.alerts == ()

    def test_adaptation_record_creation(self):
        ar = AdaptationRecord(adaptation_id='ar-1', trigger='test')
        assert ar.adaptation_id == 'ar-1'
        assert ar.previous_state == ''
        assert ar.new_state == ''

    def test_workflow_object_creation(self):
        wf = WorkflowObject(workflow_id='wf-1')
        assert wf.workflow_id == 'wf-1'
        assert wf.current_phase == 'initialization'
        assert wf.current_status == 'active'
        assert wf.priority == 0.0
        assert wf.progress == 0.0
        assert wf.confidence == 0.0

    def test_workflow_object_immutability(self):
        wf = WorkflowObject(workflow_id='wf-1')
        with pytest.raises(AttributeError):
            wf.workflow_id = 'wf-2'  # type: ignore[misc]

    def test_workflow_object_defaults(self):
        wf = WorkflowObject(workflow_id='wf-1')
        assert wf.associated_goals == ()
        assert wf.associated_plans == ()
        assert wf.execution_history == ()
        assert wf.dependencies == ()
        assert wf.responsible_modules == ()
        assert wf.version_history == ()
        assert isinstance(wf.creation_timestamp, datetime)
        assert wf.explainability_metadata == {}

    def test_workflow_result_creation(self):
        wf = WorkflowObject(workflow_id='wf-1')
        wr = WorkflowResult(workflow=wf)
        assert wr.workflow.workflow_id == 'wf-1'
        assert wr.goal_graph == ()
        assert wr.strategy_selections == ()
        assert wr.planning_steps == ()
        assert wr.execution_records == ()
        assert wr.monitoring_checkpoints == ()
        assert wr.adaptations == ()
        assert wr.pipeline_phases_completed == ()


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestAutonomousWorkflowEngine:
    """Tests for ACT-05 AutonomousWorkflowEngine."""

    def test_process_empty_request(self, engine):
        result = engine.process([])
        assert isinstance(result, WorkflowResult)
        assert len(result.pipeline_phases_completed) == 7

    def test_process_with_goals(self, engine, sample_goals):
        result = engine.process(sample_goals)
        assert len(result.goal_graph) == 2
        assert result.goal_graph[0].goal_description == 'Complete daily reading'

    def test_process_phases_order(self, engine):
        result = engine.process([])
        expected_phases = (
            'GoalGraph',
            'StrategySelection',
            'Planning',
            'Execution',
            'Monitoring',
            'Feedback',
            'Adaptation',
        )
        assert result.pipeline_phases_completed == expected_phases

    def test_process_generates_strategies(self, engine, sample_goals):
        result = engine.process(sample_goals)
        assert len(result.strategy_selections) == 2

    def test_process_generates_planning_steps(self, engine, sample_goals):
        result = engine.process(sample_goals)
        assert len(result.planning_steps) == 2

    def test_process_generates_execution_records(self, engine, sample_goals):
        result = engine.process(sample_goals)
        assert len(result.execution_records) == 2

    def test_process_generates_monitoring_checkpoints(self, engine, sample_goals):
        result = engine.process(sample_goals)
        assert len(result.monitoring_checkpoints) >= 1

    def test_process_with_context(self, engine, sample_goals, sample_context):
        result = engine.process(sample_goals, context=sample_context)
        assert result.workflow.workflow_id == 'wf-test-1'
        assert result.workflow.priority == 0.7

    def test_process_workflow_progress(self, engine, sample_goals):
        result = engine.process(sample_goals)
        assert 0.0 <= result.workflow.progress <= 1.0

    def test_process_workflow_confidence(self, engine, sample_goals):
        result = engine.process(sample_goals)
        assert 0.0 <= result.workflow.confidence <= 1.0

    def test_process_default_goal(self, engine):
        ctx = {'default_goal': 'auto-generated goal'}
        result = engine.process([], context=ctx)
        assert len(result.goal_graph) == 1
        assert result.goal_graph[0].goal_description == 'auto-generated goal'

    def test_process_with_raw_strategy_selections(self, engine):
        ctx = {
            'strategy_selections': [
                {
                    'selection_id': 'ss-raw-1',
                    'strategy_name': 'custom',
                    'confidence': 0.9,
                },
            ],
        }
        result = engine.process([], context=ctx)
        assert len(result.strategy_selections) >= 1

    def test_process_with_raw_planning_steps(self, engine):
        ctx = {
            'planning_steps': [
                {
                    'step_id': 'ps-raw-1',
                    'description': 'Custom step',
                    'order': 99,
                },
            ],
        }
        result = engine.process([], context=ctx)
        assert len(result.planning_steps) >= 1

    def test_process_with_raw_execution_records(self, engine):
        now = datetime.now(UTC).isoformat()
        ctx = {
            'execution_records': [
                {
                    'record_id': 'er-raw-1',
                    'step_id': 'ps-1',
                    'started_at': now,
                    'completed_at': now,
                    'status': 'completed',
                    'confidence': 0.8,
                },
            ],
        }
        result = engine.process([], context=ctx)
        assert len(result.execution_records) >= 1

    def test_process_with_raw_monitoring_checkpoints(self, engine):
        ctx = {
            'monitoring_checkpoints': [
                {
                    'checkpoint_id': 'mc-raw-1',
                    'phase': 'execution',
                    'progress': 0.5,
                    'health_status': 'healthy',
                },
            ],
        }
        result = engine.process([], context=ctx)
        assert len(result.monitoring_checkpoints) >= 1

    def test_process_with_raw_adaptations(self, engine):
        ctx = {
            'adaptations': [
                {
                    'adaptation_id': 'ar-raw-1',
                    'trigger': 'manual',
                    'previous_state': 'executing',
                    'new_state': 'completed',
                    'confidence': 0.9,
                },
            ],
        }
        result = engine.process([], context=ctx)
        assert len(result.adaptations) >= 1

    def test_list_workflows(self, engine):
        result = engine.list_workflows()
        assert isinstance(result, list)
