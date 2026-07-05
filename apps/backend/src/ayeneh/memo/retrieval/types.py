"""Types for the retrieval subsystem (MEM-06).

Defines RetrievalRequest, RetrievalResult, RetrievalStrategy,
MultiHopRetrieval, and all associated enumerations and value objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Retrieval strategy enumerations
# ---------------------------------------------------------------------------

RETRIEVAL_STRATEGIES: list[str] = [
    'evidence_first',
    'semantic_first',
    'episode_first',
    'identity_first',
    'narrative_first',
    'trajectory_first',
    'composite',
]

# ---------------------------------------------------------------------------
# Ranking strategy enumerations
# ---------------------------------------------------------------------------

RANKING_STRATEGIES: list[str] = [
    'relevance',
    'recency',
    'importance',
    'confidence',
    'composite',
]

# ---------------------------------------------------------------------------
# Intent detection types
# ---------------------------------------------------------------------------

DETECTED_INTENTS: list[str] = [
    'recall',
    'reflect',
    'plan',
    'explain',
    'compare',
    'explore',
    'verify',
    'update',
]

# ---------------------------------------------------------------------------
# RetrievalRequest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievalRequest:
    """A request to retrieve memories from the system."""

    request_identifier: str
    conversation_context: str = ''
    detected_intent: str = 'recall'
    current_cognitive_focus: str = ''
    relevant_projects: tuple[str, ...] = ()
    relevant_episodes: tuple[str, ...] = ()
    relevant_cognitive_objects: tuple[str, ...] = ()
    required_confidence_threshold: float = 0.0
    maximum_retrieval_size: int = 20
    ranking_strategy: str = 'composite'
    explainability_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_focus(self) -> bool:
        return bool(self.current_cognitive_focus)


# ---------------------------------------------------------------------------
# Retrieved item
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievedItem:
    """A single retrieved memory with its ranking score."""

    memory_id: str
    memory_type: str
    content: str = ''
    relevance_score: float = 0.0
    recency_score: float = 0.0
    importance_score: float = 0.0
    confidence_score: float = 0.0
    final_score: float = 0.0
    retrieval_path: tuple[str, ...] = ()
    supporting_evidence: tuple[str, ...] = ()
    explainability_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def meets_threshold(self) -> bool:
        """Return True if this item meets a minimum relevance threshold."""
        return self.final_score >= 0.3


# ---------------------------------------------------------------------------
# Retrieval result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievalResult:
    """The full result of a retrieval operation."""

    request_id: str
    retrieved_items: tuple[RetrievedItem, ...] = ()
    strategy_used: str = 'composite'
    total_candidates_evaluated: int = 0
    hops_performed: int = 0
    adaptive_retrievals_triggered: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def count(self) -> int:
        return len(self.retrieved_items)

    @property
    def average_score(self) -> float:
        if not self.retrieved_items:
            return 0.0
        return sum(item.final_score for item in self.retrieved_items) / len(
            self.retrieved_items
        )


# ---------------------------------------------------------------------------
# Multi-hop retrieval
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MultiHopRetrieval:
    """Tracks a multi-hop retrieval across the knowledge graph."""

    hop_id: str
    starting_memory_id: str
    current_memory_id: str
    hop_count: int = 0
    max_hops: int = 5
    visited_ids: tuple[str, ...] = ()
    accumulated_evidence: tuple[str, ...] = ()
    confidence_decay: float = 0.9

    @property
    def has_reached_limit(self) -> bool:
        return self.hop_count >= self.max_hops

    @property
    def accumulated_confidence(self) -> float:
        """Confidence after decay over hops."""
        return self.confidence_decay ** self.hop_count


# ---------------------------------------------------------------------------
# Adaptive retrieval trigger
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdaptiveRetrievalTrigger:
    """A trigger for additional retrieval based on new information."""

    trigger_id: str
    trigger_reason: str
    new_information: str
    suggested_strategy: str = 'semantic_first'
    priority: float = 0.5
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved: bool = False

    @property
    def is_high_priority(self) -> bool:
        return self.priority >= 0.8


# ---------------------------------------------------------------------------
# Ranking weights
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RankingWeights:
    """Configurable weights for the ranking algorithm."""

    relevance: float = 0.4
    recency: float = 0.2
    importance: float = 0.2
    confidence: float = 0.2

    def normalize(self) -> RankingWeights:
        """Return a new RankingWeights with weights summing to 1.0."""
        total = self.relevance + self.recency + self.importance + self.confidence
        if total <= 0:
            return RankingWeights(
                relevance=0.25,
                recency=0.25,
                importance=0.25,
                confidence=0.25,
            )
        return RankingWeights(
            relevance=self.relevance / total,
            recency=self.recency / total,
            importance=self.importance / total,
            confidence=self.confidence / total,
        )


# ---------------------------------------------------------------------------
# Graph expansion result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphExpansionResult:
    """Result of expanding the knowledge graph from a seed node."""

    seed_id: str
    expanded_ids: tuple[str, ...] = ()
    edges_traversed: int = 0
    depth_reached: int = 0
    confidence_at_depth: tuple[tuple[int, float], ...] = ()

    @property
    def expansion_size(self) -> int:
        return len(self.expanded_ids)


# ---------------------------------------------------------------------------
# Evidence validation result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceValidationResult:
    """Result of validating evidence for a retrieved memory."""

    memory_id: str
    evidence_count: int = 0
    supporting_count: int = 0
    contradicting_count: int = 0
    validation_score: float = 0.0
    is_valid: bool = False

    @property
    def support_ratio(self) -> float:
        if self.evidence_count <= 0:
            return 0.0
        return self.supporting_count / self.evidence_count
