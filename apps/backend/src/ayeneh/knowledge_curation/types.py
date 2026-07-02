"""Knowledge Curation types — core domain objects for knowledge relationships."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


# ---------------------------------------------------------------------------
# Node Types
# ---------------------------------------------------------------------------


class NodeType(StrEnum):
    """Types of nodes in the knowledge graph."""

    BOOK = "book"
    CHAPTER = "chapter"
    TOPIC = "topic"
    CONCEPT = "concept"
    TRADITION = "tradition"
    FRAMEWORK = "framework"
    AUTHOR = "author"
    SCHOOL = "school"


# ---------------------------------------------------------------------------
# Edge Types
# ---------------------------------------------------------------------------


class RelationType(StrEnum):
    """Types of relations between knowledge sources."""

    SUPPORTS = "supports"
    EXTENDS = "extends"
    CONTRADICTS = "contradicts"
    COMPLEMENTS = "complements"
    SPECIALIZES = "specializes"
    GENERALIZES = "generalizes"
    SHARES_CONCEPT = "shares_concept"
    SHARES_FRAMEWORK = "shares_framework"
    DIFFERENT_SCOPE = "different_scope"
    DIFFERENT_EVIDENCE = "different_evidence"
    HISTORICAL_INFLUENCE = "historical_influence"

    # Semantic graph relations
    CONTAINS = "contains"
    APPEARS_IN = "appears_in"
    BELONGS_TO = "belongs_to"
    RELATED_TO = "related_to"


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeNode:
    """Base node in the knowledge graph."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: str = NodeType.BOOK
    title: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)
    provenance_bundle_id: str = ""
    version: int = 1
    is_current: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class DocumentNode(KnowledgeNode):
    """Node representing a document (book or chapter)."""

    document_id: str = ""
    book_id: str = ""
    chapter_id: str | None = None
    author: str = ""
    language: str = "en"
    domains: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    authority: str = "secondary"
    evidence_level: str = "philosophical"
    traditions: list[str] = field(default_factory=list)


@dataclass
class ConceptNode(KnowledgeNode):
    """Node representing a normalized concept."""

    canonical_name: str = ""
    aliases: list[str] = field(default_factory=list)
    definition: str = ""
    domain: str = ""
    language: str = "en"
    hierarchy: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    epistemic_profile_ids: list[str] = field(default_factory=list)
    confidence_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass
class TopicNode(KnowledgeNode):
    """Node representing a topic grouping concepts."""

    concept_ids: list[str] = field(default_factory=list)
    book_id: str = ""
    chapter_id: str = ""
    epistemic_profile_id: str = ""
    hierarchical_profile_id: str = ""
    confidence: float = 0.5


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeEdge:
    """Edge representing a relationship between knowledge sources."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: str = RelationType.SUPPORTS

    # Relationship properties
    confidence: float = 0.5
    confidence_breakdown: dict[str, float] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    evidence_references: list[str] = field(default_factory=list)
    reason: str = ""
    provenance_bundle_id: str = ""

    # Scope
    scope: str = ""
    conditions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    # Authority comparison
    source_authority: str = ""
    target_authority: str = ""
    authority_domain: str = ""

    # Engine version
    engine_version: str = "1.0.0"

    # Versioning (append-only: version increments, never modifies)
    version: int = 1
    is_active: bool = True

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class GraphVersion:
    """A snapshot of the graph at a point in time."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version_number: int = 0
    node_count: int = 0
    edge_count: int = 0
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    node_snapshot: dict[str, dict] = field(default_factory=dict)
    edge_snapshot: dict[str, dict] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Graph Metrics
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeGraphMetrics:
    """Metrics about the knowledge graph."""

    # Node counts
    node_count: int = 0
    book_count: int = 0
    chapter_count: int = 0
    topic_count: int = 0
    concept_count: int = 0

    # Edge counts
    edge_count: int = 0
    agreements: int = 0
    conflicts: int = 0
    complementary: int = 0
    authority_relations: int = 0
    scope_relations: int = 0
    contains_edges: int = 0
    appears_in_edges: int = 0
    belongs_to_edges: int = 0
    related_to_edges: int = 0

    # Density
    concept_density: float = 0.0
    topic_density: float = 0.0

    # Cross-book
    cross_book_concepts: int = 0
    isolated_concepts: int = 0
    isolated_topics: int = 0

    # Connectivity
    average_degree: float = 0.0
    most_connected_concepts: list[str] = field(default_factory=list)
    most_connected_topics: list[str] = field(default_factory=list)

    # Growth
    graph_growth_rate: float = 0.0

    # Confidence
    average_confidence: float = 0.0
    active_edges: int = 0
    inactive_edges: int = 0


# ---------------------------------------------------------------------------
# Concept Normalization
# ---------------------------------------------------------------------------


@dataclass
class NormalizedConcept:
    """A normalized concept with aliases and hierarchy."""

    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    domain: str = ""
    definition: str = ""
    hierarchy: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    confidence: float = 0.5


# ---------------------------------------------------------------------------
# Relation Analysis Results
# ---------------------------------------------------------------------------


@dataclass
class AgreementAnalysis:
    """Result of agreement detection between two sources."""

    source_id: str = ""
    target_id: str = ""
    agreement_confidence: float = 0.0
    supporting_evidence: list[str] = field(default_factory=list)
    scope: str = ""
    limitations: list[str] = field(default_factory=list)


@dataclass
class ConflictAnalysis:
    """Result of conflict detection between two sources."""

    source_id: str = ""
    target_id: str = ""
    conflict_description: str = ""
    conflict_confidence: float = 0.0
    what_conflicts: list[str] = field(default_factory=list)
    why_conflicts: list[str] = field(default_factory=list)
    scope: str = ""
    possible_reconciliation: str = ""
    is_resolved: bool = False


@dataclass
class ComplementarityAnalysis:
    """Result of complementarity detection."""

    source_id: str = ""
    target_id: str = ""
    complementarity_confidence: float = 0.0
    different_questions: list[str] = field(default_factory=list)
    different_perspectives: list[str] = field(default_factory=list)
    scope: str = ""


@dataclass
class AuthorityComparison:
    """Result of authority comparison between sources."""

    concept: str = ""
    source_id: str = ""
    target_id: str = ""
    source_authority: str = ""
    target_authority: str = ""
    domain: str = ""
    comparison: str = ""  # "source_higher" | "target_higher" | "equal" | "different_domains"
