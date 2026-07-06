"""SELF-02 Identity Continuity types.

Defines IdentityObject and supporting value objects for the
Identity Continuity Engine (7-phase pipeline).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

IDENTITY_EVOLUTION_TYPES: list[str] = [
    'refinement',
    'expansion',
    'specialization',
    'integration',
    'correction',
    'architectural_maturation',
]

STABLE_IDENTITY_COMPONENTS: list[str] = [
    'evidence_first_reasoning',
    'transparency',
    'explainability',
    'respect_for_uncertainty',
    'ethical_governance',
]

IDENTITY_PHASES: list[str] = [
    'historical_self_model',
    'current_self_model',
    'continuity_analysis',
    'consistency_evaluation',
    'identity_revision',
    'historical_preservation',
    'updated_identity_graph',
]

CONSISTENCY_DIMENSIONS: list[str] = [
    'principle_alignment',
    'behavioral_consistency',
    'temporal_coherence',
    'value_stability',
    'goal_alignment',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdentityIdentifier:
    """Unique identifier for an identity object."""

    id: str = field(default_factory=lambda: 'identity_001')
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


@dataclass(frozen=True)
class CorePrinciple:
    """A single core principle of identity."""

    principle_name: str = ''
    description: str = ''
    stability: float = 0.0
    evidence_sources: tuple[str, ...] = ()
    first_established: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class IdentityLineageEntry:
    """A single entry in the identity's historical lineage."""

    version: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    description: str = ''
    evolution_type: str = ''
    triggering_events: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConsistencyScore:
    """Score for a single consistency dimension."""

    dimension: str = ''
    score: float = 0.0
    evidence: str = ''
    is_stable: bool = True


@dataclass(frozen=True)
class IdentityTension:
    """A known tension between identity components."""

    tension_type: str = ''
    description: str = ''
    severity: float = 0.0
    resolution_status: str = 'unresolved'
    involved_components: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdentityRevision:
    """A revision entry in identity history."""

    version: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    change_description: str = ''
    change_type: str = ''
    confidence_before: float = 0.0
    confidence_after: float = 0.0


@dataclass(frozen=True)
class IdentityConfidence:
    """Multi-dimensional confidence for identity."""

    principle_confidence: float = 0.0
    consistency_confidence: float = 0.0
    continuity_confidence: float = 0.0
    overall: float = 0.0


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Explainability metadata for identity."""

    reasoning_chain: tuple[str, ...] = ()
    evidence_summary: str = ''
    uncertainty_disclosures: tuple[str, ...] = ()
    is_explainable: bool = True


# ---------------------------------------------------------------------------
# Core type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdentityObject:
    """Complete identity object built by the Identity Continuity Engine (SELF-02)."""

    identity_id: str = ''
    identity_version: str = ''
    core_principles: tuple[str, ...] = ()
    stable_characteristics: tuple[str, ...] = ()
    adaptive_characteristics: tuple[str, ...] = ()
    historical_lineage: tuple[dict[str, Any], ...] = ()
    revision_history: tuple[dict[str, Any], ...] = ()
    confidence: float = 0.0
    supporting_evidence: tuple[str, ...] = ()
    known_tensions: tuple[dict[str, Any], ...] = ()
    future_review_points: tuple[str, ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)
