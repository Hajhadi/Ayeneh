"""Awareness Level Tracking and De-Identification for COG-16 Meta-Cognition.

Tracks awareness level progression and the degree of de-identification
from automatic cognitive content.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.cog.meta_cognition.types import (
    AWARENESS_LEVELS,
    AwarenessEvent,
    MetaCognitiveObject,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# AwarenessLevelTracker
# ---------------------------------------------------------------------------


class AwarenessLevelTracker:
    """Tracks awareness level distribution and progression over time."""

    def track(self, events: list[AwarenessEvent]) -> dict[str, Any]:
        """Compute summary statistics for awareness events."""
        if not events:
            return {
                'total_events': 0,
                'level_distribution': {},
                'average_level': 0.0,
                'highest_level': 0,
                'level_progression': [],
            }

        level_counts: Counter[int] = Counter()
        for ev in events:
            level_counts[ev.awareness_level] += 1

        levels = [ev.awareness_level for ev in events]
        average_level = sum(levels) / len(levels) if levels else 0.0
        highest_level = max(levels) if levels else 0

        progression = self._compute_progression(events)

        return {
            'total_events': len(events),
            'level_distribution': dict(level_counts),
            'average_level': round(average_level, 4),
            'highest_level': highest_level,
            'level_progression': progression,
        }

    def compute_average_level(self, objects: list[MetaCognitiveObject]) -> float:
        """Compute the average awareness level across all objects."""
        if not objects:
            return 0.0
        levels = [obj.awareness_level for obj in objects]
        return round(sum(levels) / len(levels), 4)

    def detect_level_progression(self, objects: list[MetaCognitiveObject]) -> list[dict[str, Any]]:
        """Detect progression in awareness levels across objects.

        Returns a list of progression entries ordered by creation timestamp.
        """
        if not objects:
            return []

        sorted_objects = sorted(objects, key=lambda o: o.creation_timestamp)
        progression: list[dict[str, Any]] = []
        for obj in sorted_objects:
            progression.append({
                'identifier': obj.identifier,
                'awareness_level': obj.awareness_level,
                'timestamp': obj.creation_timestamp.isoformat(),
                'description': obj.awareness_description,
            })
        return progression

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_progression(events: list[AwarenessEvent]) -> list[dict[str, Any]]:
        """Compute level progression from ordered events."""
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        progression: list[dict[str, Any]] = []
        for ev in sorted_events:
            progression.append({
                'event_id': ev.event_id,
                'awareness_level': ev.awareness_level,
                'timestamp': ev.timestamp.isoformat(),
                'process': ev.recognized_process,
            })
        return progression


# ---------------------------------------------------------------------------
# DeIdentificationTracker
# ---------------------------------------------------------------------------


class DeIdentificationTracker:
    """Tracks the degree of de-identification from cognitive content."""

    def track(self, objects: list[MetaCognitiveObject]) -> dict[str, Any]:
        """Compute de-identification summary from meta-cognitive objects."""
        if not objects:
            return {
                'total_objects': 0,
                'average_de_identification': 0.0,
                'level_distribution': {},
                'objects_with_observer': 0,
            }

        de_id_scores = [self._compute_object_de_id(obj) for obj in objects]
        average = sum(de_id_scores) / len(de_id_scores) if de_id_scores else 0.0

        level_counts: Counter[int] = Counter()
        observer_count = 0
        for obj in objects:
            level_counts[obj.awareness_level] += 1
            if obj.awareness_level >= 4:
                observer_count += 1

        return {
            'total_objects': len(objects),
            'average_de_identification': round(average, 4),
            'level_distribution': dict(level_counts),
            'objects_with_observer': observer_count,
        }

    def compute_de_identification_score(self, objects: list[MetaCognitiveObject]) -> float:
        """Compute an aggregate de-identification score.

        Higher scores indicate greater capacity to observe thoughts
        without identifying with them.
        """
        if not objects:
            return 0.0

        scores = [self._compute_object_de_id(obj) for obj in objects]
        return round(sum(scores) / len(scores), 4)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_object_de_id(obj: MetaCognitiveObject) -> float:
        """Compute de-identification score for a single object.

        Higher awareness_level + higher stability → more de-identification.
        """
        level_factor = obj.awareness_level / 5.0
        stability_factor = obj.stability
        confidence_factor = obj.confidence
        return min(1.0, level_factor * 0.5 + stability_factor * 0.3 + confidence_factor * 0.2)
