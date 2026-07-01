"""KnowledgeGraph — in-memory graph structure for knowledge relationships."""

from __future__ import annotations

from typing import Any

import structlog

from ayeneh.knowledge_curation.types import (
    KnowledgeEdge,
    KnowledgeGraphMetrics,
    KnowledgeNode,
    RelationType,
)

logger = structlog.get_logger(__name__)


class KnowledgeGraph:
    """In-memory graph structure for knowledge relationships.

    Stores nodes and edges with efficient lookup capabilities.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: dict[str, KnowledgeEdge] = {}
        self._adjacency: dict[str, set[str]] = {}  # node_id -> set of edge_ids

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def add_node(self, node: KnowledgeNode) -> None:
        """Add a node to the graph."""
        self._nodes[node.id] = node
        self._adjacency.setdefault(node.id, set())

    def get_node(self, node_id: str) -> KnowledgeNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> list[KnowledgeNode]:
        """Get all nodes of a specific type."""
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its edges."""
        if node_id not in self._nodes:
            return False

        # Remove all edges connected to this node
        edge_ids = list(self._adjacency.get(node_id, set()))
        for edge_id in edge_ids:
            self._remove_edge(edge_id)

        del self._nodes[node_id]
        self._adjacency.pop(node_id, None)
        return True

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------

    def add_edge(self, edge: KnowledgeEdge) -> None:
        """Add an edge to the graph."""
        self._edges[edge.id] = edge
        self._adjacency.setdefault(edge.source_id, set()).add(edge.id)
        self._adjacency.setdefault(edge.target_id, set()).add(edge.id)

    def get_edge(self, edge_id: str) -> KnowledgeEdge | None:
        """Get an edge by ID."""
        return self._edges.get(edge_id)

    def get_edges_from_node(self, node_id: str) -> list[KnowledgeEdge]:
        """Get all edges from a node."""
        edge_ids = self._adjacency.get(node_id, set())
        return [
            self._edges[eid]
            for eid in edge_ids
            if eid in self._edges and self._edges[eid].source_id == node_id
        ]

    def get_edges_to_node(self, node_id: str) -> list[KnowledgeEdge]:
        """Get all edges to a node."""
        edge_ids = self._adjacency.get(node_id, set())
        return [
            self._edges[eid]
            for eid in edge_ids
            if eid in self._edges and self._edges[eid].target_id == node_id
        ]

    def get_edges_between(self, source_id: str, target_id: str) -> list[KnowledgeEdge]:
        """Get all edges between two nodes."""
        edge_ids = self._adjacency.get(source_id, set())
        return [
            self._edges[eid]
            for eid in edge_ids
            if eid in self._edges
            and self._edges[eid].source_id == source_id
            and self._edges[eid].target_id == target_id
        ]

    def get_edges_by_type(self, relation_type: str) -> list[KnowledgeEdge]:
        """Get all edges of a specific type."""
        return [e for e in self._edges.values() if e.relation_type == relation_type]

    def _remove_edge(self, edge_id: str) -> None:
        """Remove an edge from the graph."""
        if edge_id not in self._edges:
            return

        edge = self._edges[edge_id]
        self._adjacency.get(edge.source_id, set()).discard(edge_id)
        self._adjacency.get(edge.target_id, set()).discard(edge_id)
        del self._edges[edge_id]

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge."""
        if edge_id not in self._edges:
            return False
        self._remove_edge(edge_id)
        return True

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    def get_neighbors(self, node_id: str) -> list[KnowledgeNode]:
        """Get all neighboring nodes."""
        edge_ids = self._adjacency.get(node_id, set())
        neighbor_ids: set[str] = set()
        for eid in edge_ids:
            if eid in self._edges:
                edge = self._edges[eid]
                if edge.source_id == node_id:
                    neighbor_ids.add(edge.target_id)
                elif edge.target_id == node_id:
                    neighbor_ids.add(edge.source_id)
        return [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]

    def get_related_nodes(
        self, node_id: str, relation_type: str, direction: str = "outgoing",
    ) -> list[KnowledgeNode]:
        """Get nodes related by a specific relation type."""
        edge_ids = self._adjacency.get(node_id, set())
        related_ids: set[str] = set()

        for eid in edge_ids:
            if eid not in self._edges:
                continue
            edge = self._edges[eid]
            if edge.relation_type != relation_type:
                continue
            if direction == "outgoing" and edge.source_id == node_id:
                related_ids.add(edge.target_id)
            elif direction == "incoming" and edge.target_id == node_id:
                related_ids.add(edge.source_id)
            elif direction == "both":
                if edge.source_id == node_id:
                    related_ids.add(edge.target_id)
                elif edge.target_id == node_id:
                    related_ids.add(edge.source_id)

        return [self._nodes[nid] for nid in related_ids if nid in self._nodes]

    def find_path(
        self, start_id: str, end_id: str, max_depth: int = 5,
    ) -> list[str] | None:
        """Find a path between two nodes using BFS."""
        if start_id == end_id:
            return [start_id]

        visited: set[str] = {start_id}
        queue: list[list[str]] = [[start_id]]

        for _ in range(max_depth):
            next_queue: list[list[str]] = []
            for path in queue:
                current = path[-1]
                for neighbor in self.get_neighbors(current):
                    if neighbor.id == end_id:
                        return path + [neighbor.id]
                    if neighbor.id not in visited:
                        visited.add(neighbor.id)
                        next_queue.append(path + [neighbor.id])
            queue = next_queue
            if not queue:
                break

        return None

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self) -> KnowledgeGraphMetrics:
        """Get graph metrics."""
        agreements = len(self.get_edges_by_type(RelationType.SUPPORTS))
        conflicts = len(self.get_edges_by_type(RelationType.CONTRADICTS))
        complementary = len(self.get_edges_by_type(RelationType.COMPLEMENTS))
        authority_relations = len(self.get_edges_by_type(RelationType.DIFFERENT_SCOPE))
        scope_relations = len(self.get_edges_by_type(RelationType.DIFFERENT_EVIDENCE))

        active = sum(1 for e in self._edges.values() if e.is_active)
        inactive = sum(1 for e in self._edges.values() if not e.is_active)

        avg_confidence = 0.0
        if self._edges:
            avg_confidence = sum(e.confidence for e in self._edges.values()) / len(
                self._edges
            )

        return KnowledgeGraphMetrics(
            node_count=len(self._nodes),
            edge_count=len(self._edges),
            agreements=agreements,
            conflicts=conflicts,
            complementary=complementary,
            authority_relations=authority_relations,
            scope_relations=scope_relations,
            average_confidence=avg_confidence,
            active_edges=active,
            inactive_edges=inactive,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the graph to a dictionary."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "node_type": n.node_type,
                    "title": n.title,
                    "metadata": n.metadata,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {
                    "id": e.id,
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relation_type": e.relation_type,
                    "confidence": e.confidence,
                    "reason": e.reason,
                    "is_active": e.is_active,
                }
                for e in self._edges.values()
            ],
        }

    def __len__(self) -> int:
        """Get total node count."""
        return len(self._nodes)

    def __contains__(self, node_id: str) -> bool:
        """Check if a node exists."""
        return node_id in self._nodes
