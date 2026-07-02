"""Graph Reasoning types — core domain objects for reasoning over the Knowledge Graph."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


# ---------------------------------------------------------------------------
# Reasoning Policy
# ---------------------------------------------------------------------------


@dataclass
class ReasoningPolicy:
    """Policy for reasoning behavior."""

    id: str = "default"
    name: str = "Default"
    hypothesis_generation_behavior: str = "conservative"
    confidence_calibration: str = "standard"
    conflict_tolerance: str = "moderate"
    agreement_strategy: str = "balanced"
    uncertainty_disclosure: str = "always"
    explanation_style: str = "detailed"
    scope_restrictions: list[str] = field(default_factory=list)
    safety_preferences: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Reasoning Cache
# ---------------------------------------------------------------------------


@dataclass
class CacheKey:
    """Cache key with version awareness."""

    graph_version: int = 0
    policy_version: str = "1.0"
    provider_version: str = "1.0"
    product_profile: str = "default"
    reasoning_version: str = "1.0"
    retrieval_strategy: str = "default"
    interpretation_version: str = "1.0"

    def to_string(self) -> str:
        return f"{self.graph_version}:{self.policy_version}:{self.provider_version}:{self.product_profile}"


@dataclass
class CacheEntry:
    """A cached reasoning result."""

    key: CacheKey = field(default_factory=CacheKey)
    result: Any = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    hit_count: int = 0


# ---------------------------------------------------------------------------
# Reasoning Chain
# ---------------------------------------------------------------------------


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step_type: str = ""
    description: str = ""
    evidence_used: list[str] = field(default_factory=list)
    graph_edges_used: list[str] = field(default_factory=list)
    interpretations_used: list[str] = field(default_factory=list)
    confidence: float = 0.5
    discarded: bool = False
    discard_reason: str = ""


@dataclass
class ReasoningChain:
    """Complete reasoning chain for a query."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    steps: list[ReasoningStep] = field(default_factory=list)
    evidence_references: list[str] = field(default_factory=list)
    interpretation_ids: list[str] = field(default_factory=list)
    discarded_paths: list[str] = field(default_factory=list)
    rejected_hypotheses: list[str] = field(default_factory=list)
    confidence_evolution: list[float] = field(default_factory=list)
    overall_confidence: float = 0.5
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Hypothesis
# ---------------------------------------------------------------------------


@dataclass
class Hypothesis:
    """A candidate hypothesis generated during reasoning."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    statement: str = ""
    supporting_evidence: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    limitations: list[str] = field(default_factory=list)
    alternative_explanations: list[str] = field(default_factory=list)
    scope: str = ""
    is_rejected: bool = False
    rejection_reason: str = ""


# ---------------------------------------------------------------------------
# Conflict
# ---------------------------------------------------------------------------


@dataclass
class ReasoningConflict:
    """A conflict detected during reasoning."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_type: str = ""  # logical, epistemic, tradition, authority, scope, terminology
    description: str = ""
    source_a: str = ""
    source_b: str = ""
    confidence: float = 0.5
    scope: str = ""
    is_resolved: bool = False
    resolution: str = ""


# ---------------------------------------------------------------------------
# Agreement
# ---------------------------------------------------------------------------


