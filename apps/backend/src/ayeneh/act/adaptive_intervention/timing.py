"""ACT-03 Timing Intelligence.

Evaluates intervention timing based on cognitive load, task phase,
emotional intensity, goal urgency, progress, and environment.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.act.adaptive_intervention.types import (
    TIMING_ASSESSMENTS,
    TimingAssessment,
)

logger = structlog.get_logger(__name__)


class TimingIntelligence:
    """Evaluates the quality of intervention timing.

    Factors:
        - Cognitive load
        - Task phase
        - Emotional intensity
        - Goal urgency
        - Progress level
        - Environment fitness
    """

    def __init__(self) -> None:
        self._history: list[TimingAssessment] = []

    def evaluate(
        self,
        context: dict[str, Any],
    ) -> TimingAssessment:
        """Evaluate timing quality for a potential intervention.

        Parameters
        ----------
        context:
            Dict with optional keys: ``cognitive_load``, ``task_phase``,
            ``emotional_intensity``, ``goal_urgency``, ``progress_level``,
            ``environment_fitness``.
        """
        cognitive_load = max(
            0.0, min(1.0, context.get('cognitive_load', 0.5)),
        )
        task_phase = context.get('task_phase', 'execution')
        emotional_intensity = max(
            0.0, min(1.0, context.get('emotional_intensity', 0.3)),
        )
        goal_urgency = max(
            0.0, min(1.0, context.get('goal_urgency', 0.5)),
        )
        progress_level = max(
            0.0, min(1.0, context.get('progress_level', 0.5)),
        )
        environment_fitness = max(
            0.0, min(1.0, context.get('environment_fitness', 0.5)),
        )

        overall = self._compute_overall_timing(
            cognitive_load,
            task_phase,
            emotional_intensity,
            goal_urgency,
            progress_level,
            environment_fitness,
        )

        assessment = TimingAssessment(
            assessment_id=str(uuid.uuid4()),
            cognitive_load=cognitive_load,
            task_phase=task_phase,
            emotional_intensity=emotional_intensity,
            goal_urgency=goal_urgency,
            progress_level=progress_level,
            environment_fitness=environment_fitness,
            overall_timing=overall,
        )

        self._history.append(assessment)

        logger.debug(
            'act.adaptive_intervention.timing.evaluated',
            overall=overall,
            cognitive_load=cognitive_load,
        )
        return assessment

    def _compute_overall_timing(
        self,
        cognitive_load: float,
        task_phase: str,
        emotional_intensity: float,
        goal_urgency: float,
        progress_level: float,
        environment_fitness: float,
    ) -> str:
        """Compute the overall timing assessment."""
        score = 0.0

        if cognitive_load > 0.8:
            score -= 2
        elif cognitive_load > 0.6:
            score -= 1
        elif cognitive_load < 0.3:
            score += 1

        phase_scores = {
            'planning': 1,
            'execution': 0,
            'reflection': 1,
            'completion': 0,
            'idle': 1,
        }
        score += phase_scores.get(task_phase, 0)

        if emotional_intensity > 0.7:
            score -= 1
        elif emotional_intensity < 0.3:
            score += 1

        if goal_urgency > 0.7:
            score += 2
        elif goal_urgency > 0.4:
            score += 1

        if progress_level > 0.8:
            score += 1
        elif progress_level < 0.2:
            score -= 1

        if environment_fitness > 0.6:
            score += 1
        elif environment_fitness < 0.3:
            score -= 1

        if score >= 3:
            return 'optimal'
        if score >= 1:
            return 'acceptable'
        if score >= -1:
            return 'suboptimal'
        if score >= -3:
            return 'premature'
        return 'too_late'

    def get_history(self) -> tuple[TimingAssessment, ...]:
        """Return all past timing assessments."""
        return tuple(self._history)

    def get_latest(self) -> TimingAssessment | None:
        """Return the most recent timing assessment."""
        return self._history[-1] if self._history else None
