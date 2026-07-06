"""Unit tests for DEC-05 Strategy Optimization types and engine."""

from __future__ import annotations

import pytest

from ayeneh.dec.strategy_optimization.types import (
    ExplainabilityMetadata,
    OptimizationSuggestion,
    OPTIMIZATION_TYPES,
    PatternDetection,
    PerformanceMetrics,
    PerformanceTrend,
    RiskProfile,
    StrategyHierarchyLevel,
    StrategyObject,
    StrategyOptimizationResult,
    STRATEGY_HIERARCHY_LEVELS,
    STRATEGY_STATUS,
)
from ayeneh.dec.strategy_optimization.engine import StrategyOptimizationEngine


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestStrategyHierarchyLevel:
    def test_valid_level(self) -> None:
        level = StrategyHierarchyLevel(level='execution')
        assert level.level == 'execution'

    def test_all_valid_levels(self) -> None:
        for lvl in STRATEGY_HIERARCHY_LEVELS:
            level = StrategyHierarchyLevel(level=lvl)
            assert level.level == lvl

    def test_invalid_level_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid hierarchy level"):
            StrategyHierarchyLevel(level='invalid')


class TestPerformanceMetrics:
    def test_default(self) -> None:
        m = PerformanceMetrics()
        assert m.success_rate == 0.0
        assert m.overall_score >= 0.0

    def test_overall_score_calculation(self) -> None:
        m = PerformanceMetrics(
            success_rate=1.0,
            efficiency=1.0,
            adaptability=1.0,
            resource_usage=0.0,
            average_confidence=1.0,
        )
        assert m.overall_score > 0.8

    def test_zero_metrics(self) -> None:
        m = PerformanceMetrics(
            success_rate=0.0,
            efficiency=0.0,
            adaptability=0.0,
            resource_usage=1.0,
            average_confidence=0.0,
        )
        assert m.overall_score <= 0.2


class TestRiskProfile:
    def test_default(self) -> None:
        r = RiskProfile()
        assert r.risk_level == 'medium'
        assert r.risk_score == 0.5


class TestOptimizationSuggestion:
    def test_valid_suggestion(self) -> None:
        s = OptimizationSuggestion(
            optimization_type='parameter_tuning',
            description='Tune parameters',
        )
        assert s.optimization_type == 'parameter_tuning'

    def test_all_valid_types(self) -> None:
        for opt_type in OPTIMIZATION_TYPES:
            s = OptimizationSuggestion(optimization_type=opt_type)
            assert s.optimization_type == opt_type

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid optimization type"):
            OptimizationSuggestion(optimization_type='magic')


class TestStrategyObject:
    def test_default_creation(self) -> None:
        s = StrategyObject(strategy_id="strat-1")
        assert s.strategy_id == "strat-1"
        assert s.description == ''
        assert s.historical_performance == 0.0
        assert s.confidence == 0.0
        assert s.creation_timestamp is not None

    def test_full_creation(self) -> None:
        s = StrategyObject(
            strategy_id="strat-2",
            description="Test strategy",
            supported_goals=("goal-1", "goal-2"),
            historical_performance=0.85,
            confidence=0.9,
            risk_profile={'risk_level': 'low'},
        )
        assert s.description == "Test strategy"
        assert len(s.supported_goals) == 2
        assert s.historical_performance == 0.85


class TestPerformanceTrend:
    def test_creation(self) -> None:
        t = PerformanceTrend(
            metric_name='success_rate',
            direction='improving',
            magnitude=0.2,
            confidence=0.8,
        )
        assert t.direction == 'improving'


class TestPatternDetection:
    def test_creation(self) -> None:
        p = PatternDetection(
            pattern_type='success_pattern',
            description='Frequent success',
            occurrences=10,
        )
        assert p.occurrences == 10


