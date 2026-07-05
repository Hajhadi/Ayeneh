"""MEM-09 Knowledge Graph — core graph operations.

Implements the pipeline: Evidence → CognitiveObjects → RelationshipExtraction
→ GraphConstruction → GraphValidation → KnowledgeGraphUpdate → Reasoning
→ Reflection → Prediction.
"""

from __future__ import annotations

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.knowledge_graph.types import (
    GraphEdge,
    GraphLayer,
    GraphNode,
    GraphPipelineStage,
    GraphQueryResult,
    KnowledgeGraphSnapshot,
    NodeCategory,
    RelationshipCategory,
    RelationshipExtraction,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# In-memory graph store
# ---------------------------------------------------------------------------

class KnowledgeGraph:
    """In-memory knowledge graph with add/remove/query operations."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._adjacency: dict[str, set[str]] = {}  # node_id -> set of edge_ids
        self._reverse_adj: dict[str, set[str]] = {}
        self._version: int = 1

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    @property
    def version(self) -> int:
        return self._version

    # -- node operations -----------------------------------------------------

    def add_node(self, node: GraphNode) -> None:
        self._nodes[node.node_id] = node
        self._adjacency.setdefault(node.node_id, set())
        self._reverse_adj.setdefault(node.node_id, set())
        self._version += 1
        logger.debug('graph.node_added', node_id=node.node_id, category=node.category.value)

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        # Remove all connected edges
        edge_ids = self._adjacency.get(node_id, set()) | self._reverse_adj.get(node_id, set())
        for eid in list(edge_ids):
            self._remove_edge_by_id(eid)
        del self._nodes[node_id]
        self._adjacency.pop(node_id, None)
        self._reverse_adj.pop(node_id, None)
        self._version += 1
        return True

    def get_nodes_by_category(self, category: NodeCategory) -> list[GraphNode]:
        return [n for n in self._nodes.values() if n.category == category]

    def get_nodes_by_layer(self, layer: GraphLayer) -> list[GraphNode]:
        return [n for n in self._nodes.values() if n.layer == layer]

    # -- edge operations -----------------------------------------------------

    def add_edge(self, edge: GraphEdge) -> None:
        self._edges[edge.edge_id] = edge
        self._adjacency.setdefault(edge.source_node, set()).add(edge.edge_id)
        self._reverse_adj.setdefault(edge.target_node, set()).add(edge.edge_id)
        self._version += 1
        logger.debug('graph.edge_added', edge_id=edge.edge_id, relationship=edge.relationship.value)

    def get_edge(self, edge_id: str) -> GraphEdge | None:
        return self._edges.get(edge_id)

    def remove_edge(self, edge_id: str) -> bool:
        return self._remove_edge_by_id(edge_id)

    def _remove_edge_by_id(self, edge_id: str) -> bool:
        if edge_id not in self._edges:
            return False
        edge = self._edges[edge_id]
        self._adjacency.get(edge.source_node, set()).discard(edge_id)
        self._reverse_adj.get(edge.target_node, set()).discard(edge_id)
        del self._edges[edge_id]
        self._version += 1
        return True

    # -- query operations ----------------------------------------------------

    def neighbors(self, node_id: str, direction: str = 'both') -> list[GraphNode]:
        """Get neighboring nodes. direction: 'out', 'in', or 'both'."""
        neighbor_ids: set[str] = set()
        if direction in ('out', 'both'):
            for eid in self._adjacency.get(node_id, set()):
                edge = self._edges.get(eid)
                if edge:
                    neighbor_ids.add(edge.target_node)
        if direction in ('in', 'both'):
            for eid in self._reverse_adj.get(node_id, set()):
                edge = self._edges.get(eid)
                if edge:
                    neighbor_ids.add(edge.source_node)
        return [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]

    def edges_between(self, source: str, target: str) -> list[GraphEdge]:
        """Get all edges from source to target."""
        result: list[GraphEdge] = []
        for eid in self._adjacency.get(source, set()):
            edge = self._edges.get(eid)
            if edge and edge.target_node == target:
                result.append(edge)
        return result

    def find_path(
        self,
        start: str,
        end: str,
        max_depth: int = 5,
    ) -> list[str] | None:
        """BFS shortest path between two nodes. Returns list of node_ids or None."""
        if start == end:
            return [start]
        from collections import deque

        visited: set[str] = {start}
        queue: deque[tuple[str, list[str]]] = deque([(start, [start])])

        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue
            for neighbor in self.neighbors(current, 'both'):
                if neighbor.node_id == end:
                    return path + [neighbor.node_id]
                if neighbor.node_id not in visited:
                    visited.add(neighbor.node_id)
                    queue.append((neighbor.node_id, path + [neighbor.node_id]))
        return None

    # -- relationship extraction ---------------------------------------------

    def extract_relationships(
        self,
        source_id: str,
        target_id: str,
        evidence_ids: tuple[str, ...] = (),
    ) -> list[RelationshipExtraction]:
        """Extract potential relationships between two cognitive objects."""
        extractions: list[RelationshipExtraction] = []
        source = self.get_node(source_id)
        target = self.get_node(target_id)
        if source is None or target is None:
            return extractions

        # Heuristic relationship inference based on categories
        cat_pair = (source.category, target.category)
        if cat_pair in _INFERRED_RELATIONSHIPS:
            for rel in _INFERRED_RELATIONSHIPS[cat_pair]:
                extractions.append(
                    RelationshipExtraction(
                        source_id=source_id,
                        target_id=target_id,
                        relationship=rel,
                        confidence=0.6,
                        evidence_ids=evidence_ids,
                        extraction_method='category_heuristic',
                    )
                )

        # Fallback: always possible to associate
        if not extractions:
            extractions.append(
                RelationshipExtraction(
                    source_id=source_id,
                    target_id=target_id,
                    relationship=RelationshipCategory.ASSOCIATED_WITH,
                    confidence=0.3,
                    evidence_ids=evidence_ids,
                    extraction_method='fallback',
                )
            )

        return extractions

    def apply_extraction(self, extraction: RelationshipExtraction) -> GraphEdge | None:
        """Add an extracted relationship as an edge if confidence is sufficient."""
        if extraction.confidence < 0.2:
            return None
        edge = GraphEdge(
            edge_id=f'edge_{extraction.source_id}_{extraction.target_id}_{extraction.relationship.value}',
            source_node=extraction.source_id,
            target_node=extraction.target_id,
            relationship=extraction.relationship,
            weight=extraction.confidence,
            confidence=extraction.confidence,
        )
        self.add_edge(edge)
        return edge

    # -- snapshot ------------------------------------------------------------

    def snapshot(self) -> KnowledgeGraphSnapshot:
        """Create a point-in-time snapshot of the graph."""
        return KnowledgeGraphSnapshot(
            snapshot_id=f'snap_v{self._version}',
            nodes=tuple(self._nodes.values()),
            edges=tuple(self._edges.values()),
            timestamp=datetime.now(UTC),
            version=self._version,
        )


# Category-pair → possible relationships mapping
_INFERRED_RELATIONSHIPS: dict[tuple[NodeCategory, NodeCategory], list[RelationshipCategory]] = {
    (NodeCategory.EVIDENCE, NodeCategory.BELIEFS): [RelationshipCategory.SUPPORTS, RelationshipCategory.CONFIRMED_BY],
    (NodeCategory.EVIDENCE, NodeCategory.NARRATIVES): [RelationshipCategory.SUPPORTS],
    (NodeCategory.GOALS, NodeCategory.BEHAVIORAL_PATTERNS): [RelationshipCategory.INFLUENCES],
    (NodeCategory.IDENTITY_COMPONENTS, NodeCategory.BEHAVIORAL_PATTERNS): [RelationshipCategory.INFLUENCES],
    (NodeCategory.BELIEFS, NodeCategory.GOALS): [RelationshipCategory.INFLUENCES, RelationshipCategory.ENABLES],
    (NodeCategory.EPISODES, NodeCategory.SEMANTIC_MEMORIES): [RelationshipCategory.DERIVED_FROM],
    (NodeCategory.EPISODES, NodeCategory.NARRATIVES): [RelationshipCategory.PART_OF],
    (NodeCategory.LIFE_CHAPTERS, NodeCategory.EPISODES): [RelationshipCategory.CONTAINS],
    (NodeCategory.PROJECTS, NodeCategory.GOALS): [RelationshipCategory.ENABLES],
    (NodeCategory.PEOPLE, NodeCategory.EPISODES): [RelationshipCategory.OBSERVED_IN],
    (NodeCategory.PLACES, NodeCategory.EPISODES): [RelationshipCategory.OBSERVED_IN],
    (NodeCategory.BOOKS, NodeCategory.CONCEPTS): [RelationshipCategory.REFERENCES],
    (NodeCategory.PREDICTIONS, NodeCategory.REALITY_OBJECTS): [RelationshipCategory.PREDICTS],
    (NodeCategory.META_COGNITIVE_OBJECTS, NodeCategory.BELIEFS): [RelationshipCategory.STRENGTHENS, RelationshipCategory.WEAKENS],
}
