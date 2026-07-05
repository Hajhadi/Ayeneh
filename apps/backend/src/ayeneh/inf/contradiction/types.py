"""INF-04 Contradiction Resolver types.

Defines ContradictionObject, ContradictionResult, and supporting value
objects for the contradiction detection and resolution pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

CONTRADICTION_CATEGORIES: list[str] = [
    'belief',
    'identity',
    'goal',
    'behavior',
    'narrative',
    'prediction',
    'planning',
    'evidence',
    'memory',
    'meta_cognitive',
]

RESOLUTION_STRATEGIES: list[str] = [
    'evidence_accumulation',
    'context_differentiation',
    'belief_revision',
    'narrative_revision',
    'identity_restructuring',
    'goal_prioritization',
    'hypothesis_preservation',
    'version_branching',
    'deferred_resolution',
]

CONTRADICTION_SEVERITY_LEVELS: list[str] = [
    'negligible',
    'minor',
    'moderate',
    'major',
    'critical',
]

CONTRADICTION_STATUSES: list[str] = [
    'detected',
    'analyzing',
    'resolving',
    'resolved',
    'persistent',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConflictClassification:
    """Classification metadata for a detected conflict."""

    category: str = 'belief'
    severity: str = 'minor'
    scope: str = 'local'  # local|global
    identity_impact: float = 0.0
    behavioral_impact: float = 0.0


@dataclass(frozen=True)
class EvidenceComparison:
    """Side-by-side comparison of evidence for two conflicting objects."""

    object_a_id: str = ''
    object_b_id: str = ''
    supporting_a: tuple[str, ...] = ()
    supporting_b: tuple[str, ...] = ()
    quality_a: float = 0.0
    quality_b: float = 0.0
    recency_a: float = 0.0
    recency_b: float = 0.0
    volume_a: int = 0
    volume_b: int = 0
    winner: str = ''  # a|b|tie


@dataclass(frozen=True)
class ResolutionPlan:
    """A concrete plan for resolving a contradiction."""

    strategy: str = 'deferred_resolution'
    steps: tuple[str, ...] = ()
    affected_objects: tuple[str, ...] = ()
    expected_outcome: str = ''
    confidence: float = 0.0
    safety_check: str = 'safe'  # safe|caution|unsafe


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContradictionObject:
    """A single contradiction detected between cognitive objects (INF-04)."""

    contradiction_id: str
    conflicting_objects: tuple[str, ...] = ()
    conflict_type: str = ''
    supporting_evidence: tuple[str, ...] = ()
    contradictory_evidence: tuple[str, ...] = ()
    contexts: tuple[str, ...] = ()
    confidence: float = 0.0
    severity: float = 0.0
    current_status: str = 'detected'
    potential_resolution_paths: tuple[str, ...] = ()
    historical_versions: tuple[dict[str, Any], ...] = ()
    version_metadata: dict[str, Any] = field(default_factory=dict)
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ContradictionResult:
    """Complete result of the contradiction resolution pipeline."""

    contradictions: tuple[ContradictionObject, ...] = ()
    classifications: tuple[ConflictClassification, ...] = ()
    evidence_comparisons: tuple[EvidenceComparison, ...] = ()
    resolution_plans: tuple[ResolutionPlan, ...] = ()
    resolved_ids: tuple[str, ...] = ()
    persistent_ids: tuple[str, ...] = ()
    overall_consistency: float = 1.0
    processing_metadata: dict[str, Any] = field(default_factory=dict)
