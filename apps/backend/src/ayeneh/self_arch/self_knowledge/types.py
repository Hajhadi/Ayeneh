"""SELF-03 Self-Knowledge types.

Defines SelfKnowledgeObject and supporting value objects for the
Self-Knowledge Engine (7-phase pipeline).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

KNOWLEDGE_CATEGORIES: list[str] = [
    'verified_capabilities',
    'verified_limitations',
    'operational_characteristics',
    'behavioral_tendencies',
    'performance_statistics',
    'architectural_assumptions',
    'open_questions',
    'experimental_knowledge',
]

EPISTEMIC_STATUSES: list[str] = [
    'verified',
    'strongly_supported',
    'provisionally_supported',
    'hypothetical',
    'unknown',
    'refuted',
]

KNOWLEDGE_PHASES: list[str] = [
    'operational_evidence',
    'self_model',
    'verification',
    'knowledge_classification',
    'confidence_calibration',
    'knowledge_integration',
    'self_knowledge_base',
]

EVIDENCE_TYPES: list[str] = [
    'direct_observation',
    'operational_data',
    'self_report',
    'peer_comparison',
    'benchmark_result',
    'user_feedback',
    'failure_analysis',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeIdentifier:
    """Unique identifier for a knowledge object."""

    id: str = field(default_factory=lambda: 'knowledge_001')
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


@dataclass(frozen=True)
class EvidenceSource:
    """A single evidence source supporting a knowledge claim."""

    source_type: str = ''
    source_id: str = ''
    description: str = ''
    reliability: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class VerificationResult:
    """Result of verifying a knowledge claim."""

    is_verified: bool = False
    verification_method: str = ''
    confidence: float = 0.0
    evidence_count: int = 0
    last_verified: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class KnowledgeException:
    """A known exception to a knowledge claim."""

    exception_description: str = ''
    condition: str = ''
    severity: str = 'low'
    is_active: bool = True


@dataclass(frozen=True)
class KnowledgeRevision:
    """A revision entry in knowledge history."""

    version: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    change_description: str = ''
    change_type: str = ''
    confidence_before: float = 0.0
    confidence_after: float = 0.0


@dataclass(frozen=True)
class KnowledgeConfidence:
    """Multi-dimensional confidence for knowledge."""

    evidence_confidence: float = 0.0
    verification_confidence: float = 0.0
    context_confidence: float = 0.0
    overall: float = 0.0


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Explainability metadata for knowledge."""

    reasoning_chain: tuple[str, ...] = ()
    evidence_summary: str = ''
    uncertainty_disclosures: tuple[str, ...] = ()
    is_explainable: bool = True


# ---------------------------------------------------------------------------
# Core type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SelfKnowledgeObject:
    """Complete self-knowledge object built by the Self-Knowledge Engine (SELF-03)."""

    knowledge_id: str = ''
    statement: str = ''
    evidence_sources: tuple[str, ...] = ()
    confidence: float = 0.0
    verification_status: str = 'unknown'
    associated_modules: tuple[str, ...] = ()
    revision_history: tuple[dict[str, Any], ...] = ()
    known_exceptions: tuple[str, ...] = ()
    applicable_contexts: tuple[str, ...] = ()
    future_validation_targets: tuple[str, ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)
