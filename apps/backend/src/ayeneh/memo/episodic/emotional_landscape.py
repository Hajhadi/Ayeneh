"""Emotional landscape tracking for episodic memory (MEM-02).

Tracks emotional states, transitions, and intensity within episodes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Emotion types
# ---------------------------------------------------------------------------

PRIMARY_EMOTIONS: list[str] = [
    'joy', 'sadness', 'anger', 'fear', 'surprise', 'disgust', 'trust',
    'anticipation', 'interest', 'frustration', 'satisfaction', 'curiosity',
    'anxiety', 'pride', 'gratitude', 'shame', 'hope', 'neutral',
]

# ---------------------------------------------------------------------------
# Emotional state
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmotionalState:
    """A snapshot of emotional state at a point in time."""

    timestamp: datetime
    primary_emotion: str
    intensity: float  # 0.0 – 1.0
    secondary_emotions: tuple[str, ...] = ()
    valence: float = 0.0  # -1.0 (negative) to 1.0 (positive)
    arousal: float = 0.5  # 0.0 (calm) to 1.0 (excited)
    trigger: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Emotional transition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmotionalTransition:
    """A change from one emotional state to another."""

    from_emotion: str
    to_emotion: str
    timestamp: datetime
    intensity_change: float = 0.0
    trigger: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Emotional landscape
# ---------------------------------------------------------------------------


class EmotionalLandscape:
    """Tracks emotional states within episodes.

    Maintains a chronological sequence of emotional states and transitions,
    and provides summary statistics about the emotional arc of an episode.
    """

    def __init__(self) -> None:
        self._states: list[EmotionalState] = []
        self._transitions: list[EmotionalTransition] = []

    @property
    def states(self) -> list[EmotionalState]:
        return list(self._states)

    @property
    def transitions(self) -> list[EmotionalTransition]:
        return list(self._transitions)

    def record_state(self, state: EmotionalState) -> None:
        """Record a new emotional state and detect any transition."""
        if self._states:
            prev = self._states[-1]
            if prev.primary_emotion != state.primary_emotion or abs(prev.intensity - state.intensity) > 0.2:
                transition = EmotionalTransition(
                    from_emotion=prev.primary_emotion,
                    to_emotion=state.primary_emotion,
                    timestamp=state.timestamp,
                    intensity_change=state.intensity - prev.intensity,
                    trigger=state.trigger,
                )
                self._transitions.append(transition)
        self._states.append(state)

    def add_state(
        self,
        primary_emotion: str,
        intensity: float,
        valence: float = 0.0,
        arousal: float = 0.5,
        secondary_emotions: tuple[str, ...] = (),
        trigger: str = '',
        timestamp: datetime | None = None,
    ) -> None:
        """Convenience: record a state from raw values."""
        self.record_state(EmotionalState(
            timestamp=timestamp or datetime.now(UTC),
            primary_emotion=primary_emotion,
            intensity=min(max(intensity, 0.0), 1.0),
            secondary_emotions=secondary_emotions,
            valence=min(max(valence, -1.0), 1.0),
            arousal=min(max(arousal, 0.0), 1.0),
            trigger=trigger,
        ))

    def peak_intensity(self) -> EmotionalState | None:
        """Return the state with the highest intensity, or None."""
        if not self._states:
            return None
        return max(self._states, key=lambda s: s.intensity)

    def dominant_emotion(self) -> str | None:
        """Return the most frequently occurring primary emotion."""
        if not self._states:
            return None
        counts: dict[str, int] = {}
        for s in self._states:
            counts[s.primary_emotion] = counts.get(s.primary_emotion, 0) + 1
        return max(counts, key=lambda k: counts[k])  # type: ignore[return-value]

    def average_valence(self) -> float:
        """Return the average emotional valence across all states."""
        if not self._states:
            return 0.0
        return sum(s.valence for s in self._states) / len(self._states)

    def transition_count(self) -> int:
        return len(self._transitions)

    def summary(self) -> dict[str, Any]:
        """Return a summary dictionary of the emotional landscape."""
        peak = self.peak_intensity()
        dominant = self.dominant_emotion()
        return {
            'state_count': len(self._states),
            'transition_count': len(self._transitions),
            'dominant_emotion': dominant,
            'average_valence': self.average_valence(),
            'peak_emotion': peak.primary_emotion if peak else None,
            'peak_intensity': peak.intensity if peak else None,
        }