@dataclass
class ReasoningAgreement:
    """An agreement detected during reasoning."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agreement_type: str = ""  # agreement, partial, shared_assumption, shared_mechanism
    description: str = ""
    source_a: str = ""
    source_b: str = ""
    confidence: float = 0.5
    scope: str = ""


# ---------------------------------------------------------------------------
# Reasoning Confidence
# ---------------------------------------------------------------------------


@dataclass
class ReasoningConfidence:
    """Decomposed confidence for reasoning."""

    retrieval_confidence: float = 0.5
    graph_confidence: float = 0.5
    evidence_confidence: float = 0.5
    interpretation_confidence: float = 0.5
    cross_book_confidence: float = 0.5
    cross_tradition_confidence: float = 0.5
    ocr_confidence: float = 1.0
    reasoning_confidence: float = 0.5
    overall_confidence: float = 0.5


# ---------------------------------------------------------------------------
# Reasoning Explanation
# ---------------------------------------------------------------------------


@dataclass
class ReasoningExplanation:
    """Explanation of the reasoning process."""

    why_conclusion: str = ""
    why_alternatives_rejected: list[str] = field(default_factory=list)
    why_confidence_limited: list[str] = field(default_factory=list)
    books_contributed: list[str] = field(default_factory=list)
    concepts_contributed: list[str] = field(default_factory=list)
    graph_paths_contributed: list[str] = field(default_factory=list)
    interpretations_contributed: list[str] = field(default_factory=list)
    semantic_links_contributed: list[str] = field(default_factory=list)
    evidence_increased_confidence: list[str] = field(default_factory=list)
    evidence_decreased_confidence: list[str] = field(default_factory=list)
    remaining_uncertainty: list[str] = field(default_factory=list)
    underlying_assumptions: list[str] = field(default_factory=list)
    scope_limitations: list[str] = field(default_factory=list)
    alternative_interpretations: list[str] = field(default_factory=list)
    strongest_evidence: str = ""
    weakest_evidence: str = ""


# ---------------------------------------------------------------------------
# Reasoning Result
# ---------------------------------------------------------------------------


@dataclass
class ReasoningResult:
    """Complete result of graph reasoning."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    chain: ReasoningChain = field(default_factory=ReasoningChain)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    conflicts: list[ReasoningConflict] = field(default_factory=list)
    agreements: list[ReasoningAgreement] = field(default_factory=list)
    confidence: ReasoningConfidence = field(default_factory=ReasoningConfidence)
    explanation: ReasoningExplanation = field(default_factory=ReasoningExplanation)
    provenance_bundle_id: str = ""
    safety_passed: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Versioning
    reasoning_version: str = "1.0.0"
    graph_version: int = 0
    knowledge_version: str = "1.0.0"
    policy_version: str = "1.0.0"
    provider_version: str = "1.0.0"
    interpretation_version: str = "1.0.0"
    retrieval_version: str = "1.0.0"
    engine_version: str = "1.0.0"


# ---------------------------------------------------------------------------
# Reasoning Diff (Incremental)
# ---------------------------------------------------------------------------


@dataclass
class ReasoningDiff:
    """Result of incremental reasoning update."""

    new_hypotheses: list[Hypothesis] = field(default_factory=list)
    updated_hypotheses: list[Hypothesis] = field(default_factory=list)
    invalidated_hypotheses: list[str] = field(default_factory=list)
    new_reasoning_paths: list[list[str]] = field(default_factory=list)
    removed_reasoning_paths: list[list[str]] = field(default_factory=list)
    new_evidence: list[dict[str, Any]] = field(default_factory=list)
    updated_confidence: ReasoningConfidence = field(default_factory=ReasoningConfidence)
    affected_concepts: list[str] = field(default_factory=list)
    affected_graph_nodes: list[str] = field(default_factory=list)
    affected_graph_edges: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Reasoning Metrics
# ---------------------------------------------------------------------------


@dataclass
class ReasoningMetrics:
    """Metrics for reasoning operations."""

    reasoning_count: int = 0
    reasoning_duration: float = 0.0
    retrieval_duration: float = 0.0
    path_discovery_duration: float = 0.0
    hypothesis_duration: float = 0.0
    conflict_duration: float = 0.0
    agreement_duration: float = 0.0
    cache_duration: float = 0.0
    total_duration: float = 0.0
    streaming_duration: float = 0.0
    cache_lookup_duration: float = 0.0
    provider_duration: float = 0.0
    explanation_duration: float = 0.0
    incremental_duration: float = 0.0

    retrieved_nodes: int = 0
    retrieved_edges: int = 0
    candidate_paths: int = 0
    accepted_paths: int = 0
    discarded_paths: int = 0
    generated_hypotheses: int = 0
    accepted_hypotheses: int = 0
    rejected_hypotheses: int = 0
    agreement_count: int = 0
    conflict_count: int = 0
    average_path_length: float = 0.0
    average_confidence: float = 0.0
    cache_hit_rate: float = 0.0
    cache_miss_rate: float = 0.0
    cache_eviction_rate: float = 0.0
    incremental_reasoning_rate: float = 0.0
    graph_traversal_depth: int = 0
    provider_used: str = ""
    provider_version: str = ""
    policy_used: str = ""
    policy_version: str = ""
