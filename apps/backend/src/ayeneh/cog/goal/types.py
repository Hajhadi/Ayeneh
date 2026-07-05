"""Goal types for the Ayeneh COG architecture (COG-08).

Defines GoalObject — an intentional structure that represents a
desired future state — along with catalogue enumerations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

GOAL_CATEGORIES: list[str] = [
    'career', 'learning', 'relationship', 'health', 'creative',
    'financial', 'spiritual', 'social', 'personal_growth', 'project',
]

LIFECYCLE_STATES: list[str] = [
    'candidate', 'provisional', 'validated', 'canonical',
    'revision', 'historical',
]


# ---------------------------------------------------------------------------
# GoalObject — intentional structure
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GoalObject:
    """An intentional structure representing a desired future state.

    Goals capture what the agent is working toward, how committed they are,
    and how far they have progressed.  They link back to the values and
    beliefs that motivate them.
    """

    identifier: str
    goal_statement: str
    category: str

    # Core metrics
    confidence: float = 0.0       # does the goal exist in cognition
    priority: float = 0.0         # relative importance among goals
    commitment_strength: float = 0.0
    progress: float = 0.0         # 0.0 – 1.0
    persistence: float = 0.0      # continuation despite interruption
    flexibility: float = 0.0      # strategy revision capacity

    # Evidence links
    supporting_evidence: tuple[str, ...] = ()
    behavioural_evidence: tuple[str, ...] = ()

    # Cross-module associations
    associated_values: tuple[str, ...] = ()
    associated_beliefs: tuple[str, ...] = ()
    associated_narratives: tuple[str, ...] = ()

    # Planning
    dependencies: tuple[str, ...] = ()     # other goal IDs
    milestones: tuple[dict[str, Any], ...] = ()

    # Lifecycle
    lifecycle_state: str = 'candidate'
    creation_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    revision_history: tuple[dict[str, Any], ...] = ()
    specification_version: str = '1.0.0'
