"""Types for MEM-10 Versioning module.

Defines version objects, revision categories, cognitive snapshots,
and the pipeline that maintains a full version history for every memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Revision categories (10)
# ---------------------------------------------------------------------------

class RevisionCategory(str, Enum):
    """Types of revision that create a new version."""

    CORRECTION = 'Correction'
    EXPANSION = 'Expansion'
    REFINEMENT = 'Refinement'
    GENERALIZATION = 'Generalization'
    SPECIALIZATION = 'Specialization'
    REPLACEMENT = 'Replacement'
    MERGER = 'Merger'
    SPLIT = 'Split'
    CONFIDENCE_UPDATE = 'ConfidenceUpdate'
    EVIDENCE_UPDATE = 'EvidenceUpdate'


# ---------------------------------------------------------------------------
# Versioning pipeline stages
# ---------------------------------------------------------------------------

class VersioningPipelineStage(str, Enum):
    """Stages of the versioning pipeline."""

    DIFFERENCE_DETECTION = 'DifferenceDetection'
    REVISION_ANALYSIS = 'RevisionAnalysis'
    VERSION_CREATION = 'VersionCreation'
    RELATIONSHIP_UPDATE = 'RelationshipUpdate'
    KNOWLEDGE_GRAPH_UPDATE = 'KnowledgeGraphUpdate'
    HISTORICAL_PRESERVATION = 'HistoricalPreservation'


# ---------------------------------------------------------------------------
# Version object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VersionObject:
    """An immutable version record for a memory."""

    version_identifier: str
    parent_version: str = ''
    target_memory: str = ''
    version_number: int = 1
    creation_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    revision_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    supporting_evidence: tuple[str, ...] = ()
    revision_type: RevisionCategory = RevisionCategory.EXPANSION
    reason_for_revision: str = ''
    confidence_before: float = 0.0
    confidence_after: float = 0.0
    affected_relationships: tuple[str, ...] = ()
    associated_episodes: tuple[str, ...] = ()
    associated_conversations: tuple[str, ...] = ()
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Difference record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DifferenceRecord:
    """Describes a detected difference between two memory versions."""

    field_name: str = ''
    old_value: Any = None
    new_value: Any = None
    significance: float = 0.0


# ---------------------------------------------------------------------------
# Revision analysis
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RevisionAnalysis:
    """Analysis of whether a revision is warranted and what type it is."""

    memory_id: str = ''
    differences: tuple[DifferenceRecord, ...] = ()
    recommended_revision: RevisionCategory = RevisionCategory.EXPANSION
    confidence_delta: float = 0.0
    rationale: str = ''
    should_create_version: bool = True


# ---------------------------------------------------------------------------
# Version chain
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VersionChain:
    """The full version history for a single memory."""

    memory_id: str = ''
    versions: tuple[VersionObject, ...] = ()
    current_version_number: int = 0

    @property
    def latest(self) -> VersionObject | None:
        return self.versions[-1] if self.versions else None


# ---------------------------------------------------------------------------
# Cognitive snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CognitiveSnapshot:
    """Complete cognitive state at a point in time."""

    snapshot_id: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    memory_versions: dict[str, int] = field(default_factory=dict)
    knowledge_graph_version: int = 0
    active_goals: tuple[str, ...] = ()
    active_projects: tuple[str, ...] = ()
    identity_state: dict[str, Any] = field(default_factory=dict)
    belief_state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Version comparison
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VersionComparison:
    """Side-by-side comparison of two versions of a memory."""

    version_a: VersionObject | None = None
    version_b: VersionObject | None = None
    differences: tuple[DifferenceRecord, ...] = ()
    summary: str = ''
