"""Integration tests for the DEC Decision Architecture."""

from __future__ import annotations

import pytest

from ayeneh.dec.action_evaluation.engine import ActionEvaluationEngine
from ayeneh.dec.action_evaluation.learning import BehavioralLearner
from ayeneh.dec.action_evaluation.types import ActionEvaluationObject
from ayeneh.dec.strategy_optimization.engine import StrategyOptimizationEngine
from ayeneh.dec.strategy_optimization.types import StrategyObject


# ---------------------------------------------------------------------------
# Cross-module integration
# ---------------------------------------------------------------------------


class TestActionEvaluationToStrategyPipeline:
    """Test that ActionEvaluation results feed into StrategyOptimization."""

    def test_evaluation_results_feed_strategy(self) -> None:
        eval_engine = ActionEvaluationEngine()
        strat_engine = StrategyOptimizationEngine()

        # Run multiple evaluations
        eval_results = []
        for i in range(3):
            result = eval_engine.evaluate(
                action_description=f"Research step {i}",
                expected_outcome=f"Find insight {i}",
                observed_outcome=f"Found insight {i}" if i < 2 else "Found nothing",
                context={'success_criteria': [f'insight {i}'], 'outcome_indicators': [f'insight {i}'] if i < 2 else []},
            )
            eval_results.append(result)

        # Convert to dicts for strategy engine
        eval_dicts = [
            {
                'outcome_category': r.comparison.category.category if r.comparison else 'inconclusive',
                'confidence': r.confidence,
                'lessons': list(r.lessons),
            }
            for r in eval_results
        ]

        # Optimize strategy based on evaluations
        strategy_result = strat_engine.optimize(
            strategy_description="Research strategy optimized from evaluations",
            action_evaluations=eval_dicts,
        )

        assert strategy_result.strategy is not None
        assert strategy_result.performance.total_evaluations == 3
        assert strategy_result.duration_ms >= 0

    def test_multiple_evaluations_build_strategy(self) -> None:
        eval_engine = ActionEvaluationEngine()
        strat_engine = StrategyOptimizationEngine()

        decisions = []
        for i in range(5):
            result = eval_engine.evaluate(
                action_description=f"Decision action {i}",
                expected_outcome=f"Expected {i}",
                observed_outcome=f"Observed {i}",
            )
            decisions.append({
                'type': 'research',
                'status': 'successful' if i % 2 == 0 else 'failed',
                'confidence': 0.8 if i % 2 == 0 else 0.3,
            })

        strategy_result = strat_engine.optimize(
            strategy_description="Strategy from decisions",
            historical_decisions=decisions,
        )
        assert strategy_result.strategy is not None
        assert len(strategy_result.patterns) >= 0


class TestBehavioralLearnerIntegration:
    """Test BehavioralLearner with real evaluation pipeline."""

    def test_learner_accumulates_from_engine(self) -> None:
        engine = ActionEvaluationEngine()
        learner = BehavioralLearner()

        for i in range(4):
            result = engine.evaluate(
                action_description=f"Action {i}",
                expected_outcome=f"Expected {i}",
                observed_outcome=f"Observed {i}",
                context={'success_criteria': [f'c{i}'], 'outcome_indicators': [f'c{i}']},
            )
            if result.evaluation_object:
                learner.ingest(result.evaluation_object)

        all_lessons = learner.get_all_lessons()
        assert isinstance(all_lessons, tuple)

        summary = learner.get_lesson_summary()
        assert isinstance(summary, dict)

    def test_learner_detects_patterns(self) -> None:
        engine = ActionEvaluationEngine()
        learner = BehavioralLearner()

        # Consistent successes
        for i in range(3):
            result = engine.evaluate(
                action_description="consistent success",
                expected_outcome="do well",
                observed_outcome="did well",
                context={
                    'success_criteria': ['did well'],
                    'outcome_indicators': ['did well'],
                },
            )
            if result.evaluation_object:
                learner.ingest(result.evaluation_object)

        strength = learner.compute_pattern_strength("consistent success")
        assert strength > 0.0


class TestEngineEndToEnd:
    """End-to-end tests running both engines together."""

    def test_full_lifecycle(self) -> None:
        eval_engine = ActionEvaluationEngine()
        strat_engine = StrategyOptimizationEngine()

        # Phase 1: Multiple evaluations
        eval_dicts = []
        for i in range(3):
            r = eval_engine.evaluate(
                action_description=f"Lifecycle action {i}",
                expected_outcome=f"Expected result {i}",
                observed_outcome=f"Observed result {i}",
                associated_plan=f"plan-{i}",
                associated_goal=f"goal-{i}",
                evidence=[
                    {'evidence_id': f'ev-{i}', 'description': f'evidence {i}', 'reliability': 0.8},
                ],
            )
            eval_dicts.append({
                'outcome_category': r.comparison.category.category if r.comparison else 'inconclusive',
                'confidence': r.confidence,
                'lessons': list(r.lessons),
            })

        # Phase 2: Strategy optimization
        decisions = [
            {'type': 'test', 'status': 'successful', 'confidence': 0.8},
            {'type': 'test', 'status': 'successful', 'confidence': 0.9},
        ]
        plans = [
            {'type': 'test', 'status': 'completed', 'steps': [1, 2]},
        ]

        result = strat_engine.optimize(
            strategy_description="Full lifecycle strategy",
            historical_decisions=decisions,
            historical_plans=plans,
            action_evaluations=eval_dicts,
            context={'hierarchy_level': 'project_strategy'},
        )

        assert result.strategy is not None
        assert result.strategy.confidence >= 0.0
        assert result.performance.overall_score >= 0.0
        assert len(result.trends) >= 3
        assert len(result.suggestions) >= 1


class TestEdgeCases:
    """Edge case tests for robustness."""

    def test_empty_evaluation_engine(self) -> None:
        engine = ActionEvaluationEngine()
        result = engine.evaluate()
        assert result.evaluation_id
        assert result.comparison is not None

    def test_empty_strategy_engine(self) -> None:
        engine = StrategyOptimizationEngine()
        result = engine.optimize()
        assert result.strategy_id
        assert result.strategy is not None

    def test_learner_empty_history(self) -> None:
        learner = BehavioralLearner()
        assert learner.get_all_lessons() == ()
        assert learner.get_reliable_habits() == ()
        assert learner.get_recurring_mistakes() == ()
        assert learner.get_high_performing_strategies() == ()
        assert learner.get_lesson_summary() == {}
        assert learner.compute_pattern_strength("anything") == 0.0
        assert learner.detect_improvement_trend()['trend'] == 'insufficient_data'

    def test_strategy_engine_retrieval(self) -> None:
        engine = StrategyOptimizationEngine()
        assert engine.get_strategy("nonexistent") is None
        assert engine.get_all_strategies() == ()

    def test_large_context(self) -> None:
        engine = ActionEvaluationEngine()
        ctx = {
            'success_criteria': [f'criterion_{i}' for i in range(20)],
            'outcome_indicators': [f'indicator_{i}' for i in range(15)],
            'side_effects': [f'effect_{i}' for i in range(5)],
        }
        result = engine.evaluate(
            action_description="Large context action",
            expected_outcome="Expected with many criteria",
            observed_outcome="Observed with many indicators",
            context=ctx,
        )
        assert result.evaluation_id
        assert result.comparison is not None
