"""Tests for ACT-04 Feedback Loop Coordinator."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.act.feedback_loop.types import (
    FEEDBACK_TYPES,
    FEEDBACK_SEVERITY_LEVELS,
    LEARNING_CATEGORIES,
    PROPAGATION_MODES,
    ActionEvaluation,
    BehavioralAdaptation,
    FeedbackObject,
    FeedbackResult,
    KnowledgeUpdate,
    ObservedOutcome,
    RealityCalibration,
    ReflectionEntry,
    StrategyRevision,
    PropagationRecord,
)
from ayeneh.act.feedback_loop.engine import FeedbackLoopCoordinator
from ayeneh.act.feedback_loop.propagation import FeedbackPropagation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return FeedbackLoopCoordinator()


@pytest.fixture
def propagation():
    return FeedbackPropagation()


@pytest.fixture
def sample_context():
    return {
        'observed_outcomes': [
            {
                'outcome_id': 'out-1',
                'source_event': 'execution_observation',
                'outcome_type': 'success',
                'description': 'Task completed successfully',
                'expected_value': 'complete',
                'actual_value': 'complete',
                'deviation_magnitude': 0.0,
                'confidence': 0.9,
            },
        ],
        'action_evaluations': [],
        'reflections': [],
        'previous_confidence': 0.6,
    }


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestFeedbackTypes:
    """Tests for ACT-04 type definitions."""

    def test_feedback_types_count(self):
        assert len(FEEDBACK_TYPES) == 9

    def test_feedback_types_include_expected(self):
        expected = {
            'behavioral', 'planning', 'prediction', 'memory', 'reflection',
            'strategy', 'habit', 'dialogue', 'meta_cognitive',
        }
        assert set(FEEDBACK_TYPES) == expected

    def test_severity_levels_count(self):
        assert len(FEEDBACK_SEVERITY_LEVELS) == 5

    def test_learning_categories_count(self):
        assert len(LEARNING_CATEGORIES) == 8

    def test_propagation_modes_count(self):
        assert len(PROPAGATION_MODES) == 4


class TestFeedbackDataclasses:
    """Tests for ACT-04 frozen dataclasses."""

    def test_feedback_object_creation(self):
        fb = FeedbackObject(feedback_id='fb-1')
        assert fb.feedback_id == 'fb-1'
        assert fb.source_event == ''
        assert fb.affected_modules == ()
        assert fb.confidence == 0.0

    def test_feedback_object_immutability(self):
        fb = FeedbackObject(feedback_id='fb-1')
        with pytest.raises(AttributeError):
            fb.feedback_id = 'fb-2'  # type: ignore[misc]

    def test_feedback_object_defaults(self):
        fb = FeedbackObject(feedback_id='fb-1')
        assert fb.observed_evidence == ()
        assert fb.learning_outcome == ''
        assert fb.propagation_targets == ()
        assert fb.applied_revisions == ()
        assert fb.remaining_questions == ()
        assert fb.version_history == ()
        assert isinstance(fb.creation_timestamp, datetime)
        assert fb.explainability_metadata == {}

    def test_observed_outcome_creation(self):
        outcome = ObservedOutcome(
            outcome_id='out-1',
            source_event='test',
            description='Test outcome',
            confidence=0.8,
        )
        assert outcome.outcome_id == 'out-1'
        assert outcome.confidence == 0.8
        assert outcome.deviation_magnitude == 0.0

    def test_action_evaluation_creation(self):
        eval_obj = ActionEvaluation(
            evaluation_id='eval-1',
            action_description='test action',
            success_score=0.7,
        )
        assert eval_obj.evaluation_id == 'eval-1'
        assert eval_obj.outcome_match is False
        assert eval_obj.success_score == 0.7

    def test_reflection_entry_creation(self):
        ref = ReflectionEntry(
            reflection_id='ref-1',
            reflection_type='general',
            confidence=0.6,
        )
        assert ref.reflection_id == 'ref-1'
        assert ref.insights == ()

    def test_reality_calibration_creation(self):
        cal = RealityCalibration(
            calibration_id='cal-1',
            previous_value=0.5,
            adjusted_value=0.6,
        )
        assert cal.calibration_id == 'cal-1'
        assert cal.previous_value == 0.5
        assert cal.adjusted_value == 0.6

    def test_knowledge_update_creation(self):
        ku = KnowledgeUpdate(
            update_id='ku-1',
            update_type='addition',
            new_knowledge='learned something',
        )
        assert ku.update_id == 'ku-1'
        assert ku.confidence_delta == 0.0

    def test_strategy_revision_creation(self):
        sr = StrategyRevision(
            revision_id='sr-1',
            affected_strategy='default',
            new_approach='improved',
        )
        assert sr.revision_id == 'sr-1'
        assert sr.revision_type == 'adjustment'

    def test_behavioral_adaptation_creation(self):
        ba = BehavioralAdaptation(
            adaptation_id='ba-1',
            adaptation_type='habit_adjustment',
        )
        assert ba.adaptation_id == 'ba-1'
        assert ba.previous_pattern == ''

    def test_propagation_record_creation(self):
        pr = PropagationRecord(
            record_id='pr-1',
            source_feedback_id='fb-1',
            target_module='execution_monitoring',
        )
        assert pr.record_id == 'pr-1'
        assert pr.applied is False

    def test_feedback_result_creation(self):
        fb = FeedbackObject(feedback_id='fb-1')
        fr = FeedbackResult(feedback=fb)
        assert fr.feedback.feedback_id == 'fb-1'
        assert fr.observed_outcomes == ()
        assert fr.action_evaluations == ()
        assert fr.reflections == ()
        assert fr.calibrations == ()
        assert fr.knowledge_updates == ()
        assert fr.strategy_revisions == ()
        assert fr.behavioral_adaptations == ()
        assert fr.pipeline_phases_completed == ()


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestFeedbackLoopCoordinator:
    """Tests for ACT-04 FeedbackLoopCoordinator engine."""

    def test_process_empty_request(self, engine):
        result = engine.process({})
        assert isinstance(result, FeedbackResult)
        assert len(result.pipeline_phases_completed) == 7

    def test_process_with_outcomes(self, engine, sample_context):
        result = engine.process(
            {'source_event': 'test'},
            context=sample_context,
        )
        assert len(result.observed_outcomes) == 1
        assert result.observed_outcomes[0].description == 'Task completed successfully'

    def test_process_generates_evaluations(self, engine, sample_context):
        result = engine.process(
            {'source_event': 'test'},
            context=sample_context,
        )
        assert len(result.action_evaluations) >= 1

    def test_process_with_no_context(self, engine):
        result = engine.process({'feedback_id': 'fb-1'})
        assert isinstance(result, FeedbackResult)
        assert result.feedback.feedback_id == 'fb-1'

    def test_process_phases_order(self, engine):
        result = engine.process({})
        expected_phases = (
            'ObservedOutcome',
            'ActionEvaluation',
            'Reflection',
            'RealityCalibration',
            'KnowledgeUpdate',
            'StrategyRevision',
            'BehavioralAdaptation',
        )
        assert result.pipeline_phases_completed == expected_phases

    def test_process_confidence_range(self, engine):
        result = engine.process({})
        assert 0.0 <= result.feedback.confidence <= 1.0

    def test_process_with_raw_reflections(self, engine):
        ctx = {
            'reflections': [
                {
                    'reflection_id': 'ref-raw-1',
                    'reflection_type': 'manual',
                    'insights': ('insight-1', 'insight-2'),
                    'confidence': 0.8,
                },
            ],
        }
        result = engine.process({}, context=ctx)
        assert len(result.reflections) >= 1

    def test_process_with_raw_calibrations(self, engine):
        ctx = {
            'calibrations': [
                {
                    'calibration_id': 'cal-raw-1',
                    'previous_value': 0.5,
                    'adjusted_value': 0.7,
                    'adjustment_reason': 'better data',
                    'confidence': 0.6,
                },
            ],
        }
        result = engine.process({}, context=ctx)
        assert len(result.calibrations) >= 1

    def test_process_with_raw_knowledge_updates(self, engine):
        ctx = {
            'knowledge_updates': [
                {
                    'update_id': 'ku-raw-1',
                    'update_type': 'addition',
                    'new_knowledge': 'new fact',
                    'confidence': 0.7,
                },
            ],
        }
        result = engine.process({}, context=ctx)
        assert len(result.knowledge_updates) >= 1

    def test_process_with_raw_strategy_revisions(self, engine):
        ctx = {
            'strategy_revisions': [
                {
                    'revision_id': 'sr-raw-1',
                    'affected_strategy': 'test',
                    'revision_type': 'major_change',
                    'previous_approach': 'old',
                    'new_approach': 'new',
                    'rationale': 'testing',
                    'confidence': 0.6,
                },
            ],
        }
        result = engine.process({}, context=ctx)
        assert len(result.strategy_revisions) >= 1

    def test_process_with_raw_adaptations(self, engine):
        ctx = {
            'behavioral_adaptations': [
                {
                    'adaptation_id': 'ba-raw-1',
                    'adaptation_type': 'habit_adjustment',
                    'target_behavior': 'test',
                    'confidence': 0.5,
                },
            ],
        }
        result = engine.process({}, context=ctx)
        assert len(result.behavioral_adaptations) >= 1

    def test_list_feedback(self, engine):
        result = engine.list_feedback()
        assert isinstance(result, list)

    def test_get_propagation_history(self, engine):
        history = engine.get_propagation_history()
        assert isinstance(history, list)

    def test_get_saturation_status(self, engine):
        status = engine.get_saturation_status()
        assert isinstance(status, dict)
        assert 'execution_monitoring' in status


# ---------------------------------------------------------------------------
# Propagation tests
# ---------------------------------------------------------------------------


class TestFeedbackPropagation:
    """Tests for ACT-04 FeedbackPropagation."""

    def test_propagate_immediate(self, propagation):
        fb = FeedbackObject(
            feedback_id='fb-1',
            propagation_targets=('execution_monitoring',),
            confidence=0.8,
        )
        records = propagation.propagate(fb, mode='immediate')
        assert len(records) == 1
        assert records[0].target_module == 'execution_monitoring'
        assert records[0].propagation_mode == 'immediate'

    def test_propagate_override_targets(self, propagation):
        fb = FeedbackObject(feedback_id='fb-1', confidence=0.5)
        records = propagation.propagate(
            fb,
            target_modules=('habit_formation', 'decision'),
            mode='batched',
        )
        assert len(records) == 2
        modules = {r.target_module for r in records}
        assert modules == {'habit_formation', 'decision'}

    def test_propagate_invalid_mode_falls_back(self, propagation):
        fb = FeedbackObject(
            feedback_id='fb-1',
            propagation_targets=('execution_monitoring',),
            confidence=0.5,
        )
        records = propagation.propagate(fb, mode='invalid_mode')
        assert records[0].propagation_mode == 'immediate'

    def test_propagate_batch(self, propagation):
        feedbacks = [
            FeedbackObject(feedback_id=f'fb-{i}', propagation_targets=('execution_monitoring',), confidence=0.5)
            for i in range(3)
        ]
        records = propagation.propagate_batch(feedbacks, mode='batched')
        assert len(records) == 3

    def test_module_feedback_count(self, propagation):
        fb = FeedbackObject(
            feedback_id='fb-1',
            propagation_targets=('execution_monitoring',),
            confidence=0.8,
        )
        propagation.propagate(fb)
        count = propagation.get_module_feedback_count('execution_monitoring')
        assert count == 1

    def test_get_propagation_history_filter(self, propagation):
        fb1 = FeedbackObject(feedback_id='fb-1', propagation_targets=('execution_monitoring',), confidence=0.5)
        fb2 = FeedbackObject(feedback_id='fb-2', propagation_targets=('habit_formation',), confidence=0.5)
        propagation.propagate(fb1)
        propagation.propagate(fb2)

        history = propagation.get_propagation_history(module='execution_monitoring')
        assert len(history) == 1
        assert history[0].target_module == 'execution_monitoring'

    def test_reset_module_counts(self, propagation):
        fb = FeedbackObject(feedback_id='fb-1', propagation_targets=('execution_monitoring',), confidence=0.5)
        propagation.propagate(fb)
        assert propagation.get_module_feedback_count('execution_monitoring') == 1
        propagation.reset_module_counts('execution_monitoring')
        assert propagation.get_module_feedback_count('execution_monitoring') == 0

    def test_queue_and_flush(self, propagation):
        fb = FeedbackObject(feedback_id='fb-1', propagation_targets=('execution_monitoring',), confidence=0.5)
        propagation.queue_feedback(fb)
        records = propagation.flush_pending()
        assert len(records) == 1

    def test_saturation_status(self, propagation):
        status = propagation.get_saturation_status()
        assert 'execution_monitoring' in status
        assert status['execution_monitoring']['limit'] == 50
        assert status['execution_monitoring']['count'] == 0

    def test_severity_classification(self, propagation):
        fb_high = FeedbackObject(feedback_id='fb-h', confidence=0.9)
        assert propagation._classify_severity(fb_high) == 'positive'

        fb_mid = FeedbackObject(feedback_id='fb-m', confidence=0.6)
        assert propagation._classify_severity(fb_mid) == 'neutral'

        fb_low = FeedbackObject(feedback_id='fb-l', confidence=0.35)
        assert propagation._classify_severity(fb_low) == 'minor_correction'

        fb_vlow = FeedbackObject(feedback_id='fb-vl', confidence=0.1)
        assert propagation._classify_severity(fb_vlow) == 'major_correction'
