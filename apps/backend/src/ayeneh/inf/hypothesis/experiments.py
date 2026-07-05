"""INF-05 Cognitive Experiments.

Defines safe, controlled experiments that test hypotheses against
real-world cognitive data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


EXPERIMENT_STATUSES: list[str] = [
    'planned',
    'active',
    'completed',
    'abandoned',
]

SAFETY_LEVELS: list[str] = [
    'safe',
    'caution',
    'unsafe',
]


@dataclass(frozen=True)
class CognitiveExperiment:
    """A controlled experiment designed to test a hypothesis."""

    experiment_id: str
    hypothesis_id: str
    description: str = ''
    expected_outcome: str = ''
    safety_check: str = 'safe'
    status: str = 'planned'
    parameters: dict[str, Any] = field(default_factory=dict)
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ExperimentResult:
    """The outcome of a completed cognitive experiment."""

    experiment_id: str
    observed_outcome: str = ''
    supports_hypothesis: bool = False
    confidence_change: float = 0.0
    notes: str = ''
    completion_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class ExperimentPlanner:
    """Plans and manages cognitive experiments."""

    def plan_experiment(
        self,
        hypothesis_id: str,
        hypothesis_statement: str,
        predictions: tuple[str, ...] = (),
    ) -> CognitiveExperiment:
        """Create a planned experiment for a hypothesis."""
        description = f"Test hypothesis: {hypothesis_statement}"
        expected = '; '.join(predictions) if predictions else 'Observable pattern change'
        return CognitiveExperiment(
            experiment_id=f'exp_{hypothesis_id}',
            hypothesis_id=hypothesis_id,
            description=description,
            expected_outcome=expected,
            safety_check='safe',
            status='planned',
        )

    def evaluate_result(
        self,
        experiment: CognitiveExperiment,
        observed_outcome: str,
        supports: bool,
    ) -> ExperimentResult:
        """Evaluate the result of a completed experiment."""
        if supports:
            delta = 0.1
        else:
            delta = -0.15
        return ExperimentResult(
            experiment_id=experiment.experiment_id,
            observed_outcome=observed_outcome,
            supports_hypothesis=supports,
            confidence_change=delta,
            notes=f"Observed: {observed_outcome}",
        )

    def is_safe(self, experiment: CognitiveExperiment) -> bool:
        """Check whether an experiment is safe to run."""
        return experiment.safety_check in ('safe', 'caution')