class TestStrategyOptimizationResult:
    def test_default(self) -> None:
        r = StrategyOptimizationResult()
        assert r.strategy_id == ''
        assert r.has_suggestions is False

    def test_with_suggestions(self) -> None:
        r = StrategyOptimizationResult(
            suggestions=(OptimizationSuggestion(),),
        )
        assert r.has_suggestions is True


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestStrategyOptimizationEngine:
    @pytest.fixture
    def engine(self) -> StrategyOptimizationEngine:
        return StrategyOptimizationEngine()

    def test_basic_optimization(self, engine: StrategyOptimizationEngine) -> None:
        result = engine.optimize(
            strategy_description="Test strategy",
        )
        assert result.strategy_id
        assert result.strategy is not None
        assert result.duration_ms >= 0
        assert isinstance(result.suggestions, tuple)
        assert isinstance(result.patterns, tuple)
        assert isinstance(result.trends, tuple)

    def test_optimization_with_decisions(self, engine: StrategyOptimizationEngine) -> None:
        decisions = [
            {'type': 'research', 'status': 'successful', 'confidence': 0.8},
            {'type': 'planning', 'status': 'failed', 'confidence': 0.3},
            {'type': 'research', 'status': 'successful', 'confidence': 0.9},
        ]
        result = engine.optimize(
            strategy_description="Decision-based strategy",
            historical_decisions=decisions,
        )
        assert result.strategy is not None
        assert result.performance.total_evaluations == 0  # no evaluations passed

    def test_optimization_with_plans(self, engine: StrategyOptimizationEngine) -> None:
        plans = [
            {'type': 'action', 'status': 'completed', 'steps': [1, 2, 3]},
            {'type': 'research', 'status': 'completed', 'steps': [1]},
        ]
        result = engine.optimize(
            strategy_description="Plan-based strategy",
            historical_plans=plans,
        )
        assert result.strategy is not None

    def test_optimization_with_evaluations(self, engine: StrategyOptimizationEngine) -> None:
        evaluations = [
            {'outcome_category': 'successful', 'confidence': 0.9, 'lessons': ['good']},
            {'outcome_category': 'failed', 'confidence': 0.2, 'lessons': ['bad']},
        ]
        result = engine.optimize(
            strategy_description="Evaluation-based strategy",
            action_evaluations=evaluations,
        )
        assert result.strategy is not None
        assert result.performance.total_evaluations == 2

    def test_optimization_with_all_data(self, engine: StrategyOptimizationEngine) -> None:
        result = engine.optimize(
            strategy_description="Comprehensive strategy",
            historical_decisions=[
                {'type': 'test', 'status': 'successful', 'confidence': 0.8},
            ],
            historical_plans=[
                {'type': 'test', 'status': 'completed', 'steps': [1]},
            ],
            action_evaluations=[
                {'outcome_category': 'successful', 'confidence': 0.9, 'lessons': []},
            ],
            context={'hierarchy_level': 'domain_strategy'},
        )
        assert result.strategy is not None
        assert result.strategy.historical_performance >= 0.0

    def test_empty_inputs(self, engine: StrategyOptimizationEngine) -> None:
        result = engine.optimize()
        assert result.strategy_id
        assert result.strategy is not None
        assert len(result.suggestions) >= 1  # at least a monitoring suggestion

    def test_get_strategy(self, engine: StrategyOptimizationEngine) -> None:
        result = engine.optimize(strategy_description="Retrieve me")
        retrieved = engine.get_strategy(result.strategy_id)
        assert retrieved is not None
        assert retrieved.strategy_id == result.strategy_id

    def test_get_all_strategies(self, engine: StrategyOptimizationEngine) -> None:
        engine.optimize(strategy_description="First")
        engine.optimize(strategy_description="Second")
        all_strats = engine.get_all_strategies()
        assert len(all_strats) >= 2

    def test_suggestions_generated_for_failures(self, engine: StrategyOptimizationEngine) -> None:
        result = engine.optimize(
            strategy_description="Failing strategy",
            historical_decisions=[
                {'type': 'test', 'status': 'failed', 'confidence': 0.1},
                {'type': 'test', 'status': 'failed', 'confidence': 0.1},
            ],
            action_evaluations=[
                {'outcome_category': 'failed', 'confidence': 0.1, 'lessons': []},
            ],
        )
        assert len(result.suggestions) >= 1

    def test_patterns_detected_for_successes(self, engine: StrategyOptimizationEngine) -> None:
        result = engine.optimize(
            strategy_description="Successful strategy",
            historical_decisions=[
                {'type': 'research', 'status': 'successful', 'confidence': 0.9},
                {'type': 'research', 'status': 'successful', 'confidence': 0.85},
            ],
        )
        # Should detect at least a success pattern
        success_patterns = [p for p in result.patterns if p.pattern_type == 'success_pattern']
        assert len(success_patterns) >= 1

    def test_trends_detected(self, engine: StrategyOptimizationEngine) -> None:
        result = engine.optimize(
            strategy_description="Trend strategy",
            historical_decisions=[
                {'type': 'test', 'status': 'successful', 'confidence': 0.8},
            ],
        )
        assert len(result.trends) >= 3  # decision, plan, evaluation trends
