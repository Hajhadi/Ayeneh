"""SELF-05 Self-Evolution types.

Defines EvolutionObject and supporting value objects for the
Self-Evolution Engine (8-phase pipeline).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

EVOLUTION_CATEGORIES: list[str] = [
    'capability_expansion',
    'capability_refinement',
    'performance_optimization',
    'architectural_refactoring',
    'knowledge_structure_revision',
    'governance_improvement',
    'safety_enhancement',
    'visualization_enhancement',
]

EVOLUTION_PHASES: list[str] = [
    'operational_history',
    'longitudinal_analysis',
    'capability_opportunities',
    'evolution_proposal',
    'consistency_validation',
    'risk_assessment',
    'approved_evolution',
    'architecture_version_update',
]

APPROVAL_STATUSES: list[str] = [
    'proposed',
    'under_review',
    'approved',
    'rejected',
    'implemented',
    'rolled_back',
    'deferred',
]

RISK_LEVELS: list[str] = [
    'negligible',
    'low',
    'medium',
    'high',
    'critical',
]

IMPACT_CATEGORIES: list[str] = [
    'performance',
    'reliability',
    'maintainability',
    'scalability',
    'security',
    'usability',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvolutionIdentifier:
    """Unique identifier for an evolution object."""

    id: str = field(default_factory=lambda: 'evolution_001')
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


@dataclass(frozen=True)
class OperationalRecord:
    """A single operational record for longitudinal analysis."""

    record_id: str = ''
    module: str = ''
    metric_name: str = ''
    metric_value: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TrendAnalysis:
    """Analysis of a trend over time."""

    trend_id: str = ''
    metric_name: str = ''
    direction: str = 'stable'  # improving, stable, degrading
    magnitude: float = 0.0
    confidence: float = 0.0
    affected_modules: tuple[str, ...] = ()
    data_points: int = 0


@dataclass(frozen=True)
class CapabilityOpportunity:
    """An identified opportunity for capability improvement."""

    opportunity_id: str = ''
    category: str = 'capability_expansion'
    description: str = ''
    current_state: str = ''
    desired_state: str = ''
    affected_modules: tuple[str, ...] = ()
    priority: float = 0.5
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvolutionProposal:
    """A proposed evolution change."""

    proposal_id: str = ''
    category: str = 'capability_expansion'
    title: str = ''
    description: str = ''
    motivation: str = ''
    expected_benefits: tuple[str, ...] = ()
    affected_modules: tuple[str, ...] = ()
    implementation_steps: tuple[str, ...] = ()
    rollback_plan: str = ''
    priority: float = 0.5


@dataclass(frozen=True)
class RiskAssessment:
    """Risk assessment for an evolution proposal."""

    risk_id: str = ''
    proposal_id: str = ''
    risk_level: str = 'medium'
    risk_description: str = ''
    mitigation_strategy: str = ''
    impact_areas: tuple[str, ...] = ()
    probability: float = 0.5
    severity: float = 0.5


@dataclass(frozen=True)
class VersionUpdate:
    """Record of a version update."""

    update_id: str = ''
    previous_version: str = ''
    new_version: str = ''
    change_summary: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    modules_affected: tuple[str, ...] = ()
    is_rollback: bool = False


@dataclass(frozen=True)
class EvolutionConfidence:
    """Multi-dimensional confidence for evolution assessment."""

    evidence_confidence: float = 0.0
    trend_confidence: float = 0.0
    risk_confidence: float = 0.0
    implementation_confidence: float = 0.0
    overall: float = 0.0


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Explainability metadata for evolution."""

    reasoning_chain: tuple[str, ...] = ()
    evidence_summary: str = ''
    uncertainty_disclosures: tuple[str, ...] = ()
    is_explainable: bool = True


# ---------------------------------------------------------------------------
# Core type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvolutionObject:
    """Complete evolution object built by the Self-Evolution Engine (SELF-05)."""

    evolution_id: str = ''
    architecture_version: str = ''
    proposal: str = ''
    motivation: str = ''
    supporting_evidence: tuple[str, ...] = ()
    affected_modules: tuple[str, ...] = ()
    expected_benefits: tuple[str, ...] = ()
    known_risks: tuple[str, ...] = ()
    approval_status: str = 'proposed'
    implementation_history: tuple[dict[str, Any], ...] = ()
    version_metadata: dict[str, Any] = field(default_factory=dict)
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvolutionResult:
    """Result of running the Self-Evolution Engine pipeline."""

    evolution_id: str = ''
    evolution_object: EvolutionObject = field(default_factory=EvolutionObject)
    operational_records: tuple[OperationalRecord, ...] = ()
    trends: tuple[TrendAnalysis, ...] = ()
    opportunities: tuple[CapabilityOpportunity, ...] = ()
    proposals: tuple[EvolutionProposal, ...] = ()
    risk_assessments: tuple[RiskAssessment, ...] = ()
    version_updates: tuple[VersionUpdate, ...] = ()
    confidence: float = 0.0
    duration_ms: float = 0.0
    errors: tuple[str, ...] = ()
