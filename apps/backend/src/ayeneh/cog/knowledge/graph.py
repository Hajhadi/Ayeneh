"""COG-04 Knowledge Graph.

A sub-graph of the CognitiveGraph dedicated to personal knowledge objects.
Supports addition, connection, category-based queries, related-item lookup,
and BFS traversal.
"""

from __future__ import annotations

import structlog
from collections import deque
from typing import Any

from ayeneh.cog.knowledge.types import KnowledgeEdge, PersonalKnowledgeObject

logger = structlog.get_logger(__name__)


class KnowledgeGraph:
    """Directed, typed property graph for personal knowledge objects (COG-04).

    Nodes are PersonalKnowledgeObject instances keyed by their identifier.
    Edges are KnowledgeEdge instances carrying a relationship label.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, PersonalKnowledgeObject] = {}
        self._edges: list[KnowledgeEdge] = []
        self._outgoing: dict[str, list[KnowledgeEdge]] = {}
        self._incoming: dict[str, list[KnowledgeEdge]] = {}
        self._category_index: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_knowledge(self, pko: PersonalKnowledgeObject) -> None:
        """Add or replace a knowledge node."""
        self._nodes[pko.identifier] = pko
        self._category_index.setdefault(pko.knowledge_category, [])
        if pko.identifier not in self._category_index[pko.knowledge_category]:
            self._category_index[pko.knowledge_category].append(pko.identifier)
        logger.info('cog.knowledge_graph.node_added', node_id=pko.identifier)

    def connect(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
    ) -> None:
        """Create a directed edge between two knowledge nodes.

        Raises ValueError if either endpoint does not exist.
        """
        if source_id not in self._nodes:
            raise ValueError(f'Source node {source_id!r} not found in knowledge graph')
        if target_id not in self._nodes:
            raise ValueError(f'Target node {target_id!r} not found in knowledge graph')

        edge = KnowledgeEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            confidence=0.5,
        )
        self._edges.append(edge)
        self._outgoing.setdefault(source_id, []).append(edge)
        self._incoming.setdefault(target_id, []).append(edge)
        logger.info(
            'cog.knowledge_graph.edge_added',
            source=source_id,
            target=target_id,
            relationship=relationship,
        )

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its incident edges. Returns True if found."""
        if node_id not in self._nodes:
            return False

        del self._nodes[node_id]

        # Remove category index entry
        for cat, ids in self._category_index.items():
            if node_id in ids:
                self._category_index[cat] = [i for i in ids if i != node_id]

        # Remove incident edges
        outgoing = self._outgoing.pop(node_id, [])
        for edge in outgoing:
            self._edges = [e for e in self._edges if e is not edge]
            incoming_list = self._incoming.get(edge.target_id, [])
            self._incoming[edge.target_id] = [e for e in incoming_list if e is not edge]

        incoming = self._incoming.pop(node_id, [])
        for edge in incoming:
            self._edges = [e for e in self._edges if e is not edge]
            outgoing_list = self._outgoing.get(edge.source_id, [])
            self._outgoing[edge.source_id] = [e for e in outgoing_list if e is not edge]

        logger.info('cog.knowledge_graph.node_removed', node_id=node_id)
        return True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_node(self, identifier: str) -> PersonalKnowledgeObject | None:
        """Retrieve a node by its identifier."""
        return self._nodes.get(identifier)

    def get_by_category(self, category: str) -> list[PersonalKnowledgeObject]:
        """Return all knowledge objects in the given category."""
        ids = self._category_index.get(category, [])
        return [self._nodes[nid] for nid in ids if nid in self._nodes]

    def get_related(self, identifier: str) -> list[PersonalKnowledgeObject]:
        """Return all nodes connected to the given node (incoming + outgoing)."""
        if identifier not in self._nodes:
            return []

        related_ids: set[str] = set()
        for edge in self._outgoing.get(identifier, []):
            related_ids.add(edge.target_id)
        for edge in self._incoming.get(identifier, []):
            related_ids.add(edge.source_id)

        return [self._nodes[nid] for nid in related_ids if nid in self._nodes]

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def traverse(
        self,
        start_id: str,
        max_depth: int = 3,
    ) -> list[PersonalKnowledgeObject]:
        """BFS traversal from start_id up to max_depth hops.

        Returns discovered nodes (excluding start) in BFS order.
        """
        if start_id not in self._nodes:
            return []

        visited: set[str] = {start_id}
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        result: list[PersonalKnowledgeObject] = []

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            # Collect neighbors from both outgoing and incoming edges
            neighbor_ids: list[str] = []
            for edge in self._outgoing.get(current_id, []):
                neighbor_ids.append(edge.target_id)
            for edge in self._incoming.get(current_id, []):
                neighbor_ids.append(edge.source_id)

            for nid in neighbor_ids:
                if nid not in visited and nid in self._nodes:
                    visited.add(nid)
                    result.append(self._nodes[nid])
                    queue.append((nid, depth + 1))

        return result

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def node_count(self) -> int:
        """Return the number of nodes."""
        return len(self._nodes)

    def edge_count(self) -> int:
        """Return the number of edges."""
        return len(self._edges)

    def all_nodes(self) -> list[PersonalKnowledgeObject]:
        """Return all nodes."""
        return list(self._nodes.values())

    def all_edges(self) -> list[KnowledgeEdge]:
        """Return all edges."""
        return list(self._edges)
