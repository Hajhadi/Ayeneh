"""Types for MEM-07 Ranking module.

Defines ranking objects, dimension enumerations, task-specific profiles,
and the pipeline stages that transform retrieved memories into a ranked
working-memory selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Ranking dimensions (12)
# ---------------------------------------------------------------------------

class RankingDimension(str, Enum):
    """The twelve dimensions along which memories are ranked."""

    CURRENT_RELEVANCE = 'CurrentRelevance'
    LONG_TERM_IMPORTANCE = 'LongTermImportance'
    BEHAVIORAL_INFLUENCE = 'BehavioralInfluence'
    IDENTITY_INFLUENCE = 'IdentityInfluence'
    GOAL_INFLUENCE = 'GoalInfluence'
    VALUE_INFLUENCE = 'ValueInfluence'
    GRAPH_CENTRALITY = 'GraphCentrality'
    SEMANTIC_SIMILARITY = 'SemanticSimilarity'
    CONTEXT_COMPATIBILITY = 'ContextCompatibility'
    EVIDENCE_QUALITY = 'EvidenceQuality'
    NOVELTY = 'Novelty'
    UNCERTAINTY = 'Uncertainty'


# ---------------------------------------------------------------------------
# Task-specific profiles (4)
# ---------------------------------------------------------------------------

class TaskProfile(str, Enum):
    """Profiles that adjust dimension weights for specific cognitive tasks."""

    DEBUGGING = 'Debugging'
    SELF_REFLECTION = 'SelfReflection'
    REALITY_CALIBRATION = 'RealityCalibration'
    PLANNING = 'Planning'


# Default weight vectors per profile — keys are RankingDimension values.
TASK_PROFILE_WEIGHTS: dict[TaskProfile, dict[str, float]] = {
    TaskProfile.DEBUGGING: {
        RankingDimension.CURRENT_RELEVANCE.value: 0.25,
        RankingDimension.EVIDENCE_QUALITY.value: 0.20,
        RankingDimension.SEMANTIC_SIMILARITY.value: 0.15,
        RankingDimension.LONG_TERM_IMPORTANCE.value: 0.10,
        RankingDimension.BEHAVIORAL_INFLUENCE.value: 0.10,
        RankingDimension.IDENTITY_INFLUENCE.value: 0.05,
        RankingDimension.GOAL_INFLUENCE.value: 0.05,
        RankingDimension.VALUE_INFLUENCE.value: 0.02,
        RankingDimension.GRAPH_CENTRALITY.value: 0.03,
        RankingDimension.CONTEXT_COMPATIBILITY.value: 0.03,
        RankingDimension.NOVELTY.value: 0.01,
        RankingDimension.UNCERTAINTY.value: 0.01,
    },
    TaskProfile.SELF_REFLECTION: {
        RankingDimension.IDENTITY_INFLUENCE.value: 0.25,
        RankingDimension.LONG_TERM_IMPORTANCE.value: 0.20,
        RankingDimension.BEHAVIORAL_INFLUENCE.value: 0.15,
        RankingDimension.CURRENT_RELEVANCE.value: 0.10,
        RankingDimension.EVIDENCE_QUALITY.value: 0.08,
        RankingDimension.SEMANTIC_SIMILARITY.value: 0.08,
        RankingDimension.GOAL_INFLUENCE.value: 0.05,
        RankingDimension.VALUE_INFLUENCE.value: 0.04,
        RankingDimension.GRAPH_CENTRALITY.value: 0.03,
        RankingDimension.CONTEXT_COMPATIBILITY.value: 0.01,
        RankingDimension.NOVELTY.value: 0.00,
        RankingDimension.UNCERTAINTY.value: 0.01,
    },
    TaskProfile.REALITY_CALIBRATION: {
        RankingDimension.EVIDENCE_QUALITY.value: 0.30,
        RankingDimension.CURRENT_RELEVANCE.value: 0.20,
        RankingDimension.SEMANTIC_SIMILARITY.value: 0.15,
        RankingDimension.UNCERTAINTY.value: 0.10,
        RankingDimension.LONG_TERM_IMPORTANCE.value: 0.10,
        RankingDimension.BEHAVIORAL_INFLUENCE.value: 0.05,
        RankingDimension.IDENTITY_INFLUENCE.value: 0.02,
        RankingDimension.GOAL_INFLUENCE.value: 0.02,
        RankingDimension.VALUE_INFLUENCE.value: 0.02,
        RankingDimension.GRAPH_CENTRALITY.value: 0.02,
        RankingDimension.CONTEXT_COMPATIBILITY.value: 0.01,
        RankingDimension.NOVELTY.value: 0.01,
    },
    TaskProfile.PLANNING: {
        RankingDimension.GOAL_INFLUENCE.value: 0.25,
        RankingDimension.CURRENT_RELEVANCE.value: 0.20,
        RankingDimension.LONG_TERM_IMPORTANCE.value: 0.15,
        RankingDimension.BEHAVIORAL_INFLUENCE.value: 0.10,
        RankingDimension.EVIDENCE_QUALITY.value: 0.10,
        RankingDimension.SEMANTIC_SIMILARITY.value: 0.08,
        RankingDimension.IDENTITY_INFLUENCE.value: 0.05,
        RankingDimension.VALUE_INFLUENCE.value: 0.02,
        RankingDimension.GRAPH_CENTRALITY.value: 0.02,
        RankingDimension.CONTEXT_COMPATIBILITY.value: 0.02,
        RankingDimension.NOVELTY.value: 0.00,
        RankingDimension.UNCERTAINTY.value: 0.01,
    },
}


# ---------------------------------------------------------------------------
# Ranking pipeline stages
# ---------------------------------------------------------------------------

class RankingPipelineStage(str, Enum):
    """Stages of the ranking pipeline."""

    FEATURE_EXTRACTION = 'FeatureExtraction'
    RELEVANCE_ESTIMATION = 'RelevanceEstimation'
    IMPORTANCE_ESTIMATION = 'ImportanceEstimation'
    CONTEXT_MATCHING = 'ContextMatching'
    EVIDENCE_WEIGHTING = 'EvidenceWeighting'
    CONFLICT_DETECTION = 'ConflictDetection'
    COMPOSITE_RANKING = 'CompositeRanking'
    WORKING_MEMORY_SELECTION = 'WorkingMemorySelection'


# ---------------------------------------------------------------------------
# Core ranking object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RankingObject:
    """The complete ranking assessment for a single memory."""

    ranking_identifier: str
    target_memory: str
    overall_score: float = 0.0
    relevance_score: float = 0.0
    importance_score: float = 0.0
    confidence_score: float = 0.0
    centrality_score: float = 0.0
    recency_score: float = 0.0
    behavioral_impact_score: float = 0.0
    identity_impact_score: float = 0.0
    evidence_quality_score: float = 0.0
    ranking_explanation: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


# ---------------------------------------------------------------------------
# Dimension scores per memory
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DimensionScores:
    """Per-dimension score breakdown for a single memory."""

    memory_id: str
    scores: dict[str, float] = field(default_factory=dict)
    raw_features: dict[str, Any] = field(default_factory=dict)

    def score(self, dimension: RankingDimension) -> float:
        return self.scores.get(dimension.value, 0.0)


# ---------------------------------------------------------------------------
# Conflict record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConflictRecord:
    """Describes a detected conflict between two memories."""

    memory_a: str
    memory_b: str
    conflict_type: str = ''
    severity: float = 0.0
    explanation: str = ''


# ---------------------------------------------------------------------------
# Ranking context
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RankingContext:
    """Contextual information supplied during ranking."""

    task_profile: TaskProfile = TaskProfile.DEBUGGING
    current_goals: tuple[str, ...] = ()
    active_projects: tuple[str, ...] = ()
    recent_conversation_ids: tuple[str, ...] = ()
    identity_components: tuple[str, ...] = ()
    value_components: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Working memory selection result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkingMemorySelection:
    """Result of selecting memories for working memory."""

    selected_memories: tuple[str, ...] = ()
    rankings: tuple[RankingObject, ...] = ()
    selection_reasoning: str = ''
    capacity_used: int = 0
    capacity_max: int = 20
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
