"""Decision Architecture types for the Ayeneh COG architecture (COG-10).

Defines DecisionObject, DecisionPattern, TradeOff, and supporting structures
that model how decisions emerge from interacting cognitive structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

DECISION_LIFECYCLE_STATES: list[str] = [
    'candidate', 'emerging', 'validated', 'canonical',
    'revised', 'deprecated', 'historical',
]

DECISION_TYPES: list[str] = [
    'deliberate', 'intuitive', 'habitual', 'reactive',
    'collaborative', 'delegated', 'emergency',
]

OUTCOME_CATEGORIES: list[str] = [
    'positive', 'negative', 'neutral', 'mixed',
    'uncertain', 'pending',
]


# ---------------------------------------------------------------------------
# DecisionObject — a single reconstructed decision
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionObject:
    """A single decision reconstructed from evidence and cognitive structures.

    Captures the full decision process: context, alternatives considered,
    chosen path, and all cognitive structures that were activated during
    the decision.
    """

    identifier: str
    decision_statement: str
    context: str
    alternatives: tuple[str, ...] = ()
    chosen_alternative: str = ''
    rejected_alternatives: tuple[str, ...] = ()
    supporting_evidence: tuple[str, ...] = ()
    activated_narratives: tuple[str, ...] = ()
    activated_beliefs: tuple[str, ...] = ()
    activated_values: tuple[str, ...] = ()
    activated_goals: tuple[str, ...] = ()
    activated_identity_components: tuple[str, ...] = ()
    confidence: float = 0.0
    uncertainty: float = 0.0
    behavioral_outcome: str = ''
    decision_inertia: float = 0.0  # resistance to change
    lifecycle_state: str = 'candidate'
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    revision_history: tuple[dict[str, Any], ...] = ()
    specification_version: str = '1.0.0'


# ---------------------------------------------------------------------------
# DecisionPattern — repeated decision structure across time
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionPattern:
    """A recurring decision structure detected across multiple decisions.

    Identifies patterns such as consistently choosing safety over growth,
    or always deferring to authority in ambiguous situations.
    """

    pattern_id: str
    description: str
    frequency: int = 0
    confidence: float = 0.0
    decision_ids: tuple[str, ...] = ()
    common_activations: dict[str, tuple[str, ...]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# TradeOff — value conflict captured in a decision
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TradeOff:
    """Records a value conflict that was resolved in a decision."""

    decision_id: str
    value_a: str
    value_b: str
    chosen: str
    rejected: str
    opportunity_cost: float = 0.0


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionResult:
    """Output of the COG-10 Decision Architecture Engine pipeline."""

    decisions: dict[str, DecisionObject]
    patterns: dict[str, DecisionPattern]
    trade_offs: tuple[TradeOff, ...] = ()
    total_extracted: int = 0
    lifecycle_summary: dict[str, int] = field(default_factory=dict)
