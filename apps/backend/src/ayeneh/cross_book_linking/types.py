"""Cross-Book Linking types — semantic relations between knowledge sources."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


class SemanticRelationType:
    """Semantic edge types for cross-book linking."""

    SUPPORTS = "supports"
    EXTENDS = "extends"
    CONTRADICTS = "contradicts"
    SHARES_CONCEPT = "shares_concept"
    DIFFERENT_SCOPE = "different_scope"
    DIFFERENT_EVIDENCE = "different_evidence"
    HISTORICAL_INFLUENCE = "historical_influence"
    USES_DIFFERENT_TERMINOLOGY = "uses_different_terminology"
    PARTIALLY_OVERLAPS = "partially_overlaps"
    SPECIAL_CASE_OF = "special_case_of"
    GENERALIZATION_OF = "generalization_of"
    RELATED_TO = "related_to"


# ---------------------------------------------------------------------------
# Similarity Provider Protocol
# ---------------------------------------------------------------------------


@dataclass
class SimilarityBreakdown:
    """Multi-factor similarity breakdown."""

    lexical_similarity: float = 0.0
    semantic_similarity: float = 0.0
    epistemic_similarity: float = 0.0
    graph_similarity: float = 0.0
    hierarchical_similarity: float = 0.0
    cross_book_support: float = 0.0
    overall_similarity: float = 0.0


@dataclass
class RelationHypothesis:
    """A hypothesis about a relation between concepts."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    possible_relation: str = ""
    probability: float = 0.0
    supporting_evidence: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    limitations: list[str] = field(default_factory=list)


@dataclass
class AmbiguousRelation:
    """A relation that cannot be confidently classified."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_concept: str = ""
    target_concept: str = ""
    possible_relations: list[str] = field(default_factory=list)
    probabilities: dict[str, float] = field(default_factory=dict)
    supporting_evidence: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    recommended_resolution: str = ""
    similarity_score: float = 0.0
    confidence: float = 0.0
    provenance_bundle_id: str = ""


@dataclass
class CrossBookDiff:
    """Tracks what changed when a new book is imported."""

    affected_concepts: list[str] = field(default_factory=list)
    affected_relations: list[str] = field(default_factory=list)
    affected_books: list[str] = field(default_factory=list)
    new_concepts: list[str] = field(default_factory=list)
    new_relations: list[str] = field(default_factory=list)


@dataclass
class SemanticEdge:
    """A semantic edge between concepts across books."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_concept_id: str = ""
    target_concept_id: str = ""
    relation_type: str = ""

    # Similarity breakdown
    similarity_breakdown: SimilarityBreakdown = field(default_factory=SimilarityBreakdown)
    similarity_score: float = 0.0

    # Confidence
    confidence: float = 0.0
    confidence_breakdown: dict[str, float] = field(default_factory=dict)

    # Ambiguity
    ambiguity: float = 0.0
    reason: str = ""

    # Provenance
    provenance_bundle_id: str = ""
    evidence_references: list[str] = field(default_factory=list)
    supporting_books: list[str] = field(default_factory=list)
    supporting_chapters: list[str] = field(default_factory=list)
    supporting_evidence: list[str] = field(default_factory=list)
    supporting_profiles: list[str] = field(default_factory=list)
    supporting_graph_edges: list[str] = field(default_factory=list)

    # Scope and conditions
    scope: str = ""
    conditions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    # Versioning
    graph_version: int = 0
    engine_version: str = "1.0.0"
    similarity_provider: str = "rule_based"
    provider_version: str = "1.0.0"
    version: int = 1
    is_active: bool = True
    created_by: str = "system"

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class LinkingResult:
    """Result of cross-book linking operation."""

    edges_created: int = 0
    edges_skipped: int = 0
    ambiguous_relations: list[AmbiguousRelation] = field(default_factory=list)
    affected_concepts: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


@dataclass
class IncrementalLinkPlan:
    """Plan for incremental linking of a new book."""

    new_book_id: str = ""
    affected_concepts: list[str] = field(default_factory=list)
    concepts_to_compare: list[str] = field(default_factory=list)
    existing_concepts: list[str] = field(default_factory=list)
    estimated_comparisons: int = 0
