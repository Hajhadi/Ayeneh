"""Tests for the ACT-03 Adaptive Intervention Engine."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.act.adaptive_intervention.types import (
    DIALOGUE_STRATEGIES,
    INTERVENTION_CATEGORIES,
    INTENSITY_LEVELS,
    OUTCOME_EVALUATIONS,
    TIMING_ASSESSMENTS,
    DialoguePlan,
    InterventionEvaluation,
    InterventionObject,
    InterventionResult,
    OpportunitySignal,
    RiskSignal,
    TimingAssessment,
)
from ayeneh.act.adaptive_intervention.engine import AdaptiveInterventionEngine
from ayeneh.act.adaptive_intervention.timing import TimingIntelligence


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return AdaptiveInterventionEngine()


@pytest.fixture
def sample_request():
    return {
        'intervention_id': 'int-001',
        'trigger_event': 'deviation_detected',
        'associated_goal': 'goal-001',
        'associated_plan': 'plan-001',
        'associated_habit': 'habit-001',
        'intervention_type': 'Reminder',
    }


@pytest.fixture
def sample_context():
    return {
        'execution_state': 'running',
        'execution_progress': 0.5,
        'goal_priority': 0.7,
        'cognitive_load': 0.4,
        'emotional_state': 'focused',
        'habit_strength': 0.6,
        'goal_frustration': 0.2,
        'goal_abandonment_risk': 0.1,
        'progress_trend': 'improving',
    }


# ---------------------------------------------------------------------------
# Tests: Types
# ---------------------------------------------------------------------------


class TestInterventionCategories:
    def test_categories_completeness(self):
        assert len(INTERVENTION_CATEGORIES) == 10
        assert 'Reminder' in INTERVENTION_CATEGORIES
        assert 'CelebrationOfProgress' in INTERVENTION_CATEGORIES
        assert 'StrategyRevision' in INTERVENTION_CATEGORIES

    def test_intensity_levels(self):
        assert len(INTENSITY_LEVELS) == 6
        assert 'SilentObservation' in INTENSITY_LEVELS
        assert 'ComprehensivePlanningDialogue' in INTENSITY_LEVELS

    def test_timing_assessments(self):
        assert len(TIMING_ASSESSMENTS) == 6
        assert 'optimal' in TIMING_ASSESSMENTS
        assert 'interrupting' in TIMING_ASSESSMENTS

    def test_outcome_evaluations(self):
        assert len(OUTCOME_EVALUATIONS) == 6
        assert 'effective' in OUTCOME_EVALUATIONS
        assert 'pending_evaluation' in OUTCOME_EVALUATIONS

    def test_dialogue_strategies(self):
        assert len(DIALOGUE_STRATEGIES) == 8
        assert 'socratic_questioning' in DIALOGUE_STRATEGIES


class TestInterventionObject:
    def test_default_values(self):
        obj = InterventionObject(intervention_id='i1')
        assert obj.intervention_id == 'i1'
        assert obj.intervention_type == ''
        assert obj.expected_benefit == 0.0
        assert obj.potential_cost == 0.0
        assert obj.confidence == 0.0

    def test_frozen(self):
        obj = InterventionObject(intervention_id='i1')
        with pytest.raises(AttributeError):
            obj.intervention_id = 'i2'

    def test_custom_values(self):
        obj = InterventionObject(
            intervention_id='i1',
            trigger_event='deviation',
            associated_goal='g1',
            intervention_type='RiskWarning',
            expected_benefit=0.8,
            confidence=0.9,
        )
        assert obj.trigger_event == 'deviation'
        assert obj.intervention_type == 'RiskWarning'
        assert obj.expected_benefit == 0.8


class TestTimingAssessment:
    def test_creation(self):
        t = TimingAssessment(
            assessment_id='t1',
            cognitive_load=0.4,
            task_phase='execution',
            overall_timing='optimal',
        )
        assert t.overall_timing == 'optimal'
        assert t.cognitive_load == 0.4


class TestOpportunitySignal:
    def test_creation(self):
        o = OpportunitySignal(
            signal_id='o1',
            signal_type='completion_celebration',
            strength=0.9,
            urgency=0.7,
        )
        assert o.strength == 0.9


class TestRiskSignal:
    def test_creation(self):
        r = RiskSignal(
            signal_id='r1',
            risk_type='goal_abandonment',
            severity=0.8,
            probability=0.6,
        )
        assert r.severity == 0.8


class TestInterventionEvaluation:
    def test_creation(self):
        e = InterventionEvaluation(
            evaluation_id='e1',
            expected_benefit=0.7,
            potential_cost=0.2,
            net_value=0.5,
        )
        assert e.net_value == 0.5


class TestDialoguePlan:
    def test_creation(self):
        d = DialoguePlan(
            plan_id='d1',
            strategy='socratic_questioning',
            intensity='ReflectiveQuestion',
        )
        assert d.strategy == 'socratic_questioning'


class TestInterventionResult:
    def test_creation(self):
        obj = InterventionObject(intervention_id='i1')
        r = InterventionResult(intervention=obj)
        assert r.intervention.intervention_id == 'i1'
        assert r.timing is None
        assert r.pipeline_phases_completed == ()


# ---------------------------------------------------------------------------
# Tests: TimingIntelligence
# ---------------------------------------------------------------------------


class TestTimingIntelligence:
    def test_init(self):
        ti = TimingIntelligence()
        assert len(ti._history) == 0

    def test_evaluate_optimal(self):
        ti = TimingIntelligence()
        ctx = {
            'cognitive_load': 0.2,
            'task_phase': 'reflection',
            'emotional_intensity': 0.2,
            'goal_urgency': 0.8,
            'progress_level': 0.5,
            'environment_fitness': 0.7,
        }
        assessment = ti.evaluate(ctx)
        assert assessment.overall_timing == 'optimal'

    def test_evaluate_suboptimal(self):
        ti = TimingIntelligence()
        ctx = {
            'cognitive_load': 0.7,
            'task_phase': 'execution',
            'emotional_intensity': 0.6,
            'goal_urgency': 0.3,
            'progress_level': 0.5,
            'environment_fitness': 0.4,
        }
        assessment = ti.evaluate(ctx)
        assert assessment.overall_timing in ('suboptimal', 'acceptable')

    def test_evaluate_premature(self):
        ti = TimingIntelligence()
        ctx = {
            'cognitive_load': 0.9,
            'task_phase': 'execution',
            'emotional_intensity': 0.8,
            'goal_urgency': 0.1,
            'progress_level': 0.1,
            'environment_fitness': 0.2,
        }
        assessment = ti.evaluate(ctx)
        assert assessment.overall_timing in ('premature', 'too_late', 'suboptimal')

    def test_evaluate_clamps_values(self):
        ti = TimingIntelligence()
        ctx = {
            'cognitive_load': 5.0,
            'emotional_intensity': -1.0,
            'goal_urgency': 100.0,
            'progress_level': 0.5,
            'environment_fitness': 0.5,
        }
        assessment = ti.evaluate(ctx)
        assert 0.0 <= assessment.cognitive_load <= 1.0
        assert 0.0 <= assessment.emotional_intensity <= 1.0

    def test_history_tracked(self):
        ti = TimingIntelligence()
        ti.evaluate({})
        ti.evaluate({})
        assert len(ti.get_history()) == 2

    def test_get_latest(self):
        ti = TimingIntelligence()
        assert ti.get_latest() is None
        ti.evaluate({})
        latest = ti.get_latest()
        assert latest is not None


# ---------------------------------------------------------------------------
# Tests: Engine
# ---------------------------------------------------------------------------


class TestAdaptiveInterventionEngine:
    def test_init(self, engine):
        assert engine._interventions == {}
        assert engine._timing_intelligence is not None

    def test_process_basic(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert isinstance(result, InterventionResult)
        assert result.intervention.intervention_id == 'int-001'
        assert len(result.pipeline_phases_completed) == 7

    def test_process_creates_intervention(self, engine, sample_request):
        engine.process(sample_request)
        assert 'int-001' in engine._interventions

    def test_process_timing_assessed(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert result.timing is not None
        assert result.timing.overall_timing in TIMING_ASSESSMENTS

    def test_process_opportunities_detected(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert isinstance(result.opportunities, tuple)

    def test_process_risks_assessed(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert isinstance(result.risks, tuple)

    def test_process_evaluation_computed(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert result.evaluation is not None
        assert result.evaluation.net_value is not None

    def test_process_dialogue_plan_created(self, engine, sample_request, sample_context):
        result = engine.process(sample_request, sample_context)
        assert result.dialogue_plan is not None
        assert result.dialogue_plan.strategy in DIALOGUE_STRATEGIES

    def test_process_blocked_execution(self, engine):
        request = {
            'intervention_id': 'int-002',
            'trigger_event': 'blocked',
        }
        context = {'execution_state': 'blocked'}
        result = engine.process(request, context)
        assert any(
            r.risk_type == 'execution_blocked'
            for r in result.risks
        )

    def test_process_high_frustration(self, engine):
        request = {
            'intervention_id': 'int-003',
            'trigger_event': 'frustration',
        }
        context = {'goal_frustration': 0.8}
        result = engine.process(request, context)
        assert any(
            o.signal_type == 'frustration_support'
            for o in result.opportunities
        )

    def test_process_near_completion(self, engine):
        request = {
            'intervention_id': 'int-004',
            'trigger_event': 'progress',
        }
        context = {'execution_progress': 0.95}
        result = engine.process(request, context)
        assert any(
            o.signal_type == 'completion_celebration'
            for o in result.opportunities
        )

    def test_process_update_existing(self, engine, sample_request, sample_context):
        engine.process(sample_request, sample_context)
        result = engine.process(sample_request, sample_context)
        assert len(result.intervention.version_history) >= 1

    def test_get_intervention(self, engine, sample_request):
        engine.process(sample_request)
        intervention = engine.get_intervention('int-001')
        assert intervention is not None

    def test_get_intervention_not_found(self, engine):
        assert engine.get_intervention('nonexistent') is None

    def test_list_interventions(self, engine, sample_request):
        engine.process(sample_request)
        interventions = engine.list_interventions()
        assert len(interventions) == 1

    def test_get_timing_intelligence(self, engine):
        ti = engine.get_timing_intelligence()
        assert isinstance(ti, TimingIntelligence)

    def test_process_default_intervention_type(self, engine):
        request = {'intervention_id': 'int-005'}
        result = engine.process(request)
        assert result.intervention.intervention_type == 'Reminder'

    def test_process_celebration_strategy(self, engine):
        request = {
            'intervention_id': 'int-006',
            'trigger_event': 'completion',
        }
        context = {'celebration_warranted': True}
        result = engine.process(request, context)
        assert result.dialogue_plan.strategy == 'celebratory_acknowledgment'
