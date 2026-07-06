"""DEC-05 Strategy Optimization — domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any


STRATEGY_HIERARCHY_LEVELS = [
    'life_strategy',
    'domain_strategy',
    'project_strategy',
    'problem_solving',
    'learning',
    'decision',
    'execution',
    'micro',
]

STRATEGY_STATUS = ['active', 'inactive', 'deprecated', 'experimental']

OPTIMIZATION_TYPES = [
    'parameter_tuning',
    'structural_change',
    'context_adaptation',
    'combination',
    'replacement',
]


@dataclass(frozen=True)
class StrategyHierarchyLevel:
    """Classifies a strategy's position in the hierarchy."""

    level: str = 'execution'
    parent_level: str = ''
    scope: str = ''

    def __post_init__(self) -> None:
        if self.level not in STRATEGY_HIERARCHY_LEVELS:
            raise ValueError(
                f"Invalid hierarchy level: {self.level!r}. "
                f"Must be one of {STRATEGY_HIERARCHY_LEVELS}"
            )


@dataclass(frozen=True)
class PerformanceMetrics:
    """Quantitative metrics for strategy performance."""

    success_rate: float = 0.0
    efficiency: float = 0.0
    adaptability: float = 0.0
    resource_usage: float = 0.0
    time_to_completion: float = 0.0
    total_evaluations: int = 0
    average_confidence: float = 0.0

    @property
    def overall_score(self) -> float:
        """Weighted composite performance score."""
        return (
            self.success_rate * 0.35
            + self.efficiency * 0.25
            + self.adaptability * 0.20
            + (1.0 - self.resource_usage) * 0.10
            + self.average_confidence * 0.10
        )


@dataclass(frozen=True)
class RiskProfile:
    """Risk characteristics of a strategy."""

    risk_level: str = 'medium'  # 'low', 'medium', 'high', 'critical'
    risk_factors: tuple[str, ...] = ()
    mitigation_strategies: tuple[str, ...] = ()
    worst_case_scenario: str = ''
    risk_score: float = 0.5


@dataclass(frozen=True)
class OptimizationSuggestion:
    """A suggestion for optimizing a strategy."""

    suggestion_id: str = ''
    optimization_type: str = 'parameter_tuning'
    description: str = ''
    expected_improvement: float = 0.0
    confidence: float = 0.0
    implementation_effort: str = 'low'  # 'low', 'medium', 'high'
    prerequisites: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.optimization_type not in OPTIMIZATION_TYPES:
            raise ValueError(
                f"Invalid optimization type: {self.optimization_type!r}. "
                f"Must be one of {OPTIMIZATION_TYPES}"
            )


@dataclass(frozen=True)
class PerformanceTrend:
    """Describes a detected trend in performance metrics."""

    metric_name: str = ''
    direction: str = 'stable'  # 'improving', 'declining', 'stable', 'volatile'
    magnitude: float = 0.0
    confidence: float = 0.0
    sample_size: int = 0
    time_window: str = ''


@dataclass(frozen=True)
class PatternDetection:
    """A pattern detected across historical decisions and evaluations."""

    pattern_id: str = ''
    pattern_type: str = ''  # 'success_pattern', 'failure_pattern', 'context_pattern', 'timing_pattern'
    description: str = ''
    occurrences: int = 0
    confidence: float = 0.0
    supporting_data: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Metadata supporting explanation of strategy decisions."""

    reasoning_chain: tuple[str, ...] = ()
    contributing_factors: tuple[dict[str, Any], ...] = ()
    confidence_decomposition: dict[str, float] = field(default_factory=dict)
    alternatives_considered: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrategyObject:
    """Core domain object for a strategy."""

    strategy_id: str = ''
    description: str = ''
    supported_goals: tuple[str, ...] = ()
    underlying_principles: tuple[str, ...] = ()
    supporting_evidence: tuple[str, ...] = ()
    historical_performance: float = 0.0
    applicable_contexts: tuple[str, ...] = ()
    known_limitations: tuple[str, ...] = ()
    risk_profile: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    revision_history: tuple[dict[str, Any], ...] = ()
    version_metadata: dict[str, Any] = field(default_factory=dict)
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyOptimizationResult:
    """Complete result from the StrategyOptimizationEngine pipeline."""

    strategy_id: str = ''
    strategy: StrategyObject | None = None
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    trends: tuple[PerformanceTrend, ...] = ()
    patterns: tuple[PatternDetection, ...] = ()
    suggestions: tuple[OptimizationSuggestion, ...] = ()
    confidence: float = 0.0
    duration_ms: float = 0.0
    errors: tuple[str, ...] = ()

    @property
    def has_suggestions(self) -> bool:
        return len(self.suggestions) > 0
