"""Types for the working memory subsystem (MEM-04).

Defines WorkingMemoryObject, ContextWindow, ContextSwitch, OpenLoop,
and all associated enumerations and value objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Working memory source enumerations
# ---------------------------------------------------------------------------

WORKING_MEMORY_SOURCES: list[str] = [
    'current_conversation',
    'recent_conversation',
    'episodic_memory',
    'semantic_personal_memory',
    'behavioral_patterns',
    'goals',
    'values',
    'beliefs',
    'identity_components',
    'reflections',
    'predictions',
    'reality_calibration_objects',
    'meta_cognitive_objects',
]

# ---------------------------------------------------------------------------
# Context window enumerations
# ---------------------------------------------------------------------------

CONTEXT_WINDOWS: list[str] = [
    'immediate',
    'session',
    'episode',
    'project',
    'longitudinal',
]

# ---------------------------------------------------------------------------
# Compression strategy enumerations
# ---------------------------------------------------------------------------

COMPRESSION_STRATEGIES: list[str] = [
    'grouping',
    'replacing_observations_with_semantic_knowledge',
    'collapsing_reasoning_chains',
    'preserving_graph_references',
]

# ---------------------------------------------------------------------------
# Open loop categories
# ---------------------------------------------------------------------------

OPEN_LOOP_CATEGORIES: list[str] = [
    'unanswered_questions',
    'incomplete_projects',
    'pending_decisions',
    'unresolved_contradictions',
    'unfinished_reflections',
    'incomplete_episodes',
]

# ---------------------------------------------------------------------------
# Explainability metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Metadata explaining why a memory was activated in working memory."""

    activation_reasons: tuple[str, ...] = ()
    contributing_factors: tuple[str, ...] = ()
    explanation_text: str = ''
    confidence_justification: str = ''
    source_trace: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# WorkingMemoryObject
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkingMemoryObject:
    """A single item held in working memory.

    Each object tracks why it was activated, how relevant it is,
    its temporal properties, and its connections to other cognitive structures.
    """

    identifier: str
    source_memory: str
    activation_reason: str
    activation_score: float = 0.0
    priority_score: float = 0.0
    supporting_evidence: tuple[str, ...] = ()
    associated_episode: str = ''
    associated_cognitive_objects: tuple[str, ...] = ()
    associated_projects: tuple[str, ...] = ()
    temporal_relevance: float = 0.0
    estimated_lifetime: float = 0.0
    dependency_links: tuple[str, ...] = ()
    explainability_metadata: ExplainabilityMetadata = field(
        default_factory=ExplainabilityMetadata
    )

    @property
    def is_expired(self) -> bool:
        """Return True if estimated_lifetime has been exceeded."""
        return self.estimated_lifetime <= 0.0

    @property
    def effective_score(self) -> float:
        """Combined activation and priority score."""
        return self.activation_score * 0.6 + self.priority_score * 0.4


# ---------------------------------------------------------------------------
# Context window
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextWindow:
    """A bounded view of working memory for a specific context scope."""

    window_type: str  # one of CONTEXT_WINDOWS
    window_id: str
    activated_objects: tuple[WorkingMemoryObject, ...] = ()
    max_capacity: int = 20
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def utilization(self) -> float:
        """Fraction of capacity currently used."""
        if self.max_capacity <= 0:
            return 0.0
        return len(self.activated_objects) / self.max_capacity

    @property
    def is_full(self) -> bool:
        return len(self.activated_objects) >= self.max_capacity

    @property
    def available_capacity(self) -> int:
        return max(0, self.max_capacity - len(self.activated_objects))


# ---------------------------------------------------------------------------
# Context switch
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextSwitch:
    """Records a transition between working memory contexts."""

    previous_state: tuple[WorkingMemoryObject, ...] = ()
    reason: str = ''
    new_activation_set: tuple[WorkingMemoryObject, ...] = ()
    residual_dependencies: tuple[str, ...] = ()
    open_hypotheses: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Open loop
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OpenLoop:
    """An incomplete item that needs future resolution."""

    loop_id: str
    category: str  # one of OPEN_LOOP_CATEGORIES
    description: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    associated_memory_ids: tuple[str, ...] = ()
    priority: float = 0.5
    resolved: bool = False
    resolution_memory_id: str = ''

    @property
    def age_seconds(self) -> float:
        """Time since creation."""
        return (datetime.now(UTC) - self.created_at).total_seconds()


# ---------------------------------------------------------------------------
# Compression result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompressionResult:
    """Result of a compression operation on working memory."""

    original_count: int
    compressed_count: int
    strategy_used: str
    grouped_ids: tuple[str, ...] = ()
    replaced_ids: tuple[str, ...] = ()
    collapsed_ids: tuple[str, ...] = ()
    preserved_references: tuple[str, ...] = ()

    @property
    def compression_ratio(self) -> float:
        """Fraction of items removed."""
        if self.original_count <= 0:
            return 0.0
        return 1.0 - (self.compressed_count / self.original_count)


# ---------------------------------------------------------------------------
# Working memory state snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkingMemorySnapshot:
    """A point-in-time snapshot of working memory state."""

    snapshot_id: str
    active_objects: tuple[WorkingMemoryObject, ...] = ()
    context_windows: tuple[ContextWindow, ...] = ()
    open_loops: tuple[OpenLoop, ...] = ()
    active_hypotheses: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def total_items(self) -> int:
        return len(self.active_objects)

    @property
    def unresolved_loops(self) -> int:
        return sum(1 for loop in self.open_loops if not loop.resolved)
