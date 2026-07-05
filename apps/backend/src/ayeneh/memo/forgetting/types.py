"""Types for MEM-08 Forgetting / Compression module.

Defines compression objects, adaptive-forgetting tiers, multi-resolution
levels, and the pipeline stages that reduce memory load while preserving
essential knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Compression types (5)
# ---------------------------------------------------------------------------

class CompressionType(str, Enum):
    """Strategies for compressing or forgetting memories."""

    REDUNDANCY = 'Redundancy'
    CONVERSATION = 'Conversation'
    EPISODE = 'Episode'
    SEMANTIC = 'Semantic'
    GRAPH = 'Graph'


# ---------------------------------------------------------------------------
# Adaptive forgetting tiers
# ---------------------------------------------------------------------------

class AdaptiveForgettingTier(str, Enum):
    """Activity-based tiers governing how memories age and compress."""

    FREQUENTLY_ACTIVE = 'FrequentlyActive'
    OCCASIONALLY_ACTIVE = 'OccasionallyActive'
    DORMANT = 'Dormant'
    ARCHIVED = 'Archived'
    HISTORICAL_ONLY = 'HistoricalOnly'


# Tier thresholds — memory falls into a tier based on access frequency score.
TIER_THRESHOLDS: dict[AdaptiveForgettingTier, tuple[float, float]] = {
    AdaptiveForgettingTier.FREQUENTLY_ACTIVE: (0.8, 1.0),
    AdaptiveForgettingTier.OCCASIONALLY_ACTIVE: (0.5, 0.8),
    AdaptiveForgettingTier.DORMANT: (0.2, 0.5),
    AdaptiveForgettingTier.ARCHIVED: (0.05, 0.2),
    AdaptiveForgettingTier.HISTORICAL_ONLY: (0.0, 0.05),
}


# ---------------------------------------------------------------------------
# Multi-resolution levels (7)
# ---------------------------------------------------------------------------

class ResolutionLevel(str, Enum):
    """Levels of abstraction in multi-resolution memory storage."""

    RAW_CONVERSATION = 'RawConversation'
    EVIDENCE = 'Evidence'
    EPISODE = 'Episode'
    EPISODE_SUMMARY = 'EpisodeSummary'
    LIFE_CHAPTER_SUMMARY = 'LifeChapterSummary'
    LONGITUDINAL_TRAJECTORY = 'LongitudinalTrajectory'
    IDENTITY_LEVEL_UNDERSTANDING = 'IdentityLevelUnderstanding'


RESOLUTION_ORDER: list[ResolutionLevel] = [
    ResolutionLevel.RAW_CONVERSATION,
    ResolutionLevel.EVIDENCE,
    ResolutionLevel.EPISODE,
    ResolutionLevel.EPISODE_SUMMARY,
    ResolutionLevel.LIFE_CHAPTER_SUMMARY,
    ResolutionLevel.LONGITUDINAL_TRAJECTORY,
    ResolutionLevel.IDENTITY_LEVEL_UNDERSTANDING,
]


# ---------------------------------------------------------------------------
# Forgetting pipeline stages
# ---------------------------------------------------------------------------

class ForgettingPipelineStage(str, Enum):
    """Stages of the forgetting / compression pipeline."""

    USAGE_ANALYSIS = 'UsageAnalysis'
    IMPORTANCE_ANALYSIS = 'ImportanceAnalysis'
    REDUNDANCY_DETECTION = 'RedundancyDetection'
    COMPRESSION_CANDIDATE = 'CompressionCandidate'
    EVIDENCE_PRESERVATION = 'EvidencePreservation'
    KNOWLEDGE_COMPRESSION = 'KnowledgeCompression'
    GRAPH_UPDATE = 'GraphUpdate'
    RETRIEVAL_OPTIMIZATION = 'RetrievalOptimization'


# ---------------------------------------------------------------------------
# Compression object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CompressionObject:
    """Records a compression or forgetting action applied to memories."""

    compression_identifier: str
    affected_memory_objects: tuple[str, ...] = ()
    compression_strategy: CompressionType = CompressionType.REDUNDANCY
    reason: str = ''
    supporting_evidence: tuple[str, ...] = ()
    knowledge_preserved: str = ''
    information_reduced: float = 0.0
    recoverability_status: str = 'recoverable'
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    version_history: tuple[dict[str, Any], ...] = ()
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Usage analysis record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UsageRecord:
    """Tracks access patterns for a memory."""

    memory_id: str
    access_count: int = 0
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_frequency_score: float = 0.0
    retrieval_latency_ms: float = 0.0
    context_diversity: int = 0


# ---------------------------------------------------------------------------
# Redundancy pair
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RedundancyPair:
    """Two memories identified as redundant."""

    memory_a: str
    memory_b: str
    similarity: float = 0.0
    recommended_action: str = 'merge'


# ---------------------------------------------------------------------------
# Compression candidate
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CompressionCandidate:
    """A memory flagged as a compression candidate with rationale."""

    memory_id: str
    compression_type: CompressionType = CompressionType.REDUNDANCY
    priority: float = 0.0
    estimated_information_loss: float = 0.0
    rationale: str = ''
    current_resolution: ResolutionLevel = ResolutionLevel.RAW_CONVERSATION
    target_resolution: ResolutionLevel = ResolutionLevel.EPISODE_SUMMARY


# ---------------------------------------------------------------------------
# Forgetting result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ForgettingResult:
    """Summary of a forgetting / compression batch run."""

    compression_identifier: str
    compressions_applied: tuple[CompressionObject, ...] = ()
    memories_affected: int = 0
    information_reduced: float = 0.0
    recoverable: bool = True
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)
