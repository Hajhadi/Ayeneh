"""Episode boundary detection for the episodic memory engine (MEM-02).

Detects boundaries between episodes based on multiple signals:
primary goal completion, context transition, identity shift, project
completion, major interruption, and persistent inactivity.
"""

from __future__ import annotations

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.types import Event

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Boundary signals
# ---------------------------------------------------------------------------

BOUNDARY_SIGNAL_TYPES: list[str] = [
    'goal_completion',
    'context_transition',
    'identity_shift',
    'project_completion',
    'major_interruption',
    'persistent_inactivity',
]

DEFAULT_INACTIVITY_THRESHOLD_SECONDS: float = 1800.0  # 30 minutes


# ---------------------------------------------------------------------------
# Boundary record
# ---------------------------------------------------------------------------


class EpisodeBoundary:
    """A detected boundary between episodes."""

    __slots__ = ('signal_type', 'timestamp', 'confidence', 'evidence', 'metadata')

    def __init__(
        self,
        signal_type: str,
        timestamp: datetime,
        confidence: float = 1.0,
        evidence: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.signal_type = signal_type
        self.timestamp = timestamp
        self.confidence = confidence
        self.evidence = evidence
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            'signal_type': self.signal_type,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence,
            'evidence': list(self.evidence),
            'metadata': self.metadata,
        }


# ---------------------------------------------------------------------------
# Boundary detector
# ---------------------------------------------------------------------------


class EpisodeBoundaryDetector:
    """Detects episode boundaries from a stream of events.

    Runs as the 5th phase in the episodic memory engine pipeline.
    """

    def __init__(
        self,
        inactivity_threshold_seconds: float = DEFAULT_INACTIVITY_THRESHOLD_SECONDS,
    ) -> None:
        self._inactivity_threshold = inactivity_threshold_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_boundaries(self, events: list[Event]) -> list[EpisodeBoundary]:
        """Analyze a sequence of events and return detected boundaries."""
        if not events:
            return []

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        boundaries: list[EpisodeBoundary] = []

        for i, event in enumerate(sorted_events):
            # Goal completion
            if self._is_goal_completion(event):
                boundaries.append(EpisodeBoundary(
                    signal_type='goal_completion',
                    timestamp=event.timestamp,
                    confidence=event.confidence,
                    evidence=(event.event_id,),
                    metadata={'event_description': event.description},
                ))

            # Context transition
            if i > 0:
                prev = sorted_events[i - 1]
                if self._is_context_transition(prev, event):
                    boundaries.append(EpisodeBoundary(
                        signal_type='context_transition',
                        timestamp=event.timestamp,
                        evidence=(prev.event_id, event.event_id),
                    ))

            # Identity shift
            if self._is_identity_shift(event):
                boundaries.append(EpisodeBoundary(
                    signal_type='identity_shift',
                    timestamp=event.timestamp,
                    confidence=event.confidence * 0.9,
                    evidence=(event.event_id,),
                    metadata={'event_description': event.description},
                ))

            # Project completion
            if self._is_project_completion(event):
                boundaries.append(EpisodeBoundary(
                    signal_type='project_completion',
                    timestamp=event.timestamp,
                    confidence=event.confidence,
                    evidence=(event.event_id,),
                ))

            # Major interruption
            if self._is_major_interruption(event):
                boundaries.append(EpisodeBoundary(
                    signal_type='major_interruption',
                    timestamp=event.timestamp,
                    confidence=event.confidence * 0.8,
                    evidence=(event.event_id,),
                ))

            # Persistent inactivity
            if i > 0:
                prev = sorted_events[i - 1]
                gap = (event.timestamp - prev.timestamp).total_seconds()
                if gap >= self._inactivity_threshold:
                    boundaries.append(EpisodeBoundary(
                        signal_type='persistent_inactivity',
                        timestamp=event.timestamp,
                        confidence=min(1.0, gap / (self._inactivity_threshold * 2)),
                        evidence=(prev.event_id, event.event_id),
                        metadata={'gap_seconds': gap},
                    ))

        boundaries.sort(key=lambda b: b.timestamp)
        logger.debug(
            'episode_boundaries_detected',
            count=len(boundaries),
            signals=[b.signal_type for b in boundaries],
        )
        return boundaries

    # ------------------------------------------------------------------
    # Signal detectors (extensible hooks)
    # ------------------------------------------------------------------

    def _is_goal_completion(self, event: Event) -> bool:
        desc = event.description.lower()
        return any(kw in desc for kw in ('completed', 'finished', 'achieved', 'done', 'accomplished'))

    def _is_context_transition(self, prev: Event, current: Event) -> bool:
        prev_source = prev.metadata.get('source_context', prev.source_observations[0] if prev.source_observations else '')
        curr_source = current.metadata.get('source_context', current.source_observations[0] if current.source_observations else '')
        return prev_source != curr_source

    def _is_identity_shift(self, event: Event) -> bool:
        desc = event.description.lower()
        return any(kw in desc for kw in ('realized i am', 'identity', 'who i am', 'self-concept', 'core belief'))

    def _is_project_completion(self, event: Event) -> bool:
        return (
            event.event_type == 'project'
            and any(kw in event.description.lower() for kw in ('completed', 'finished', 'delivered'))
        )

    def _is_major_interruption(self, event: Event) -> bool:
        desc = event.description.lower()
        return event.event_type == 'interruption' or any(
            kw in desc for kw in ('interrupted', 'crisis', 'emergency', 'abruptly stopped')
        )
