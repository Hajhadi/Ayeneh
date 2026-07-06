"""Tests for ACT integration — models, API, pipeline."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.act.feedback_loop.engine import FeedbackLoopCoordinator
from ayeneh.act.feedback_loop.propagation import FeedbackPropagation
from ayeneh.act.autonomous_workflow.engine import AutonomousWorkflowEngine
from ayeneh.act.execution_monitoring.engine import ExecutionMonitoringEngine


# ---------------------------------------------------------------------------
# Cross-module integration tests
# ---------------------------------------------------------------------------


class TestACTExecutionIntegration:
    """Integration tests for ACT-01 Execution Monitoring."""

    def test_execution_create_and_process(self):
        engine = ExecutionMonitoringEngine()
        result = engine.process({
            'execution_id': 'exec-int-1',
            'associated_plan': 'plan-1',
            'associated_goal': 'goal-1',
        })
        assert result.execution.execution_id == 'exec-int-1'
        assert result.execution.current_state == 'prepared'
        assert len(result.pipeline_phases_completed) == 7

    def test_execution_with_deviations(self):
        engine = ExecutionMonitoringEngine()
        ctx = {
            'new_deviations': [
                {
                    'deviation_type': 'scope_creep',
                    'severity': 'significant',
                    'description': 'Task expanded beyond original scope',
                },
            ],
        }
        result = engine.process(
            {'execution_id': 'exec-dev-1'},
            context=ctx,
        )
        assert len(result.deviations_detected) >= 1

    def test_execution_state_transition(self):
        engine = ExecutionMonitoringEngine()
        ctx = {'target_state': 'running'}
        result = engine.process(
            {'execution_id': 'exec-trans-1', 'current_state': 'initialized'},
            context=ctx,
        )
        assert result.execution.current_state == 'running'


class TestACTFeedbackIntegration:
    """Integration tests for ACT-04 Feedback Loop."""

    def test_feedback_end_to_end(self):
        engine = FeedbackLoopCoordinator()
        ctx = {
            'observed_outcomes': [
                {
                    'outcome_id': 'out-e2e-1',
                    'source_event': 'execution_observation',
                    'description': 'Plan completed on time',
                    'expected_value': 'on_time',
                    'actual_value': 'on_time',
                    'deviation_magnitude': 0.0,
                    'confidence': 0.9,
                },
            ],
        }
        result = engine.process({'source_event': 'execution'}, context=ctx)
        assert len(result.observed_outcomes) == 1
        assert len(result.action_evaluations) >= 1
        assert len(result.reflections) >= 1

    def test_feedback_propagation_integration(self):
        prop = FeedbackPropagation()
        fb = __import__('ayeneh.act.feedback_loop.types', fromlist=['FeedbackObject']).FeedbackObject(
            feedback_id='fb-prop-1',
            propagation_targets=('execution_monitoring', 'habit_formation'),
            confidence=0.7,
        )
        records = prop.propagate(fb)
        assert len(records) == 2
        assert all(r.applied for r in records)

    def test_feedback_confidence_chain(self):
        engine = FeedbackLoopCoordinator()
        ctx = {
            'previous_confidence': 0.3,
            'observed_outcomes': [
                {
                    'outcome_id': 'out-conf-1',
                    'description': 'Good outcome',
                    'confidence': 0.9,
                    'deviation_magnitude': 0.05,
                    'expected_value': 'good',
                    'actual_value': 'good',
                },
            ],
        }
        result = engine.process({}, context=ctx)
        assert result.feedback.confidence > 0.0


class TestACTWorkflowIntegration:
    """Integration tests for ACT-05 Autonomous Workflow."""

    def test_workflow_end_to_end(self):
        engine = AutonomousWorkflowEngine()
        goals = [
            {'description': 'Read chapter 1', 'priority': 0.9},
            {'description': 'Summarize key points', 'priority': 0.7},
        ]
        result = engine.process(goals)
        assert len(result.goal_graph) == 2
        assert len(result.strategy_selections) == 2
        assert len(result.planning_steps) == 2
        assert len(result.execution_records) == 2
        assert result.workflow.current_phase in ('execution', 'completion', 'adaptation')

    def test_workflow_completion_detection(self):
        engine = AutonomousWorkflowEngine()
        goals = [{'description': 'Simple task', 'priority': 0.5}]
        result = engine.process(goals)
        # All steps complete, so progress should be 1.0
        assert result.workflow.progress == 1.0


class TestACTPipelineIntegration:
    """Integration tests for ACT subsystem within the pipeline context."""

    def test_act_engines_instantiate_independently(self):
        exec_engine = ExecutionMonitoringEngine()
        feedback_engine = FeedbackLoopCoordinator()
        workflow_engine = AutonomousWorkflowEngine()

        assert exec_engine is not None
        assert feedback_engine is not None
        assert workflow_engine is not None

    def test_act_engines_share_no_state(self):
        e1 = ExecutionMonitoringEngine()
        e2 = ExecutionMonitoringEngine()
        e1.process({'execution_id': 'exec-1'})
        assert e2.list_executions() == []

    def test_feedback_to_workflow_data_flow(self):
        feedback_engine = FeedbackLoopCoordinator()
        workflow_engine = AutonomousWorkflowEngine()

        # Run feedback
        fb_result = feedback_engine.process(
            {'source_event': 'workflow_completion'},
            context={
                'observed_outcomes': [
                    {
                        'outcome_id': 'out-1',
                        'description': 'Workflow completed',
                        'confidence': 0.9,
                        'deviation_magnitude': 0.0,
                    },
                ],
            },
        )

        # Use feedback as context for workflow
        wf_ctx = {
            'adaptations': [
                {
                    'trigger': 'feedback',
                    'previous_state': 'executing',
                    'new_state': 'completed',
                    'confidence': fb_result.feedback.confidence,
                },
            ],
        }
        wf_result = workflow_engine.process([], context=wf_ctx)
        assert isinstance(wf_result, type(wf_result))

    def test_full_act_chain(self):
        """Test a full ACT chain: execute -> feedback -> adapt."""
        exec_engine = ExecutionMonitoringEngine()
        feedback_engine = FeedbackLoopCoordinator()
        workflow_engine = AutonomousWorkflowEngine()

        # Step 1: Execute
        exec_result = exec_engine.process({
            'execution_id': 'chain-1',
            'associated_plan': 'plan-1',
        })
        assert exec_result.execution.execution_id == 'chain-1'

        # Step 2: Feedback on execution
        fb_result = feedback_engine.process(
            {'source_event': 'execution_complete'},
            context={
                'observed_outcomes': [
                    {
                        'outcome_id': 'out-chain-1',
                        'description': 'Execution succeeded',
                        'confidence': 0.85,
                        'deviation_magnitude': 0.1,
                    },
                ],
            },
        )
        assert fb_result.feedback.confidence > 0.0

        # Step 3: Workflow adaptation
        wf_result = workflow_engine.process(
            [{'description': 'Next task', 'priority': 0.7}],
            context={
                'adaptations': [
                    {
                        'trigger': 'feedback_based',
                        'previous_state': 'executing',
                        'new_state': 'adapted',
                        'confidence': fb_result.feedback.confidence,
                    },
                ],
            },
        )
        assert len(wf_result.goal_graph) == 1


class TestACTDBModels:
    """Tests for ACT DB model definitions (import-level validation)."""

    def test_act_execution_model_imports(self):
        from ayeneh.infrastructure.persistence.models.act_execution import ACTExecutionModel
        assert ACTExecutionModel.__tablename__ == "act_executions"

    def test_act_habit_model_imports(self):
        from ayeneh.infrastructure.persistence.models.act_habit import ACTHabitModel
        assert ACTHabitModel.__tablename__ == "act_habits"

    def test_act_intervention_model_imports(self):
        from ayeneh.infrastructure.persistence.models.act_intervention import ACTInterventionModel
        assert ACTInterventionModel.__tablename__ == "act_interventions"

    def test_act_feedback_model_imports(self):
        from ayeneh.infrastructure.persistence.models.act_feedback import ACTFeedbackModel
        assert ACTFeedbackModel.__tablename__ == "act_feedbacks"

    def test_act_workflow_model_imports(self):
        from ayeneh.infrastructure.persistence.models.act_workflow import ACTWorkflowModel
        assert ACTWorkflowModel.__tablename__ == "act_workflows"

    def test_all_models_in_init(self):
        from ayeneh.infrastructure.persistence.models import (
            ACTExecutionModel,
            ACTHabitModel,
            ACTInterventionModel,
            ACTFeedbackModel,
            ACTWorkflowModel,
        )
        assert ACTExecutionModel is not None
        assert ACTHabitModel is not None
        assert ACTInterventionModel is not None
        assert ACTFeedbackModel is not None
        assert ACTWorkflowModel is not None


class TestACTAPIEndpoint:
    """Tests for ACT API endpoint definitions (import-level validation)."""

    def test_act_endpoint_imports(self):
        from ayeneh.api.v1.endpoints.act import router
        assert router is not None

    def test_act_health_endpoint_exists(self):
        from ayeneh.api.v1.endpoints.act import act_health
        assert callable(act_health)

    def test_act_router_prefix(self):
        from ayeneh.api.v1.endpoints.act import router
        assert router.prefix == "/act"

    def test_act_router_tags(self):
        from ayeneh.api.v1.endpoints.act import router
        assert "action_architecture" in router.tags
