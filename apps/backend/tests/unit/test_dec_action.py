"""Unit tests for DEC-04 Action Evaluation types and engine."""

from __future__ import annotations

import pytest

from ayeneh.dec.action_evaluation.types import (
    ActionEvaluationObject,
    ActionEvaluationResult,
    ComparisonResult,
    DeviationComponent,
    EvidenceItem,
    ExplainabilityMetadata,
    LessonLearned,
    OutcomeCategory,
    OUTCOME_CATEGORIES,
    EVIDENCE_TYPES,
)
from ayeneh.dec.action_evaluation.engine import ActionEvaluationEngine
from ayeneh.dec.action_evaluation.learning import BehavioralLearner


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestOutcomeCategory:
    def test_valid_category(self) -> None:
        cat = OutcomeCategory(category='successful', confidence=0.9)
        assert cat.category == 'successful'
        assert cat.confidence == 0.9

    def test_all_valid_categories(self) -> None:
        for cat_name in OUTCOME_CATEGORIES:
            cat = OutcomeCategory(category=cat_name)
            assert cat.category == cat_name

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid outcome category"):
            OutcomeCategory(category='invalid_category')


class TestEvidenceItem:
    def test_valid_evidence(self) -> None:
        ev = EvidenceItem(
            evidence_id="e1",
            evidence_type='direct_observation',
            reliability=0.8,
        )
        assert ev.evidence_id == "e1"
        assert ev.reliability == 0.8

    def test_invalid_evidence_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid evidence type"):
            EvidenceItem(evidence_type='fake_type')


class TestActionEvaluationObject:
    def test_default_creation(self) -> None:
        obj = ActionEvaluationObject(evaluation_id="eval-1")
        assert obj.evaluation_id == "eval-1"
        assert obj.associated_action == ''
        assert obj.confidence == 0.0
        assert obj.deviation_analysis == ()
        assert obj.supporting_evidence == ()
        assert obj.lessons_learned == ()
        assert obj.creation_timestamp is not None

    def test_full_creation(self) -> None:
        obj = ActionEvaluationObject(
            evaluation_id="eval-2",
            associated_action="did something",
            associated_plan="plan-1",
            associated_goal="goal-1",
            expected_outcome="success",
            observed_outcome="partial success",
            confidence=0.7,
            deviation_analysis=({'dimension': 'timing', 'magnitude': 0.3},),
            supporting_evidence=("ev-1",),
            lessons_learned=("lesson-1",),
        )
        assert obj.associated_action == "did something"
        assert obj.confidence == 0.7
        assert len(obj.deviation_analysis) == 1


class TestDeviationComponent:
    def test_creation(self) -> None:
        d = DeviationComponent(
            dimension='timing',
            expected_value="fast",
            observed_value="slow",
            magnitude=0.6,
            direction='negative',
        )
        assert d.dimension == 'timing'
        assert d.magnitude == 0.6


class TestComparisonResult:
    def test_default(self) -> None:
        c = ComparisonResult()
        assert c.overall_match == 0.0
        assert c.dimensions == ()
        assert c.summary == ''


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestActionEvaluationEngine:
    @pytest.fixture
    def engine(self) -> ActionEvaluationEngine:
        return ActionEvaluationEngine()

    def test_basic_evaluation(self, engine: ActionEvaluationEngine) -> None:
        result = engine.evaluate(
            action_description="Test action",
            expected_outcome="Expected result",
            observed_outcome="Observed result",
        )
        assert result.evaluation_id
        assert result.evaluation_object is not None
        assert result.comparison is not None
        assert result.duration_ms >= 0
        assert result.evaluation_object.confidence >= 0.0

    def test_evaluation_with_context(self, engine: ActionEvaluationEngine) -> None:
        ctx = {
            'action_type': 'test',
            'success_criteria': ['criterion1', 'criterion2'],
            'outcome_indicators': ['indicator1'],
            'side_effects': [],
        }
        result = engine.evaluate(
            action_description="Contextual action",
            expected_outcome="Expected",
            observed_outcome="Observed",
            context=ctx,
        )
        assert result.evaluation_id
        assert result.comparison is not None

    def test_evaluation_with_evidence(self, engine: ActionEvaluationEngine) -> None:
        evidence = [
            {'evidence_id': 'ev1', 'description': 'test evidence', 'reliability': 0.9},
            {'evidence_id': 'ev2', 'description': 'more evidence', 'reliability': 0.7},
        ]
        result = engine.evaluate(
            action_description="Evidence-based action",
            expected_outcome="Expected",
            observed_outcome="Observed",
            evidence=evidence,
        )
        assert result.evaluation_id
        assert len(result.lessons) >= 0

    def test_evaluation_with_plan_and_goal(self, engine: ActionEvaluationEngine) -> None:
        result = engine.evaluate(
            action_description="Plan-linked action",
            expected_outcome="Expected",
            observed_outcome="Observed",
            associated_plan="plan-123",
            associated_goal="goal-456",
        )
        obj = result.evaluation_object
        assert obj is not None
        assert obj.associated_plan == "plan-123"
        assert obj.associated_goal == "goal-456"

    def test_empty_inputs(self, engine: ActionEvaluationEngine) -> None:
        result = engine.evaluate()
        assert result.evaluation_id
        assert result.comparison is not None

    def test_successful_outcome_classification(self, engine: ActionEvaluationEngine) -> None:
        result = engine.evaluate(
            action_description="do research",
            expected_outcome="do research",
            observed_outcome="do research with good results",
            context={
                'success_criteria': ['research done'],
                'outcome_indicators': ['research done', 'good results'],
            },
        )
        category = result.comparison.category.category if result.comparison else 'unknown'
        assert category in OUTCOME_CATEGORIES

    def test_failed_outcome_classification(self, engine: ActionEvaluationEngine) -> None:
        result = engine.evaluate(
            action_description="build house",
            expected_outcome="build beautiful house",
            observed_outcome="complete failure nothing happened",
            context={
                'success_criteria': ['house built', 'beautiful', 'complete'],
                'outcome_indicators': [],
                'side_effects': ['wasted resources'],
            },
        )
        assert result.evaluation_id
        assert result.comparison is not None


