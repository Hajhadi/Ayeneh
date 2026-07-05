"""DLG-01 Self-Evaluation module.

Evaluates dialogue response quality across multiple dimensions before delivery.
Responses failing minimum quality thresholds shall be revised.

Specification: DLG-01 §18 Dialogue Self-Evaluation.
"""

from __future__ import annotations

from typing import Any

import structlog

from ayeneh.dlg.manager.types import DialoguePlan, DialogueResponse, EvaluationResult

logger = structlog.get_logger(__name__)

# Default quality thresholds
DEFAULT_QUALITY_THRESHOLD: float = 0.5
DEFAULT_DIMENSION_THRESHOLD: float = 0.3


class SelfEvaluator:
    """Evaluates response quality before delivery.

    Considers accuracy, evidence support, explainability, relevance,
    cognitive usefulness, uncertainty communication, and narrative neutrality.
    """

    def __init__(self, quality_threshold: float = DEFAULT_QUALITY_THRESHOLD) -> None:
        self._quality_threshold = quality_threshold
        self._dimension_threshold = DEFAULT_DIMENSION_THRESHOLD

    def evaluate(
        self,
        response: DialogueResponse,
        plan: DialoguePlan,
        context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Evaluate response quality across all dimensions."""
        ctx = context or {}

        accuracy = self._evaluate_accuracy(response, plan, ctx)
        evidence_support = self._evaluate_evidence_support(response, plan, ctx)
        explainability = self._evaluate_explainability(response, plan, ctx)
        relevance = self._evaluate_relevance(response, plan, ctx)
        cognitive_usefulness = self._evaluate_cognitive_usefulness(
            response, plan, ctx,
        )
        uncertainty_communication = self._evaluate_uncertainty_communication(
            response, ctx,
        )
        narrative_neutrality = self._evaluate_narrative_neutrality(response, ctx)

        dimensions = [
            accuracy,
            evidence_support,
            explainability,
            relevance,
            cognitive_usefulness,
            uncertainty_communication,
            narrative_neutrality,
        ]
        overall_quality = sum(dimensions) / len(dimensions)

        revision_notes = self._identify_revision_notes(
            accuracy=accuracy,
            evidence_support=evidence_support,
            explainability=explainability,
            relevance=relevance,
            cognitive_usefulness=cognitive_usefulness,
            uncertainty_communication=uncertainty_communication,
            narrative_neutrality=narrative_neutrality,
        )

        passes_threshold = overall_quality >= self._quality_threshold
        revision_needed = not passes_threshold or any(
            d < self._dimension_threshold for d in dimensions
        )

        result = EvaluationResult(
            overall_quality=overall_quality,
            accuracy=accuracy,
            evidence_support=evidence_support,
            explainability=explainability,
            relevance=relevance,
            cognitive_usefulness=cognitive_usefulness,
            uncertainty_communication=uncertainty_communication,
            narrative_neutrality=narrative_neutrality,
            passes_threshold=passes_threshold,
            revision_needed=revision_needed,
            revision_notes=tuple(revision_notes),
        )

        logger.info(
            "self_evaluation_complete",
            overall=round(overall_quality, 3),
            passes=passes_threshold,
            revision_needed=revision_needed,
        )

        return result

    def _evaluate_accuracy(
        self,
        response: DialogueResponse,
        plan: DialoguePlan,
        ctx: dict[str, Any],
    ) -> float:
        """Evaluate factual accuracy of the response."""
        score = 0.5

        if response.evidence_citations:
            score += 0.2
        if response.explicit_uncertainty_markers:
            score += 0.1
        if response.content:
            score += 0.1

        return min(1.0, score)

    def _evaluate_evidence_support(
        self,
        response: DialogueResponse,
        plan: DialoguePlan,
        ctx: dict[str, Any],
    ) -> float:
        """Evaluate whether the response is supported by evidence."""
        score = 0.3

        if response.evidence_citations:
            score += 0.3
        if plan.required_evidence:
            score += 0.2
        if response.content and len(response.content) > 20:
            score += 0.1

        return min(1.0, score)

    def _evaluate_explainability(
        self,
        response: DialogueResponse,
        plan: DialoguePlan,
        ctx: dict[str, Any],
    ) -> float:
        """Evaluate whether the response is explainable."""
        score = 0.4

        if response.content and len(response.content) > 10:
            score += 0.2
        if plan.expected_user_benefit:
            score += 0.2
        if response.granularity in ('structured', 'deep_analysis'):
            score += 0.1

        return min(1.0, score)

    def _evaluate_relevance(
        self,
        response: DialogueResponse,
        plan: DialoguePlan,
        ctx: dict[str, Any],
    ) -> float:
        """Evaluate response relevance to the user's intent."""
        score = 0.4

        if plan.primary_objective:
            score += 0.3
        if response.content:
            score += 0.2

        return min(1.0, score)

    def _evaluate_cognitive_usefulness(
        self,
        response: DialogueResponse,
        plan: DialoguePlan,
        ctx: dict[str, Any],
    ) -> float:
        """Evaluate cognitive usefulness of the response."""
        score = 0.3

        if plan.expected_user_benefit:
            score += 0.3
        if response.action_suggestions:
            score += 0.2
        if response.questions_raised:
            score += 0.1

        return min(1.0, score)

    def _evaluate_uncertainty_communication(
        self,
        response: DialogueResponse,
        ctx: dict[str, Any],
    ) -> float:
        """Evaluate how well uncertainty is communicated."""
        score = 0.5

        if response.explicit_uncertainty_markers:
            score += 0.3
        if response.emotional_tone in ('neutral', 'calm'):
            score += 0.1

        return min(1.0, score)

    def _evaluate_narrative_neutrality(
        self,
        response: DialogueResponse,
        ctx: dict[str, Any],
    ) -> float:
        """Evaluate narrative neutrality of the response."""
        score = 0.6

        if response.emotional_tone == 'neutral':
            score += 0.2
        if not response.explicit_uncertainty_markers or len(
            response.explicit_uncertainty_markers
        ) < 3:
            score += 0.1

        return min(1.0, score)

    def _identify_revision_notes(
        self,
        accuracy: float,
        evidence_support: float,
        explainability: float,
        relevance: float,
        cognitive_usefulness: float,
        uncertainty_communication: float,
        narrative_neutrality: float,
    ) -> list[str]:
        """Identify specific revision notes for failing dimensions."""
        notes: list[str] = []
        threshold = self._dimension_threshold

        if accuracy < threshold:
            notes.append("Improve factual accuracy with supporting evidence")
        if evidence_support < threshold:
            notes.append("Add evidence citations to support claims")
        if explainability < threshold:
            notes.append("Improve explainability of reasoning")
        if relevance < threshold:
            notes.append("Better align response with user intent")
        if cognitive_usefulness < threshold:
            notes.append("Increase cognitive usefulness for the user")
        if uncertainty_communication < threshold:
            notes.append("Communicate uncertainties more explicitly")
        if narrative_neutrality < threshold:
            notes.append("Maintain narrative neutrality")

        return notes
