"""Awakening Dynamics — COG-12 support module.

Models the progression from automatic to aware cognition through
eight levels: automatic → pattern_recognition → observation → understanding
→ experimentation → behavioral_change → identity_revision → integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Awakening levels
# ---------------------------------------------------------------------------

AWAKENING_LEVELS: list[str] = [
    'automatic',
    'pattern_recognition',
    'observation',
    'understanding',
    'experimentation',
    'behavioral_change',
    'identity_revision',
    'integration',
]


# ---------------------------------------------------------------------------
# AwakeningProgress
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AwakeningProgress:
    """Tracks the user's progression through awareness levels.

    Levels (0-7):
        0. automatic — no awareness, fully reactive
        1. pattern_recognition — noticing patterns exist
        2. observation — actively observing own cognition
        3. understanding — grasping why patterns exist
        4. experimentation — trying different approaches
        5. behavioral_change — sustained behavioral shifts
        6. identity_revision — updating self-concept
        7. integration — new patterns are default
    """

    current_level: int = 0  # 0-7
    confidence: float = 0.0
    evidence: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Awakening Dynamics
# ---------------------------------------------------------------------------


class AwakeningDynamics:
    """Estimates the user's current level of cognitive awareness.

    Analyzes meta-cognition events and reflection events to determine
    where the user falls on the automatic→integration spectrum.
    """

    def estimate_level(
        self,
        meta_cognition_events: list[dict[str, Any]],
        reflection_events: list[dict[str, Any]],
    ) -> AwakeningProgress:
        """Estimate the current awakening level.

        Parameters
        ----------
        meta_cognition_events:
            Events where the user demonstrated meta-cognition (e.g., "I noticed
            that I tend to…"). Each dict has ``'text'`` and optional ``'type'``.
        reflection_events:
            Events where the user reflected on cognition (e.g., "I realized
            my belief about X comes from Y"). Each dict has ``'text'`` and
            optional ``'type'``.
        """
        logger.info('cog.reflection.awakening_estimation_started')

        if not meta_cognition_events and not reflection_events:
            return AwakeningProgress(current_level=0, confidence=1.0)

        # Score each event against level indicators
        level_scores: dict[int, float] = {i: 0.0 for i in range(8)}
        evidence_ids: list[str] = []

        for event in meta_cognition_events:
            level = _classify_meta_cognition_level(event)
            level_scores[level] += 1.0
            eid = event.get('id', '')
            if eid:
                evidence_ids.append(eid)

        for event in reflection_events:
            level = _classify_reflection_level(event)
            level_scores[level] += 1.5  # Reflections weighted higher
            eid = event.get('id', '')
            if eid:
                evidence_ids.append(eid)

        # Determine highest level with meaningful support
        total_events = len(meta_cognition_events) + len(reflection_events)
        current_level = 0
        for level in range(7, -1, -1):
            if level_scores[level] > 0:
                # Need at least 1 event at this level or higher
                supporting = sum(
                    level_scores[l] for l in range(level, 8)
                )
                if supporting >= 1.0:
                    current_level = level
                    break

        # Confidence based on evidence density
        confidence = min(1.0, total_events * 0.15)

        result = AwakeningProgress(
            current_level=current_level,
            confidence=confidence,
            evidence=tuple(evidence_ids),
        )

        logger.info(
            'cog.reflection.awakening_estimated',
            level=current_level,
            level_name=AWAKENING_LEVELS[current_level],
            confidence=confidence,
        )
        return result


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _classify_meta_cognition_level(event: dict[str, Any]) -> int:
    """Classify a meta-cognition event into an awakening level (0-7)."""
    text = event.get('text', '').lower()
    event_type = event.get('type', '')

    # Level 6-7: identity_revision, integration
    if any(kw in text for kw in ('identity', 'who i am', 'core self', 'fundamental')):
        return 6
    if event_type in ('identity_revision', 'integration'):
        return 6

    # Level 5: behavioral_change
    if any(kw in text for kw in ('changed', 'stopped', 'started doing', 'new habit')):
        return 5
    if event_type == 'behavior_change':
        return 5

    # Level 4: experimentation
    if any(kw in text for kw in ('tried', 'experiment', 'tested', 'attempted')):
        return 4
    if event_type == 'experimentation':
        return 4

    # Level 3: understanding
    if any(kw in text for kw in ('because', 'reason', 'why', 'understand', 'realize')):
        return 3
    if event_type == 'understanding':
        return 3

    # Level 2: observation
    if any(kw in text for kw in ('notice', 'observe', 'aware', 'tend to')):
        return 2
    if event_type == 'observation':
        return 2

    # Level 1: pattern_recognition
    if any(kw in text for kw in ('pattern', 'always', 'never', 'often', 'typically')):
        return 1
    if event_type == 'pattern_recognition':
        return 1

    # Level 0: automatic
    return 0


def _classify_reflection_level(event: dict[str, Any]) -> int:
    """Classify a reflection event into an awakening level (0-7)."""
    text = event.get('text', '').lower()
    event_type = event.get('type', '')

    # Reflections inherently require at least level 2 (observation)
    if event_type in ('identity_revision', 'integration'):
        return 6
    if event_type == 'behavior_change':
        return 5
    if event_type == 'experimentation':
        return 4
    if event_type == 'understanding':
        return 3

    # Text-based classification
    if any(kw in text for kw in ('identity', 'who i am', 'fundamental')):
        return 6
    if any(kw in text for kw in ('changed', 'stopped', 'new approach')):
        return 5
    if any(kw in text for kw in ('tried', 'experiment')):
        return 4
    if any(kw in text for kw in ('because', 'reason', 'understand')):
        return 3

    # Default for any reflection: at least observation level
    return 2
