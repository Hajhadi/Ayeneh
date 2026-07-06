"""SELF-01 Self-Model types.

Defines SelfModelObject and supporting value objects for the
Self-Model Engine (7-phase pipeline).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

SELF_MODEL_PHASES: list[str] = [
    'architecture_state',
    'module_discovery',
    'capability_assessment',
    'constraint_identification',
    'resource_assessment',
    'self_model_construction',
    'version_update',
]

MODULE_STATUS_TYPES: list[str] = [
    'active',
    'inactive',
    'degraded',
    'unknown',
    'initializing',
]

RESOURCE_TYPES: list[str] = [
    'compute_capacity',
    'memory_capacity',
    'context_window',
    'tool_availability',
    'network_access',
    'storage_capacity',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SelfModelIdentifier:
    """Unique identifier for a self-model object."""

    id: str = field(default_factory=lambda: 'self_model_001')
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


@dataclass(frozen=True)
class ModuleStatusEntry:
    """Status of a single module."""

    module_name: str = ''
    status: str = 'unknown'
    last_checked: datetime = field(default_factory=lambda: datetime.now(UTC))
    health_score: float = 0.0
    error_message: str = ''


@dataclass(frozen=True)
class CapabilityDescriptor:
    """Describes a single capability of the system."""

    capability_name: str = ''
    description: str = ''
    confidence: float = 0.0
    evidence_sources: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    last_validated: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ConstraintDescriptor:
    """Describes a single active constraint."""

    constraint_type: str = ''
    description: str = ''
    severity: str = 'medium'
    source: str = ''
    is_active: bool = True


@dataclass(frozen=True)
class ResourceAvailability:
    """Availability of a single resource."""

    resource_type: str = ''
    current_level: float = 0.0
    max_level: float = 1.0
    utilization: float = 0.0
    is_critical: bool = False


@dataclass(frozen=True)
class RevisionEntry:
    """A single entry in the revision history."""

    version: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    change_description: str = ''
    change_type: str = ''
    confidence_before: float = 0.0
    confidence_after: float = 0.0


@dataclass(frozen=True)
class SelfModelConfidence:
    """Multi-dimensional confidence for the self-model."""

    architecture_confidence: float = 0.0
    capability_confidence: float = 0.0
    constraint_confidence: float = 0.0
    resource_confidence: float = 0.0
    overall: float = 0.0


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Explainability metadata for the self-model."""

    reasoning_chain: tuple[str, ...] = ()
    evidence_summary: str = ''
    uncertainty_disclosures: tuple[str, ...] = ()
    is_explainable: bool = True


# ---------------------------------------------------------------------------
# Core type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SelfModelObject:
    """Complete self-model object built by the Self-Model Engine (SELF-01)."""

    model_id: str = ''
    architecture_version: str = ''
    available_modules: tuple[str, ...] = ()
    module_status: dict[str, str] = field(default_factory=dict)
    capabilities: tuple[dict[str, Any], ...] = ()
    known_limitations: tuple[dict[str, Any], ...] = ()
    active_constraints: tuple[dict[str, Any], ...] = ()
    available_resources: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    revision_history: tuple[dict[str, Any], ...] = ()
    version_metadata: dict[str, Any] = field(default_factory=dict)
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)
