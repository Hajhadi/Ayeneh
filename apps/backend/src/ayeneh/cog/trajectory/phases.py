"""Developmental Phases — COG-13 support module.

Identifies developmental phases and transitional periods from cognitive
trajectories. Phases represent stable periods; transitional periods
represent times of active reorganization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.cog.trajectory.types import TrajectoryObject

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# DevelopmentalPhase
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DevelopmentalPhase:
    """A stable period of cognitive development.

    Characterized by consistent patterns of change across multiple
    cognitive structures during a defined time period.
    """

    phase_id: str
    description: str
    start_estimate: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_estimate: datetime | None = None
    dominant_characteristics: tuple[str, ...] = ()
    stability_score: float = 0.0


# ---------------------------------------------------------------------------
# TransitionalPeriod
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionalPeriod:
    """A period of active cognitive reorganization.

    Characterized by instability, competing structures, and rapid change
    across multiple cognitive domains.
    """

    period_id: str
    description: str
    characteristics: tuple[str, ...] = ()  # identity_revision|belief_instability|competing_narratives|goal_restructuring
    uncertainty_level: float = 0.0


# ---------------------------------------------------------------------------
# Phase Identifier
# ---------------------------------------------------------------------------


class PhaseIdentifier:
    """Identifies developmental phases and transitional periods from trajectories."""

    def identify(
        self,
        trajectories: list[TrajectoryObject],
    ) -> tuple[list[DevelopmentalPhase], list[TransitionalPeriod]]:
        """Identify phases and transitional periods.

        Parameters
        ----------
        trajectories:
            List of TrajectoryObject instances to analyze.
        """
        logger.info('cog.trajectory.phase_identification_started')

        phases: list[DevelopmentalPhase] = []
        transitions: list[TransitionalPeriod] = []

        if not trajectories:
            return phases, transitions

        # Group trajectories by direction
        direction_groups: dict[str, list[TrajectoryObject]] = {}
        for traj in trajectories:
            direction = traj.direction or 'stabilizing'
            direction_groups.setdefault(direction, []).append(traj)

        # Identify phases from dominant direction groups
        for direction, group in direction_groups.items():
            if len(group) < 1:
                continue

            avg_stability = sum(t.historical_continuity for t in group) / len(group)
            avg_rate = sum(t.rate_of_change for t in group) / len(group)

            # Determine phase characteristics
            characteristics = _infer_phase_characteristics(direction, avg_rate, group)

            phase = DevelopmentalPhase(
                phase_id=str(_stable_id(direction, len(phases))),
                description=f"Phase of {direction} across {len(group)} cognitive structures",
                dominant_characteristics=characteristics,
                stability_score=avg_stability,
            )
            phases.append(phase)

        # Identify transitional periods (high change rate, mixed directions)
        mixed_directions = [
            d for d, g in direction_groups.items()
            if d in ('transforming', 'fragmenting', 'integrating')
        ]
        if len(mixed_directions) >= 1 or any(
            t.rate_of_change > 0.5 for t in trajectories
        ):
            high_change = [
                t for t in trajectories if t.rate_of_change > 0.5
            ]
            if high_change:
                characteristics = _infer_transitional_characteristics(high_change)
                uncertainty = sum(t.rate_of_change for t in high_change) / len(high_change)

                transition = TransitionalPeriod(
                    period_id=str(_stable_id('transition', 0)),
                    description=(
                        f"Transitional period involving {len(high_change)} "
                        f"cognitive structures with elevated change rates"
                    ),
                    characteristics=characteristics,
                    uncertainty_level=min(1.0, uncertainty),
                )
                transitions.append(transition)

        logger.info(
            'cog.trajectory.phases_identified',
            phase_count=len(phases),
            transition_count=len(transitions),
        )
        return phases, transitions


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _infer_phase_characteristics(
    direction: str,
    avg_rate: float,
    group: list[TrajectoryObject],
) -> tuple[str, ...]:
    """Infer dominant characteristics of a developmental phase."""
    characteristics: list[str] = []

    # Direction-based characteristics
    dir_chars: dict[str, str] = {
        'strengthening': 'consolidation',
        'weakening': 'destabilization',
        'stabilizing': 'stability',
        'fragmenting': 'fragmentation',
        'integrating': 'integration',
        'transforming': 'transformation',
    }
    if direction in dir_chars:
        characteristics.append(dir_chars[direction])

    # Rate-based characteristics
    if avg_rate > 0.7:
        characteristics.append('rapid_change')
    elif avg_rate > 0.3:
        characteristics.append('moderate_change')
    else:
        characteristics.append('stability')

    # Type-based characteristics
    target_types = {t.target_type for t in group}
    if 'identity' in target_types:
        characteristics.append('identity_work')
    if 'belief' in target_types:
        characteristics.append('belief_revision')
    if 'value' in target_types:
        characteristics.append('value_clarification')
    if 'goal' in target_types:
        characteristics.append('goal_restructuring')

    return tuple(characteristics)


def _infer_transitional_characteristics(
    high_change_trajectories: list[TrajectoryObject],
) -> tuple[str, ...]:
    """Infer characteristics of a transitional period."""
    characteristics: list[str] = []

    target_types = {t.target_type for t in high_change_trajectories}
    directions = {t.direction for t in high_change_trajectories}

    if 'identity' in target_types:
        characteristics.append('identity_revision')
    if 'belief' in target_types and 'weakening' in directions:
        characteristics.append('belief_instability')
    if 'narrative' in target_types:
        characteristics.append('competing_narratives')
    if 'goal' in target_types:
        characteristics.append('goal_restructuring')

    if not characteristics:
        characteristics.append('general_reorganization')

    return tuple(characteristics)


def _stable_id(prefix: str, index: int) -> str:
    """Generate a deterministic ID for phases."""
    return f"{prefix}-phase-{index}"
