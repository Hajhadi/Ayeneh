"""DEC-04 Behavioral Learning — extracts patterns and lessons from evaluations."""

from __future__ import annotations

from collections import Counter
from typing import Any

import structlog

from ayeneh.dec.action_evaluation.types import (
    ActionEvaluationObject,
    LessonLearned,
)

logger = structlog.get_logger(__name__)

LESSON_TYPES = [
    'reliable_habit',
    'recurring_mistake',
    'high_performing_strategy',
    'context_sensitive',
    'skill_development',
]


class BehavioralLearner:
    """Extracts behavioral patterns and lessons from a history of action evaluations.

    Identifies:
        - Reliable habits (consistently successful patterns)
        - Recurring mistakes (consistently failing patterns)
        - High-performing strategies (best outcomes)
        - Context-sensitive behaviors (outcome varies by context)
        - Skill development (improving over time)
    """

    def __init__(self) -> None:
        self._evaluation_history: list[ActionEvaluationObject] = []
        self._lesson_index: dict[str, list[LessonLearned]] = {}

    def ingest(self, evaluation: ActionEvaluationObject) -> list[LessonLearned]:
        """Ingest a new evaluation and extract lessons."""
        self._evaluation_history.append(evaluation)
        new_lessons = self._extract_lessons(evaluation)
        for lesson in new_lessons:
            key = lesson.lesson_type
            if key not in self._lesson_index:
                self._lesson_index[key] = []
            self._lesson_index[key].append(lesson)
        logger.info(
            "evaluation_ingested",
            evaluation_id=evaluation.evaluation_id,
            new_lessons=len(new_lessons),
            history_size=len(self._evaluation_history),
        )
        return new_lessons

    def get_reliable_habits(self) -> tuple[LessonLearned, ...]:
        """Return lessons classified as reliable habits."""
        return tuple(
            l for l in self._lesson_index.get('reliable_habit', [])
            if l.confidence >= 0.6
        )

    def get_recurring_mistakes(self) -> tuple[LessonLearned, ...]:
        """Return lessons classified as recurring mistakes."""
        return tuple(
            l for l in self._lesson_index.get('recurring_mistake', [])
            if l.confidence >= 0.4
        )

    def get_high_performing_strategies(self) -> tuple[LessonLearned, ...]:
        """Return lessons classified as high-performing strategies."""
        return tuple(
            l for l in self._lesson_index.get('high_performing_strategy', [])
            if l.confidence >= 0.7
        )

    def get_context_sensitive_behaviors(self) -> tuple[LessonLearned, ...]:
        """Return context-sensitive behavior lessons."""
        return tuple(self._lesson_index.get('context_sensitive', []))

    def get_skill_development(self) -> tuple[LessonLearned, ...]:
        """Return skill development lessons."""
        return tuple(self._lesson_index.get('skill_development', []))

    def get_all_lessons(self) -> tuple[LessonLearned, ...]:
        """Return all collected lessons, sorted by confidence descending."""
        all_lessons = []
        for lessons in self._lesson_index.values():
            all_lessons.extend(lessons)
        return tuple(sorted(all_lessons, key=lambda l: l.confidence, reverse=True))

    def get_lesson_summary(self) -> dict[str, Any]:
        """Return a summary of all lessons by type."""
        return {
            lesson_type: len(lessons)
            for lesson_type, lessons in self._lesson_index.items()
        }

    def compute_pattern_strength(self, action_description: str) -> float:
        """Compute how strongly a pattern has been observed for a given action."""
        if not self._evaluation_history:
            return 0.0

        matching = [
            e for e in self._evaluation_history
            if action_description.lower() in (e.associated_action or '').lower()
        ]

        if not matching:
            return 0.0

        # Strength increases with count and consistency of outcomes
        count_factor = min(len(matching) / 5.0, 1.0)
        confidences = [e.confidence for e in matching]
        consistency = 1.0 - _std_dev(confidences) if len(confidences) > 1 else 0.5
        return count_factor * 0.6 + consistency * 0.4

    def detect_improvement_trend(self) -> dict[str, Any]:
        """Detect whether evaluations are improving over time."""
        if len(self._evaluation_history) < 2:
            return {'trend': 'insufficient_data', 'direction': 'unknown', 'confidence': 0.0}

        mid = len(self._evaluation_history) // 2
        first_half = self._evaluation_history[:mid]
        second_half = self._evaluation_history[mid:]

        avg_first = sum(e.confidence for e in first_half) / max(len(first_half), 1)
        avg_second = sum(e.confidence for e in second_half) / max(len(second_half), 1)

        diff = avg_second - avg_first
        if diff > 0.1:
            direction = 'improving'
        elif diff < -0.1:
            direction = 'declining'
        else:
            direction = 'stable'

        return {
            'trend': 'available',
            'direction': direction,
            'first_half_avg': avg_first,
            'second_half_avg': avg_second,
            'difference': diff,
            'confidence': min(abs(diff) * 2, 1.0),
        }

    def reset(self) -> None:
        """Clear all accumulated history."""
        self._evaluation_history.clear()
        self._lesson_index.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _extract_lessons(self, evaluation: ActionEvaluationObject) -> list[LessonLearned]:
        """Extract lessons from a single evaluation."""
        lessons: list[LessonLearned] = []

        if not evaluation.lessons_learned:
            return lessons

        for lesson_text in evaluation.lessons_learned:
            lesson_type = self._classify_lesson(lesson_text, evaluation)
            lessons.append(LessonLearned(
                lesson_id=f"{evaluation.evaluation_id}-{len(lessons)}",
                lesson_text=lesson_text,
                lesson_type=lesson_type,
                confidence=evaluation.confidence,
                supporting_evaluations=(evaluation.evaluation_id,),
            ))

        return lessons

    def _classify_lesson(
        self,
        lesson_text: str,
        evaluation: ActionEvaluationObject,
    ) -> str:
        """Classify a lesson into its type based on content and context."""
        text_lower = lesson_text.lower()

        if any(kw in text_lower for kw in ['recurring', 'repeated', 'habit', 'again', 'consistently']):
            return 'reliable_habit'

        if any(kw in text_lower for kw in ['mistake', 'failed', 'error', 'wrong', 'deviation']):
            return 'recurring_mistake'

        if any(kw in text_lower for kw in ['strategy', 'successful', 'best', 'optimal', 'effective']):
            return 'high_performing_strategy'

        if any(kw in text_lower for kw in ['context', 'depends', 'varies', 'situation', 'conditional']):
            return 'context_sensitive'

        if any(kw in text_lower for kw in ['skill', 'improvement', 'development', 'learning', 'growth']):
            return 'skill_development'

        # Default classification based on confidence
        if evaluation.confidence >= 0.7:
            return 'high_performing_strategy'
        elif evaluation.confidence <= 0.3:
            return 'recurring_mistake'
        return 'context_sensitive'


def _std_dev(values: tuple[float, ...] | list[float]) -> float:
    """Compute standard deviation of a sequence of floats."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return variance ** 0.5
