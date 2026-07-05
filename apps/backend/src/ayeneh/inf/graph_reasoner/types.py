"""INF-02 Graph Reasoner types.

Defines GraphReasoningObject, GraphReasoningResult, and supporting
value objects for graph-based reasoning over knowledge networks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

TRAVERSAL_STRATEGIES: list[str] = [
    'breadth_first',
    'depth_first',
    'importance_guided',
    'evidence_guided',
    'identity_guided',
    'narrative_guided',
    'contradiction_guided',
    'goal_guided',
]

PATTERN_TYPES: list[str] = [
    'hub_concept',
    'dependency_chain',
    'feedback_loop',
    'bridge_node',
    'isolated_cluster',
    'emergent_community',
    'contradiction_cluster',
    'reinforcement_loop',
]

NODE_IMPORTANCE_FACTORS: list[str] = [
    'connection_count',
    'evidence_count',
    'inference_count',
    'centrality',
    'recency',
    'confidence',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraversalStep:
    """A single step in a graph traversal."""

    step_id: str
    from_node: str
    to_node: str
    relationship_type: str
    weight: float = 0.0
    depth: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StructuralPattern:
    """A pattern detected in graph structure."""

    pattern_id: str
    pattern_type: str
    node_ids: tuple[str, ...] = ()
    description: str = ''
    confidence: float = 0.0
    evidence_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SubgraphResult:
    """A subgraph extracted during reasoning."""

    nodes: tuple[dict[str, Any], ...] = ()
    edges: tuple[dict[str, Any], ...] = ()
    root_node: str = ''
    depth: int = 0
    node_count: int = 0
    edge_count: int = 0


@dataclass(frozen=True)
class AlternativePath:
    """An alternative reasoning path through the graph."""

    path_id: str
    nodes: tuple[str, ...] = ()
    confidence: float = 0.0
    explanation: str = ''
    length: int = 0


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GraphReasoningObject:
    """A reasoning session over the knowledge graph (INF-02)."""

    reasoning_id: str
    starting_nodes: tuple[str, ...] = ()
    traversal_strategy: str = 'breadth_first'
    visited_nodes: tuple[str, ...] = ()
    visited_relationships: tuple[str, ...] = ()
    generated_subgraph: dict[str, Any] = field(default_factory=dict)
    detected_patterns: tuple[dict[str, Any], ...] = ()
    supporting_evidence: tuple[str, ...] = ()
    reasoning_confidence: float = 0.0
    traversal_depth: int = 0
    alternative_paths: tuple[dict[str, Any], ...] = ()
    version_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphReasoningResult:
    """Complete result of the graph reasoning pipeline."""

    reasoning_object: GraphReasoningObject = field(default_factory=lambda: GraphReasoningObject(reasoning_id=''))
    subgraph: SubgraphResult = field(default_factory=SubgraphResult)
    patterns: tuple[StructuralPattern, ...] = ()
    traversals: tuple[TraversalStep, ...] = ()
    alternative_paths: tuple[AlternativePath, ...] = ()
    inferences: tuple[dict[str, Any], ...] = ()
    calibration_notes: tuple[str, ...] = ()
    overall_confidence: float = 0.0
    processing_metadata: dict[str, Any] = field(default_factory=dict)
