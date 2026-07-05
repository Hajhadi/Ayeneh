"""Cognitive property graph for the Ayeneh COG architecture.

Provides a directed, typed property graph that stores all cognitive objects
as nodes and their relationships (supports, contradicts, depends_on, …) as
edges.  Downstream modules (belief network, narrative engine, …) query this
graph to reason over the full cognitive model.
"""

from __future__ import annotations

import structlog
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ayeneh.cog.base import CognitiveObject, EvidenceRef

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Supported relationship types
# ---------------------------------------------------------------------------

RELATIONSHIP_TYPES: frozenset[str] = frozenset({
    'supports',
    'contradicts',
    'depends_on',
    'explains',
    'caused_by',
    'strengthens',
    'weakens',
    'evolved_into',
})


# ---------------------------------------------------------------------------
# GraphEdge
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GraphEdge:
    """A typed, weighted, evidence-backed directed edge."""

    source_id: str
    target_id: str
    relationship: str
    confidence: float
    evidence_refs: tuple[EvidenceRef, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    creation_rationale: str = ''


# ---------------------------------------------------------------------------
# CognitiveGraph
# ---------------------------------------------------------------------------

class CognitiveGraph:
    """Directed property graph for all cognitive objects.

    Nodes are stored by ``CognitiveObject.identifier``; edges are kept in
    adjacency-friendly lists and indexed by source/target for fast lookup.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, CognitiveObject] = {}
        self._edges: list[GraphEdge] = []
        self._outgoing: dict[str, list[GraphEdge]] = {}
        self._incoming: dict[str, list[GraphEdge]] = {}

    # -- mutation ------------------------------------------------------------

    def add_node(self, obj: CognitiveObject) -> None:
        """Insert or replace a cognitive object node."""
        self._nodes[obj.identifier] = obj
        logger.debug('cog.graph.node_added', node_id=obj.identifier, obj_type=obj.object_type)

    def add_edge(self, edge: GraphEdge) -> None:
        """Append a directed edge.  Both endpoints must already exist."""
        if edge.source_id not in self._nodes:
            raise ValueError(f"Source node not found: {edge.source_id}")
        if edge.target_id not in self._nodes:
            raise ValueError(f"Target node not found: {edge.target_id}")

        if edge.relationship not in RELATIONSHIP_TYPES:
            raise ValueError(f"Unknown relationship type: {edge.relationship}")

        self._edges.append(edge)
        self._outgoing.setdefault(edge.source_id, []).append(edge)
        self._incoming.setdefault(edge.target_id, []).append(edge)
        logger.debug(
            'cog.graph.edge_added',
            source=edge.source_id,
            target=edge.target_id,
            rel=edge.relationship,
        )

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all incident edges."""
        self._nodes.pop(node_id, None)
        self._edges = [
            e for e in self._edges
            if e.source_id != node_id and e.target_id != node_id
        ]
        self._outgoing.pop(node_id, None)
        self._incoming.pop(node_id, None)
        self._outgoing = {k: [e for e in v if e.target_id != node_id] for k, v in self._outgoing.items()}
        self._incoming = {k: [e for e in v if e.source_id != node_id] for k, v in self._incoming.items()}

    # -- queries -------------------------------------------------------------

    def get_node(self, identifier: str) -> CognitiveObject | None:
        """Return the node for *identifier*, or ``None``."""
        return self._nodes.get(identifier)

    def get_edges_from(self, node_id: str) -> list[GraphEdge]:
        """Return all outgoing edges from *node_id*."""
        return list(self._outgoing.get(node_id, []))

    def get_edges_to(self, node_id: str) -> list[GraphEdge]:
        """Return all incoming edges to *node_id*."""
        return list(self._incoming.get(node_id, []))

    def nodes(self) -> list[CognitiveObject]:
        """Return all nodes in the graph."""
        return list(self._nodes.values())

    def edges(self) -> list[GraphEdge]:
        """Return all edges in the graph."""
        return list(self._edges)

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    # -- traversal -----------------------------------------------------------

    def traverse(
        self,
        start_id: str,
        relationship: str,
        max_depth: int = 5,
    ) -> list[CognitiveObject]:
        """BFS traversal following edges of *relationship* type.

        Returns discovered nodes (excluding *start_id*) in BFS order.
        """
        visited: set[str] = set()
        result: list[CognitiveObject] = []
        queue: deque[tuple[str, int]] = deque()
        queue.append((start_id, 0))

        while queue:
            current_id, depth = queue.popleft()
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)

            if current_id != start_id:
                node = self._nodes.get(current_id)
                if node is not None:
                    result.append(node)

            for edge in self._outgoing.get(current_id, []):
                if edge.relationship == relationship and edge.target_id not in visited:
                    queue.append((edge.target_id, depth + 1))

        return result

    def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 6,
    ) -> list[CognitiveObject] | None:
        """BFS shortest path between two nodes (any relationship type).

        Returns the ordered list of intermediate nodes, or ``None`` if
        no path exists within *max_depth*.
        """
        visited: set[str] = set()
        queue: deque[tuple[str, list[str]]] = deque()
        queue.append((start_id, [start_id]))

        while queue:
            current_id, path = queue.popleft()
            if current_id == end_id:
                return [self._nodes[nid] for nid in path[1:-1] if nid in self._nodes]
            if current_id in visited or len(path) > max_depth:
                continue
            visited.add(current_id)

            for edge in self._outgoing.get(current_id, []):
                if edge.target_id not in visited:
                    queue.append((edge.target_id, path + [edge.target_id]))

        return None
