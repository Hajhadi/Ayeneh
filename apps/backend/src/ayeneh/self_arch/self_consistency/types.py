"""SELF-04 Self-Consistency types.

Defines ConsistencyObject and supporting value objects for the
Self-Consistency Engine (8-phase pipeline).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

CONSISTENCY_LEVELS: list[str] = [
    'logical',
    'behavioral',
    'knowledge',
    'planning',
    'identity',
    'ethical',
    'architectural',
]

CONFLICT_CATEGORIES: list[str] = [
    'logical_contradiction',
    'evidence_conflict',
    'temporal_inconsistency',
    'version_mismatch',
    'dependency_inconsistency',
    'governance_conflict',
    'behavioral_inconsistency',
]

CONSISTENCY_PHASES: list[str] = [
    'architecture_state',
    'cross_module_analysis',
    'consistency_detection',
    'conflict_identification',
    'evidence_evaluation',
    'consistency_resolution',
    'integrity_update',
    'architecture_health',
]

RESOLUTION_STRATEGIES: list[str] = [
    'automatic',
    'manual_review',
    'priority_override',
    'merge',
    'deprecation',
    'quarantine',
    'escalation',
]

CONFIDENCE_DIMENSIONS: list[str] = [
    'evidence_strength',
    'cross_module_agreement',
    'temporal_stability',
    'architectural_coherence',
    'conflict_severity',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsistencyIdentifier:
    """Unique identifier for a consistency object."""

    id: str = field(default_factory=lambda: 'consistency_001')
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


@dataclass(frozen=True)
class ModuleConsistencyStatus:
    """Consistency status of a single module."""

    module_name: str = ''
    consistency_level: str = 'logical'
    score: float = 0.0
    conflicts_detected: int = 0
    last_checked: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: str = ''


@dataclass(frozen=True)
class ConflictDescriptor:
    """Describes a single detected conflict."""

    conflict_id: str = ''
    category: str = 'logical_contradiction'
    description: str = ''
    severity: str = 'medium'
    affected_modules: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolution_status: str = 'unresolved'
    resolution_strategy: str = ''


@dataclass(frozen=True)
class CrossModuleRelationship:
    """Relationship between two modules for consistency checking."""

    source_module: str = ''
    target_module: str = ''
    relationship_type: str = 'data_dependency'
    consistency_score: float = 0.0
    is_bidirectional: bool = False
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceItem:
    """A single piece of evidence for consistency evaluation."""

    evidence_id: str = ''
    source: str = ''
    content: str = ''
    reliability: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    supports_consistency: bool = True


@dataclass(frozen=True)
class ResolutionAction:
    """Action taken to resolve a conflict."""

    action_id: str = ''
    conflict_id: str = ''
    strategy: str = 'automatic'
    description: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    outcome: str = ''
    confidence_impact: float = 0.0


@dataclass(frozen=True)
class IntegrityCheck:
    """Result of an integrity check on the architecture."""

    check_id: str = ''
    check_type: str = ''
    passed: bool = True
    score: float = 1.0
    details: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class HealthIndicator:
    """Architecture health indicator."""

    indicator_name: str = ''
    value: float = 0.0
    threshold: float = 0.5
    is_healthy: bool = True
    trend: str = 'stable'  # improving, stable, degrading


@dataclass(frozen=True)
class ConsistencyConfidence:
    """Multi-dimensional confidence for consistency assessment."""

    evidence_confidence: float = 0.0
    cross_module_confidence: float = 0.0
    temporal_confidence: float = 0.0
    architectural_confidence: float = 0.0
    overall: float = 0.0


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Explainability metadata for consistency."""

    reasoning_chain: tuple[str, ...] = ()
    evidence_summary: str = ''
    uncertainty_disclosures: tuple[str, ...] = ()
    is_explainable: bool = True


# ---------------------------------------------------------------------------
# Core type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsistencyObject:
    """Complete consistency object built by the Self-Consistency Engine (SELF-04)."""

    consistency_id: str = ''
    affected_modules: tuple[str, ...] = ()
    consistency_type: str = ''
    supporting_evidence: tuple[str, ...] = ()
    detected_conflicts: tuple[dict[str, Any], ...] = ()
    resolution_status: str = 'unresolved'
    confidence: float = 0.0
    revision_history: tuple[dict[str, Any], ...] = ()
    architectural_impact: str = ''
    recommended_actions: tuple[str, ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsistencyResult:
    """Result of running the Self-Consistency Engine pipeline."""

    consistency_id: str = ''
    consistency_object: ConsistencyObject = field(default_factory=ConsistencyObject)
    module_statuses: tuple[ModuleConsistencyStatus, ...] = ()
    conflicts: tuple[ConflictDescriptor, ...] = ()
    relationships: tuple[CrossModuleRelationship, ...] = ()
    evidence: tuple[EvidenceItem, ...] = ()
    resolutions: tuple[ResolutionAction, ...] = ()
    integrity_checks: tuple[IntegrityCheck, ...] = ()
    health_indicators: tuple[HealthIndicator, ...] = ()
    confidence: float = 0.0
    duration_ms: float = 0.0
    errors: tuple[str, ...] = ()
