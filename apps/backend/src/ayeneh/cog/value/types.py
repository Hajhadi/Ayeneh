"""Value types for the Ayeneh COG architecture (COG-07).

Defines ValueObject — an enduring principle that guides behaviour and
decision-making — along with catalogue enumerations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

VALUE_CATEGORIES: list[str] = [
    'relationship', 'achievement', 'growth', 'security', 'freedom',
    'authenticity', 'compassion', 'justice', 'knowledge', 'creativity',
    'spirituality', 'health', 'community', 'family', 'autonomy',
]

LIFECYCLE_STATES: list[str] = [
    'candidate', 'provisional', 'validated', 'canonical',
    'revision', 'historical',
]

DECLARED_VS_OBSERVED: list[str] = [
    'unknown', 'declared', 'observed', 'aligned', 'misaligned',
]


# ---------------------------------------------------------------------------
# ValueObject — enduring principle
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValueObject:
    """An enduring value that guides the cognitive agent's priorities.

    Values differ from beliefs in that beliefs are propositional
    ("the world is X"), whereas values are evaluative ("Y matters").
    """

    identifier: str
    value_statement: str
    category: str

    # Core metrics
    confidence: float = 0.0       # does the value exist in cognition
    stability: float = 0.0        # temporal persistence
    priority: float = 0.0         # relative importance in decisions
    influence: float = 0.0        # effect on behaviour

    # Evidence links
    supporting_evidence: tuple[str, ...] = ()
    behavioural_evidence: tuple[str, ...] = ()
    contradictory_evidence: tuple[str, ...] = ()

    # Cross-module associations
    associated_beliefs: tuple[str, ...] = ()
    associated_goals: tuple[str, ...] = ()
    associated_narratives: tuple[str, ...] = ()
    associated_identity_components: tuple[str, ...] = ()

    # Authenticity tracking
    declared_vs_observed: str = 'unknown'

    # Lifecycle
    lifecycle_state: str = 'candidate'
    creation_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    revision_history: tuple[dict[str, Any], ...] = ()
    specification_version: str = '1.0.0'