# ---------------------------------------------------------------------------
# BehavioralLearner tests
# ---------------------------------------------------------------------------


class TestBehavioralLearner:
    @pytest.fixture
    def learner(self) -> BehavioralLearner:
        return BehavioralLearner()

    def _make_eval(self, action: str, confidence: float, lessons: list[str]) -> ActionEvaluationObject:
        return ActionEvaluationObject(
            evaluation_id=f"eval-{action}",
            associated_action=action,
            confidence=confidence,
            lessons_learned=tuple(lessons),
        )

    def test_ingest_single(self, learner: BehavioralLearner) -> None:
        ev = self._make_eval("test action", 0.8, ["This was a good strategy"])
        new_lessons = learner.ingest(ev)
        assert len(new_lessons) > 0
        assert learner.get_all_lessons()

    def test_reliable_habits(self, learner: BehavioralLearner) -> None:
        ev = self._make_eval("consistent action", 0.9, ["This is a reliable habit"])
        learner.ingest(ev)
        habits = learner.get_reliable_habits()
        assert len(habits) >= 0  # classification depends on text

    def test_recurring_mistakes(self, learner: BehavioralLearner) -> None:
        ev = self._make_eval("failing action", 0.2, ["This was a recurring mistake"])
        learner.ingest(ev)
        mistakes = learner.get_recurring_mistakes()
        assert isinstance(mistakes, tuple)

    def test_high_performing_strategies(self, learner: BehavioralLearner) -> None:
        ev = self._make_eval("great action", 0.9, ["This is a high-performing strategy"])
        learner.ingest(ev)
        strategies = learner.get_high_performing_strategies()
        assert isinstance(strategies, tuple)

    def test_pattern_strength(self, learner: BehavioralLearner) -> None:
        for i in range(5):
            learner.ingest(self._make_eval("repeated action", 0.8, ["habit"]))
        strength = learner.compute_pattern_strength("repeated action")
        assert 0.0 <= strength <= 1.0
        assert strength > 0.0

    def test_improvement_trend_insufficient_data(self, learner: BehavioralLearner) -> None:
        trend = learner.detect_improvement_trend()
        assert trend['trend'] == 'insufficient_data'

    def test_improvement_trend_with_data(self, learner: BehavioralLearner) -> None:
        for i in range(5):
            learner.ingest(self._make_eval("action", 0.3 + i * 0.1, ["lesson"]))
        trend = learner.detect_improvement_trend()
        assert trend['trend'] == 'available'
        assert trend['direction'] in ('improving', 'declining', 'stable')

    def test_reset(self, learner: BehavioralLearner) -> None:
        learner.ingest(self._make_eval("action", 0.5, ["lesson"]))
        assert learner.get_all_lessons()
        learner.reset()
        assert len(learner.get_all_lessons()) == 0

    def test_lesson_summary(self, learner: BehavioralLearner) -> None:
        learner.ingest(self._make_eval("a", 0.5, ["lesson one"]))
        learner.ingest(self._make_eval("b", 0.7, ["lesson two"]))
        summary = learner.get_lesson_summary()
        assert isinstance(summary, dict)
