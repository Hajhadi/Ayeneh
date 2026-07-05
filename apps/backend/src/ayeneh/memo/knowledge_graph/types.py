"""Types for MEM-09 Knowledge Graph module.

Defines node categories, relationship categories, multi-layer structure,
graph analytics results, and the pipeline stages that maintain a
knowledge graph over cognitive objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Node categories (19)
# ---------------------------------------------------------------------------

class NodeCategory(str, Enum):
    """Canonical categories for knowledge-graph nodes."""

    EVIDENCE = 'Evidence'
    EPISODES = 'Episodes'
    LIFE_CHAPTERS = 'LifeChapters'
    SEMANTIC_MEMORIES = 'SemanticMemories'
    BELIEFS = 'Beliefs'
    NARRATIVES = 'Narratives'
    GOALS = 'Goals'
    VALUES = 'Values'
    IDENTITY_COMPONENTS = 'IdentityComponents'
    BEHAVIORAL_PATTERNS = 'BehavioralPatterns'
    PROJECTS = 'Projects'
    BOOKS = 'Books'
    PEOPLE = 'People'
    ORGANIZATIONS = 'Organizations'
    PLACES = 'Places'
    CONCEPTS = 'Concepts'
    PREDICTIONS = 'Predictions'
    REALITY_OBJECTS = 'RealityObjects'
    META_COGNITIVE_OBJECTS = 'MetaCognitiveObjects'


# ---------------------------------------------------------------------------
# Relationship categories (20)
# ---------------------------------------------------------------------------

class RelationshipCategory(str, Enum):
    """Canonical edge types in the knowledge graph."""

    SUPPORTS = 'supports'
    CONTRADICTS = 'contradicts'
    CAUSES = 'causes'
    ENABLES = 'enables'
    BLOCKS = 'blocks'
    DERIVED_FROM = 'derived_from'
    ASSOCIATED_WITH = 'associated_with'
    PART_OF = 'part_of'
    CONTAINS = 'contains'
    INFLUENCES = 'influences'
    PREDICTS = 'predicts'
    STRENGTHENS = 'strengthens'
    WEAKENS = 'weakens'
    PRECEDES = 'precedes'
    FOLLOWS = 'follows'
    EVOLVED_INTO = 'evolved_into'
    REPLACED_BY = 'replaced_by'
    REFERENCES = 'references'
    OBSERVED_IN = 'observed_in'
    CONFIRMED_BY = 'confirmed_by'


# ---------------------------------------------------------------------------
# Multi-layer levels (6)
# ---------------------------------------------------------------------------

class GraphLayer(str, Enum):
    """Abstraction layers in the knowledge graph."""

    EVIDENCE = 'Evidence'
    EPISODE = 'Episode'
    SEMANTIC = 'Semantic'
    BEHAVIOR = 'Behavior'
    IDENTITY = 'Identity'
    META_COGNITIVE = 'MetaCognitive'


LAYER_ORDER: list[GraphLayer] = [
    GraphLayer.EVIDENCE,
    GraphLayer.EPISODE,
    GraphLayer.SEMANTIC,
    GraphLayer.BEHAVIOR,
    GraphLayer.IDENTITY,
    GraphLayer.META_COGNITIVE,
]


# ---------------------------------------------------------------------------
# Graph pipeline stages
# ---------------------------------------------------------------------------

class GraphPipelineStage(str, Enum):
    """Stages of the knowledge-graph pipeline."""

    RELATIONSHIP_EXTRACTION = 'RelationshipExtraction'
    GRAPH_CONSTRUCTION = 'GraphConstruction'
    GRAPH_VALIDATION = 'GraphValidation'
    KNOWLEDGE_GRAPH_UPDATE = 'KnowledgeGraphUpdate'
    REASONING = 'Reasoning'
    REFLECTION = 'Reflection'
    PREDICTION = 'Prediction'


# ---------------------------------------------------------------------------
# Graph node
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GraphNode:
    """A single node in the knowledge graph."""

    node_id: str
    label: str = ''
    category: NodeCategory = NodeCategory.CONCEPTS
    layer: GraphLayer = GraphLayer.SEMANTIC
    properties: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Graph edge (relationship)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GraphEdge:
    """A directed edge between two nodes."""

    edge_id: str
    source_node: str = ''
    target_node: str = ''
    relationship: RelationshipCategory = RelationshipCategory.ASSOCIATED_WITH
    weight: float = 1.0
    confidence: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Graph analytics results
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GraphAnalytics:
    """Aggregated analytics computed over the knowledge graph."""

    centrality: dict[str, float] = field(default_factory=dict)
    density: float = 0.0
    coherence: float = 0.0
    clustering: dict[str, float] = field(default_factory=dict)
    rigidity: float = 0.0
    connectivity: float = 0.0
    node_count: int = 0
    edge_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Relationship extraction result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RelationshipExtraction:
    """A newly extracted relationship waiting to be inserted into the graph."""

    source_id: str = ''
    target_id: str = ''
    relationship: RelationshipCategory = RelationshipCategory.ASSOCIATED_WITH
    confidence: float = 0.0
    evidence_ids: tuple[str, ...] = ()
    extraction_method: str = ''


# ---------------------------------------------------------------------------
# Graph query result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GraphQueryResult:
    """Result of a graph query (e.g. shortest path, neighborhood)."""

    query_type: str = ''
    result_nodes: tuple[str, ...] = ()
    result_edges: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Knowledge graph snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KnowledgeGraphSnapshot:
    """Point-in-time snapshot of the entire knowledge graph."""

    snapshot_id: str = ''
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    analytics: GraphAnalytics | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1
