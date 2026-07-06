"""DEC-01 Multi-Criteria Analyzer.

Evaluates decision options across independent criteria and produces
ranked MultiCriteriaScore objects.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.dec.decision_support.types import MultiCriteriaScore

logger = structlog.get_logger(__name__)

# Default weights for each criterion (sum to 1.0)
DEFAULT_CRITERIA_WEIGHTS: dict[str, float] = {
    'goal_alignment': 0.18,
    'evidence_quality': 0.12,
    'risk': 0.12,
    'opportunity': 0.10,
    'ethical': 0.15,
    'sustainability': 0.10,
    'resource_requirement': 0.08,
    'reversibility': 0.05,
    'learning_potential': 0.10,
}


class MultiCriteriaAnalyzer:
    """Evaluates decision options across independent criteria.

    Each option is scored on multiple dimensions and combined into a
    weighted overall score.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
    ) -> None:
        self._weights = weights or dict(DEFAULT_CRITERIA_WEIGHTS)

    def evaluate(
        self,
        options: tuple[dict[str, Any], ...],
        criteria_inputs: dict[str, dict[str, float]] | None = None,
    ) -> tuple[MultiCriteriaScore, ...]:
        """Evaluate all options across criteria.

        Parameters
        ----------
        options:
            Tuple of option dicts with at least a ``'name'`` key.
        criteria_inputs:
            Optional mapping of ``{option_name: {criterion: score}}``.
            If omitted, default mid-range scores are used.
        """
        logger.debug(
            'dec.multicriteria.evaluate',
            option_count=len(options),
        )

        scores: list[MultiCriteriaScore] = []
        for option in options:
            name = option.get('name', '')
            inputs = (criteria_inputs or {}).get(name, {})
            score = self._score_option(name, inputs)
            scores.append(score)

        ranked = self._rank(scores)
        logger.debug('dec.multicriteria.ranked', ranked_count=len(ranked))
        return tuple(ranked)

    def _score_option(
        self,
        name: str,
        inputs: dict[str, float],
    ) -> MultiCriteriaScore:
        """Score a single option across all criteria."""
        goal_alignment = inputs.get('goal_alignment', 0.5)
        evidence_quality = inputs.get('evidence_quality', 0.5)
        risk = inputs.get('risk', 0.5)
        opportunity = inputs.get('opportunity', 0.5)
        ethical = inputs.get('ethical', 0.7)
        sustainability = inputs.get('sustainability', 0.5)
        resource_requirement = inputs.get('resource_requirement', 0.5)
        reversibility = inputs.get('reversibility', 0.5)
        learning_potential = inputs.get('learning_potential', 0.5)

        # Lower resource_requirement is better (invert for scoring)
        resource_score = 1.0 - resource_requirement
        # Lower risk is better (invert for scoring)
        risk_score = 1.0 - risk

        overall = (
            goal_alignment * self._weights.get('goal_alignment', 0.18)
            + evidence_quality * self._weights.get('evidence_quality', 0.12)
            + risk_score * self._weights.get('risk', 0.12)
            + opportunity * self._weights.get('opportunity', 0.10)
            + ethical * self._weights.get('ethical', 0.15)
            + sustainability * self._weights.get('sustainability', 0.10)
            + resource_score * self._weights.get('resource_requirement', 0.08)
            + reversibility * self._weights.get('reversibility', 0.05)
            + learning_potential * self._weights.get('learning_potential', 0.10)
        )

        return MultiCriteriaScore(
            option=name,
            goal_alignment=round(goal_alignment, 4),
            evidence_quality=round(evidence_quality, 4),
            risk=round(risk, 4),
            opportunity=round(opportunity, 4),
            ethical=round(ethical, 4),
            sustainability=round(sustainability, 4),
            resource_requirement=round(resource_requirement, 4),
            reversibility=round(reversibility, 4),
            learning_potential=round(learning_potential, 4),
            overall=round(min(max(overall, 0.0), 1.0), 4),
        )

    def _rank(self, scores: list[MultiCriteriaScore]) -> list[MultiCriteriaScore]:
        """Sort scores by overall descending."""
        return sorted(scores, key=lambda s: s.overall, reverse=True)

    def get_top_option(self, scores: tuple[MultiCriteriaScore, ...]) -> MultiCriteriaScore | None:
        """Return the highest-ranked option."""
        if not scores:
            return None
        return max(scores, key=lambda s: s.overall)

    def compare(
        self,
        score_a: MultiCriteriaScore,
        score_b: MultiCriteriaScore,
    ) -> dict[str, Any]:
        """Compare two option scores and return differences."""
        criteria = [
            'goal_alignment', 'evidence_quality', 'risk', 'opportunity',
            'ethical', 'sustainability', 'resource_requirement',
            'reversibility', 'learning_potential',
        ]

        differences: dict[str, float] = {}
        for c in criteria:
            val_a = getattr(score_a, c)
            val_b = getattr(score_b, c)
            differences[c] = round(val_a - val_b, 4)

        return {
            'option_a': score_a.option,
            'option_b': score_b.option,
            'differences': differences,
            'overall_difference': round(score_a.overall - score_b.overall, 4),
            'winner': score_a.option if score_a.overall >= score_b.overall else score_b.option,
        }
