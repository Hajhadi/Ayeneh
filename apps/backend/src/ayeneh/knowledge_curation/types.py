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
    hierarchy: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)


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
    evidence: list[str] = field(default_factory=list)
    reason: str = ""
    provenance: str = ""

    # Scope
    scope: str = ""
    conditions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    # Authority comparison
    source_authority: str = ""
    target_authority: str = ""
    authority_domain: str = ""

    # Versioning
    version: int = 1
    is_active: bool = True

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Graph Metrics
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeGraphMetrics:
    """Metrics about the knowledge graph."""

    node_count: int = 0
    edge_count: int = 0
    agreements: int = 0
    conflicts: int = 0
    complementary: int = 0
    authority_relations: int = 0
    scope_relations: int = 0
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
