"""DEC-05 Strategy Optimization Engine — 8-phase pipeline for optimizing strategies."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog

from ayeneh.dec.strategy_optimization.types import (
    ExplainabilityMetadata,
    OptimizationSuggestion,
    PerformanceMetrics,
    PerformanceTrend,
    PatternDetection,
    RiskProfile,
    StrategyHierarchyLevel,
    StrategyObject,
    StrategyOptimizationResult,
)

logger = structlog.get_logger(__name__)


class StrategyOptimizationEngine:
    """Optimizes strategies based on historical decisions, plans, and action evaluations.

    Phases:
        1. HistoricalDecisions     — collect and analyze past decisions
        2. HistoricalPlans         — collect and analyze past plans
        3. ActionEvaluations       — incorporate action evaluation results
        4. PerformanceTrends       — detect trends in performance metrics
        5. PatternDetection        — identify recurring patterns
        6. StrategyConstruction    — construct or update strategy objects
        7. Optimization            — generate optimization suggestions
        8. StrategicKnowledgeBase  — update the strategy knowledge base
    """

    def __init__(self) -> None:
        self._strategies: dict[str, StrategyObject] = {}
        self._performance_history: dict[str, list[float]] = {}

    def optimize(
        self,
        strategy_description: str = '',
        context: dict[str, Any] | None = None,
        historical_decisions: list[dict[str, Any]] | None = None,
        historical_plans: list[dict[str, Any]] | None = None,
        action_evaluations: list[dict[str, Any]] | None = None,
        strategy_id: str = '',
        session_id: str = '',
    ) -> StrategyOptimizationResult:
        """Run the full 8-phase strategy optimization pipeline."""
        start = time.monotonic()
        ctx = context or {}
        errors: list[str] = []

        logger.info(
            "strategy_optimization_started",
            session_id=session_id,
            strategy_description=strategy_description[:80],
        )

        # Phase 1: HistoricalDecisions
        decisions_analysis = self._phase_historical_decisions(
            historical_decisions or [], ctx, errors,
        )

        # Phase 2: HistoricalPlans
        plans_analysis = self._phase_historical_plans(
            historical_plans or [], ctx, errors,
        )

        # Phase 3: ActionEvaluations
        eval_analysis = self._phase_action_evaluations(
            action_evaluations or [], ctx, errors,
        )

        # Phase 4: PerformanceTrends
        trends = self._phase_performance_trends(
            decisions_analysis, plans_analysis, eval_analysis, errors,
        )

        # Phase 5: PatternDetection
        patterns = self._phase_pattern_detection(
            decisions_analysis, plans_analysis, eval_analysis, errors,
        )

        # Phase 6: StrategyConstruction
        strategy = self._phase_strategy_construction(
            strategy_description, strategy_id, decisions_analysis,
            plans_analysis, eval_analysis, patterns, ctx, errors,
        )

        # Phase 7: Optimization
        suggestions = self._phase_optimization(
            strategy, trends, patterns, eval_analysis, errors,
        )

        # Phase 8: StrategicKnowledgeBase
        self._phase_strategic_knowledge_base(
            strategy, suggestions, errors,
        )

        # Compute performance metrics
        performance = self._compute_performance(
            decisions_analysis, plans_analysis, eval_analysis,
        )

        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "strategy_optimization_completed",
            strategy_id=strategy.strategy_id,
            suggestions_count=len(suggestions),
            patterns_count=len(patterns),
            duration_ms=duration_ms,
        )

        return StrategyOptimizationResult(
            strategy_id=strategy.strategy_id,
            strategy=strategy,
            performance=performance,
            trends=tuple(trends),
            patterns=tuple(patterns),
            suggestions=tuple(suggestions),
            confidence=strategy.confidence,
            duration_ms=duration_ms,
            errors=tuple(errors),
        )

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _phase_historical_decisions(
        self,
        decisions: list[dict[str, Any]],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        """Phase 1: Collect and analyze historical decisions."""
        try:
            total = len(decisions)
            successful = sum(1 for d in decisions if d.get('status') == 'successful')
            success_rate = successful / max(total, 1)

            avg_confidence = (
                sum(d.get('confidence', 0.5) for d in decisions) / max(total, 1)
            )

            analysis = {
                'total_decisions': total,
                'successful_decisions': successful,
                'success_rate': success_rate,
                'average_confidence': avg_confidence,
                'decision_types': _count_field(decisions, 'type'),
                'time_range': _time_range(decisions),
            }
            logger.debug("phase_historical_decisions_completed", count=total)
            return analysis
        except Exception as exc:
            errors.append(f"Phase 1 (HistoricalDecisions) error: {exc}")
            return {'total_decisions': 0, 'success_rate': 0.0, 'average_confidence': 0.5}

    def _phase_historical_plans(
        self,
        plans: list[dict[str, Any]],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        """Phase 2: Collect and analyze historical plans."""
        try:
            total = len(plans)
            completed = sum(1 for p in plans if p.get('status') in ('completed', 'successful'))
            completion_rate = completed / max(total, 1)

            avg_steps = (
                sum(len(p.get('steps', [])) for p in plans) / max(total, 1)
            )

            analysis = {
                'total_plans': total,
                'completed_plans': completed,
                'completion_rate': completion_rate,
                'average_steps': avg_steps,
                'plan_types': _count_field(plans, 'type'),
            }
            logger.debug("phase_historical_plans_completed", count=total)
            return analysis
        except Exception as exc:
            errors.append(f"Phase 2 (HistoricalPlans) error: {exc}")
            return {'total_plans': 0, 'completion_rate': 0.0, 'average_steps': 0.0}

    def _phase_action_evaluations(
        self,
        evaluations: list[dict[str, Any]],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        """Phase 3: Incorporate action evaluation results."""
        try:
            total = len(evaluations)
            successful = sum(
                1 for e in evaluations
                if e.get('outcome_category', '') in ('successful', 'unexpectedly_beneficial')
            )
            success_rate = successful / max(total, 1)

            avg_confidence = (
                sum(e.get('confidence', 0.5) for e in evaluations) / max(total, 1)
            )

            lessons_count = sum(len(e.get('lessons', [])) for e in evaluations)

            analysis = {
                'total_evaluations': total,
                'successful_outcomes': successful,
                'success_rate': success_rate,
                'average_confidence': avg_confidence,
                'lessons_extracted': lessons_count,
                'outcome_categories': _count_field(evaluations, 'outcome_category'),
            }
            logger.debug("phase_action_evaluations_completed", count=total)
            return analysis
        except Exception as exc:
            errors.append(f"Phase 3 (ActionEvaluations) error: {exc}")
            return {'total_evaluations': 0, 'success_rate': 0.0, 'average_confidence': 0.5}

    def _phase_performance_trends(
        self,
        decisions: dict[str, Any],
        plans: dict[str, Any],
        evaluations: dict[str, Any],
        errors: list[str],
    ) -> list[PerformanceTrend]:
        """Phase 4: Detect trends in performance metrics."""
        try:
            trends: list[PerformanceTrend] = []

            # Decision success trend
            trends.append(PerformanceTrend(
                metric_name='decision_success_rate',
                direction='improving' if decisions.get('success_rate', 0) > 0.5 else 'declining',
                magnitude=abs(decisions.get('success_rate', 0.5) - 0.5),
                confidence=0.7,
                sample_size=decisions.get('total_decisions', 0),
            ))

            # Plan completion trend
            trends.append(PerformanceTrend(
                metric_name='plan_completion_rate',
                direction='improving' if plans.get('completion_rate', 0) > 0.5 else 'declining',
                magnitude=abs(plans.get('completion_rate', 0.5) - 0.5),
                confidence=0.7,
                sample_size=plans.get('total_plans', 0),
            ))

            # Evaluation outcome trend
            trends.append(PerformanceTrend(
                metric_name='evaluation_success_rate',
                direction='improving' if evaluations.get('success_rate', 0) > 0.5 else 'declining',
                magnitude=abs(evaluations.get('success_rate', 0.5) - 0.5),
                confidence=0.6,
                sample_size=evaluations.get('total_evaluations', 0),
            ))

            logger.debug("phase_performance_trends_completed", count=len(trends))
            return trends
        except Exception as exc:
            errors.append(f"Phase 4 (PerformanceTrends) error: {exc}")
            return []

    def _phase_pattern_detection(
        self,
        decisions: dict[str, Any],
        plans: dict[str, Any],
        evaluations: dict[str, Any],
        errors: list[str],
    ) -> list[PatternDetection]:
        """Phase 5: Identify recurring patterns."""
        try:
            patterns: list[PatternDetection] = []

            # Success pattern
            if decisions.get('success_rate', 0) > 0.7:
                patterns.append(PatternDetection(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type='success_pattern',
                    description=f"High decision success rate: {decisions['success_rate']:.0%}",
                    occurrences=decisions.get('successful_decisions', 0),
                    confidence=decisions.get('success_rate', 0.5),
                ))

            # Failure pattern
            if decisions.get('success_rate', 1) < 0.3 and decisions.get('total_decisions', 0) > 0:
                patterns.append(PatternDetection(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type='failure_pattern',
                    description=f"Low decision success rate: {decisions['success_rate']:.0%}",
                    occurrences=decisions.get('total_decisions', 0) - decisions.get('successful_decisions', 0),
                    confidence=1.0 - decisions.get('success_rate', 0.5),
                ))

            # Context pattern — decision type distribution
            decision_types = decisions.get('decision_types', {})
            if decision_types:
                most_common = max(decision_types, key=decision_types.get)  # type: ignore[arg-type]
                patterns.append(PatternDetection(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type='context_pattern',
                    description=f"Most frequent decision type: {most_common} ({decision_types[most_common]} occurrences)",
                    occurrences=decision_types[most_common],
                    confidence=0.8,
                ))

            # Evaluation lesson pattern
            if evaluations.get('lessons_extracted', 0) > 0:
                patterns.append(PatternDetection(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type='success_pattern',
                    description=f"Learning from evaluations: {evaluations['lessons_extracted']} lessons extracted",
                    occurrences=evaluations['lessons_extracted'],
                    confidence=0.6,
                ))

            logger.debug("phase_pattern_detection_completed", count=len(patterns))
            return patterns
        except Exception as exc:
            errors.append(f"Phase 5 (PatternDetection) error: {exc}")
            return []

    def _phase_strategy_construction(
        self,
        strategy_description: str,
        strategy_id: str,
        decisions: dict[str, Any],
        plans: dict[str, Any],
        evaluations: dict[str, Any],
        patterns: list[PatternDetection],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> StrategyObject:
        """Phase 6: Construct or update strategy objects."""
        try:
            effective_id = strategy_id or str(uuid.uuid4())

            # Determine hierarchy level from context
            hierarchy_level = ctx.get('hierarchy_level', 'execution')
            try:
                level_obj = StrategyHierarchyLevel(level=hierarchy_level)
            except ValueError:
                level_obj = StrategyHierarchyLevel(level='execution')

            # Build principles from patterns
            principles: list[str] = []
            for p in patterns:
                if p.pattern_type == 'success_pattern':
                    principles.append(f"Reinforce: {p.description}")
                elif p.pattern_type == 'failure_pattern':
                    principles.append(f"Avoid: {p.description}")

            # Build limitations from failure patterns
            limitations: list[str] = []
            for p in patterns:
                if p.pattern_type == 'failure_pattern':
                    limitations.append(p.description)

            # Compute performance from analyses
            perf_score = (
                decisions.get('success_rate', 0.5) * 0.4
                + plans.get('completion_rate', 0.5) * 0.3
                + evaluations.get('success_rate', 0.5) * 0.3
            )

            # Risk profile
            risk_level = 'low' if perf_score > 0.7 else 'medium' if perf_score > 0.4 else 'high'
            risk = RiskProfile(
                risk_level=risk_level,
                risk_factors=tuple(limitations),
                risk_score=1.0 - perf_score,
            )

            explainability = ExplainabilityMetadata(
                reasoning_chain=(
                    f"Strategy based on {decisions.get('total_decisions', 0)} decisions, "
                    f"{plans.get('total_plans', 0)} plans, "
                    f"{evaluations.get('total_evaluations', 0)} evaluations",
                    f"Detected {len(patterns)} patterns",
                    f"Performance score: {perf_score:.2f}",
                ),
                contributing_factors=tuple(
                    {'pattern': p.pattern_type, 'confidence': p.confidence}
                    for p in patterns
                ),
                confidence_decomposition={
                    'decision_data': decisions.get('average_confidence', 0.5),
                    'plan_data': plans.get('completion_rate', 0.5),
                    'evaluation_data': evaluations.get('average_confidence', 0.5),
                },
            )

            strategy = StrategyObject(
                strategy_id=effective_id,
                description=strategy_description or f"Strategy for {level_obj.level}",
                supported_goals=tuple(ctx.get('supported_goals', [])),
                underlying_principles=tuple(principles),
                supporting_evidence=tuple(p.pattern_id for p in patterns),
                historical_performance=perf_score,
                applicable_contexts=tuple(ctx.get('applicable_contexts', [level_obj.level])),
                known_limitations=tuple(limitations),
                risk_profile={
                    'risk_level': risk.risk_level,
                    'risk_score': risk.risk_score,
                    'risk_factors': list(risk.risk_factors),
                },
                confidence=perf_score,
                explainability_metadata={
                    'reasoning_chain': explainability.reasoning_chain,
                    'contributing_factors': explainability.contributing_factors,
                    'confidence_decomposition': explainability.confidence_decomposition,
                },
            )

            logger.debug("phase_strategy_construction_completed", strategy_id=effective_id)
            return strategy
        except Exception as exc:
            errors.append(f"Phase 6 (StrategyConstruction) error: {exc}")
            return StrategyObject(
                strategy_id=strategy_id or str(uuid.uuid4()),
                description=strategy_description,
            )

    def _phase_optimization(
        self,
        strategy: StrategyObject,
        trends: list[PerformanceTrend],
        patterns: list[PatternDetection],
        evaluations: dict[str, Any],
        errors: list[str],
    ) -> list[OptimizationSuggestion]:
        """Phase 7: Generate optimization suggestions."""
        try:
            suggestions: list[OptimizationSuggestion] = []

            # Suggestion from declining trends
            for trend in trends:
                if trend.direction == 'declining':
                    suggestions.append(OptimizationSuggestion(
                        suggestion_id=str(uuid.uuid4()),
                        optimization_type='parameter_tuning',
                        description=f"Address declining {trend.metric_name} (magnitude: {trend.magnitude:.2f})",
                        expected_improvement=trend.magnitude,
                        confidence=trend.confidence,
                        implementation_effort='low',
                    ))

            # Suggestion from failure patterns
            failure_patterns = [p for p in patterns if p.pattern_type == 'failure_pattern']
            if failure_patterns:
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    optimization_type='structural_change',
                    description=f"Address {len(failure_patterns)} failure patterns detected",
                    expected_improvement=sum(p.confidence for p in failure_patterns) / len(failure_patterns),
                    confidence=0.7,
                    implementation_effort='medium',
                ))

            # Suggestion from low evaluation success
            if evaluations.get('success_rate', 1.0) < 0.5 and evaluations.get('total_evaluations', 0) > 0:
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    optimization_type='context_adaptation',
                    description=f"Improve evaluation success rate from {evaluations['success_rate']:.0%}",
                    expected_improvement=0.5 - evaluations['success_rate'],
                    confidence=0.6,
                    implementation_effort='medium',
                ))

            # Suggestion for high-performing strategies to combine
            success_patterns = [p for p in patterns if p.pattern_type == 'success_pattern']
            if len(success_patterns) >= 2:
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    optimization_type='combination',
                    description=f"Combine {len(success_patterns)} successful patterns into unified approach",
                    expected_improvement=0.15,
                    confidence=0.65,
                    implementation_effort='high',
                ))

            # If no suggestions, add a monitoring suggestion
            if not suggestions:
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=str(uuid.uuid4()),
                    optimization_type='parameter_tuning',
                    description="Continue monitoring — current performance is acceptable",
                    expected_improvement=0.05,
                    confidence=0.5,
                    implementation_effort='low',
                ))

            logger.debug("phase_optimization_completed", count=len(suggestions))
            return suggestions
        except Exception as exc:
            errors.append(f"Phase 7 (Optimization) error: {exc}")
            return []

    def _phase_strategic_knowledge_base(
        self,
        strategy: StrategyObject,
        suggestions: list[OptimizationSuggestion],
        errors: list[str],
    ) -> None:
        """Phase 8: Update the strategy knowledge base."""
        try:
            self._strategies[strategy.strategy_id] = strategy

            # Track performance
            if strategy.strategy_id not in self._performance_history:
                self._performance_history[strategy.strategy_id] = []
            self._performance_history[strategy.strategy_id].append(
                strategy.historical_performance
            )

            logger.debug(
                "phase_strategic_knowledge_base_completed",
                strategy_id=strategy.strategy_id,
                total_strategies=len(self._strategies),
            )
        except Exception as exc:
            errors.append(f"Phase 8 (StrategicKnowledgeBase) error: {exc}")

    def _compute_performance(
        self,
        decisions: dict[str, Any],
        plans: dict[str, Any],
        evaluations: dict[str, Any],
    ) -> PerformanceMetrics:
        """Compute aggregate performance metrics."""
        return PerformanceMetrics(
            success_rate=(
                decisions.get('success_rate', 0.5) * 0.4
                + plans.get('completion_rate', 0.5) * 0.3
                + evaluations.get('success_rate', 0.5) * 0.3
            ),
            efficiency=plans.get('completion_rate', 0.5),
            adaptability=evaluations.get('success_rate', 0.5),
            resource_usage=max(0.0, 1.0 - plans.get('completion_rate', 0.5)),
            total_evaluations=evaluations.get('total_evaluations', 0),
            average_confidence=(
                decisions.get('average_confidence', 0.5) * 0.4
                + evaluations.get('average_confidence', 0.5) * 0.6
            ),
        )

    def get_strategy(self, strategy_id: str) -> StrategyObject | None:
        """Retrieve a strategy from the knowledge base."""
        return self._strategies.get(strategy_id)

    def get_all_strategies(self) -> tuple[StrategyObject, ...]:
        """Retrieve all strategies from the knowledge base."""
        return tuple(self._strategies.values())


def _count_field(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    """Count occurrences of a field value across a list of dicts."""
    counter: dict[str, int] = {}
    for item in items:
        val = str(item.get(field, 'unknown'))
        counter[val] = counter.get(val, 0) + 1
    return counter


def _time_range(items: list[dict[str, Any]]) -> dict[str, str]:
    """Extract time range from items with timestamp fields."""
    timestamps = [
        item.get('timestamp', '') or item.get('created_at', '')
        for item in items
        if item.get('timestamp') or item.get('created_at')
    ]
    if not timestamps:
        return {'start': '', 'end': ''}
    sorted_ts = sorted(timestamps)
    return {'start': sorted_ts[0], 'end': sorted_ts[-1]}
