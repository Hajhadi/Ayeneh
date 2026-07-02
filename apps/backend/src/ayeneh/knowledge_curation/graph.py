"""KnowledgeGraph — multi-layer semantic graph with versioning."""

from __future__ import annotations

from typing import Any

import structlog

from ayeneh.knowledge_curation.types import (
    GraphVersion,
    KnowledgeEdge,
    KnowledgeGraphMetrics,
    KnowledgeNode,
    RelationType,
)

logger = structlog.get_logger(__name__)


class KnowledgeGraph:
    """Multi-layer semantic graph with append-only versioning.

    Stores nodes and edges with efficient lookup capabilities.
    Supports graph versioning for historical reconstruction.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: dict[str, KnowledgeEdge] = {}
        self._adjacency: dict[str, set[str]] = {}
        self._versions: list[GraphVersion] = []
        self._version_counter: int = 0

    # ------------------------------------------------------------------
    # Versioning
    # ------------------------------------------------------------------

    def create_version(self, description: str = "") -> GraphVersion:
        """Create a snapshot of the current graph state."""
        self._version_counter += 1
        version = GraphVersion(
            version_number=self._version_counter,
            node_count=len(self._nodes),
            edge_count=len(self._edges),
            description=description,
            node_snapshot={nid: self._node_to_dict(n) for nid, n in self._nodes.items()},
            edge_snapshot={eid: self._edge_to_dict(e) for eid, e in self._edges.items()},
        )
        self._versions.append(version)
        return version

    def get_version(self, version_number: int) -> GraphVersion | None:
        """Get a specific version."""
        for v in self._versions:
            if v.version_number == version_number:
                return v
        return None

    def get_latest_version(self) -> GraphVersion | None:
        """Get the latest version."""
        return self._versions[-1] if self._versions else None

    def get_versions(self) -> list[GraphVersion]:
        """Get all versions."""
        return list(self._versions)

    def restore_version(self, version_number: int) -> bool:
        """Restore graph to a specific version."""
        version = self.get_version(version_number)
        if version is None:
            return False
        self._nodes = {
            nid: self._node_from_dict(data)
            for nid, data in version.node_snapshot.items()
        }
        self._edges = {
            eid: self._edge_from_dict(data)
            for eid, data in version.edge_snapshot.items()
        }
        self._adjacency = {}
        for nid in self._nodes:
            self._adjacency[nid] = set()
        for eid, edge in self._edges.items():
            self._adjacency.setdefault(edge.source_id, set()).add(eid)
            self._adjacency.setdefault(edge.target_id, set()).add(eid)
        return True

    def _node_to_dict(self, node: KnowledgeNode) -> dict:
        """Convert node to dictionary for snapshot."""
        return {
            "id": node.id,
            "node_type": node.node_type,
            "title": node.title,
            "version": node.version,
            "is_current": node.is_current,
        }

    def _node_from_dict(self, data: dict) -> KnowledgeNode:
        """Create node from dictionary."""
        return KnowledgeNode(
            id=data["id"],
            node_type=data["node_type"],
            title=data["title"],
            version=data.get("version", 1),
            is_current=data.get("is_current", True),
        )

    def _edge_to_dict(self, edge: KnowledgeEdge) -> dict:
        """Convert edge to dictionary for snapshot."""
        return {
            "id": edge.id,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "relation_type": edge.relation_type,
            "version": edge.version,
            "is_active": edge.is_active,
        }

    def _edge_from_dict(self, data: dict) -> KnowledgeEdge:
        """Create edge from dictionary."""
        return KnowledgeEdge(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=data["relation_type"],
            version=data.get("version", 1),
            is_active=data.get("is_active", True),
        )

    # ------------------------------------------------------------------
    # Node operations (append-only)
    # ------------------------------------------------------------------

    def add_node(self, node: KnowledgeNode) -> None:
        """Add a node to the graph (append-only)."""
        if node.id in self._nodes:
            existing = self._nodes[node.id]
            node.version = existing.version + 1
            node.created_at = existing.created_at
        self._nodes[node.id] = node
        self._adjacency.setdefault(node.id, set())

    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the graph (marks inactive for versioning)."""
        if node_id not in self._nodes:
            return False

        # Mark as inactive for versioning
        self._nodes[node_id].is_current = False

        # Remove edges connected to this node
        edge_ids = list(self._adjacency.get(node_id, set()))
        for edge_id in edge_ids:
            if edge_id in self._edges:
                self._edges[edge_id].is_active = False

        self._adjacency.pop(node_id, None)
        return True

    def get_node(self, node_id: str) -> KnowledgeNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_nodes_by_type(self, node_type: str) -> list[KnowledgeNode]:
        """Get all nodes of a specific type."""
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def get_current_nodes(self) -> list[KnowledgeNode]:
        """Get only current (non-historical) nodes."""
        return [n for n in self._nodes.values() if n.is_current]

    # ------------------------------------------------------------------
    # Edge operations (append-only)
    # ------------------------------------------------------------------

    def add_edge(self, edge: KnowledgeEdge) -> None:
        """Add an edge to the graph (append-only)."""
        if edge.id in self._edges:
            existing = self._edges[edge.id]
            edge.version = existing.version + 1
            edge.created_at = existing.created_at
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
        """Get all active edges to a node."""
        edge_ids = self._adjacency.get(node_id, set())
        return [
            self._edges[eid]
            for eid in edge_ids
            if eid in self._edges
            and self._edges[eid].target_id == node_id
            and self._edges[eid].is_active
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

    # ------------------------------------------------------------------
    # Query APIs
    # ------------------------------------------------------------------

    def find_concept(self, canonical_name: str) -> list[KnowledgeNode]:
        """Find concept nodes by canonical name."""
        return [
            n for n in self._nodes.values()
            if n.node_type == "concept"
            and hasattr(n, "canonical_name")
            and n.canonical_name.lower() == canonical_name.lower()
        ]

    def find_topic(self, name: str) -> list[KnowledgeNode]:
        """Find topic nodes by name."""
        return [
            n for n in self._nodes.values()
            if n.node_type == "topic"
            and n.title.lower() == name.lower()
        ]

    def find_books_for_concept(self, concept_name: str) -> list[KnowledgeNode]:
        """Find all books discussing a concept."""
        concepts = self.find_concept(concept_name)
        if not concepts:
            return []

        book_ids: set[str] = set()
        for concept in concepts:
            edges = self.get_edges_to_node(concept.id)
            for edge in edges:
                if edge.relation_type in ("appears_in", "contains"):
                    book_ids.add(edge.source_id)

        return [self._nodes[bid] for bid in book_ids if bid in self._nodes]

    def find_topics_for_concept(self, concept_name: str) -> list[KnowledgeNode]:
        """Find all topics related to a concept."""
        concepts = self.find_concept(concept_name)
        if not concepts:
            return []

        topic_ids: set[str] = set()
        for concept in concepts:
            edges = self.get_edges_to_node(concept.id)
            for edge in edges:
                if edge.relation_type == "belongs_to":
                    topic_ids.add(edge.source_id)

        return [self._nodes[tid] for tid in topic_ids if tid in self._nodes]

    def find_neighboring_concepts(self, concept_name: str) -> list[KnowledgeNode]:
        """Find neighboring concepts."""
        concepts = self.find_concept(concept_name)
        if not concepts:
            return []

        neighbor_ids: set[str] = set()
        for concept in concepts:
            neighbors = self.get_neighbors(concept.id)
            for neighbor in neighbors:
                if neighbor.node_type == "concept":
                    neighbor_ids.add(neighbor.id)

        return [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]

    def find_concept_evidence(self, concept_name: str) -> list[dict[str, Any]]:
        """Find evidence for a concept."""
        concepts = self.find_concept(concept_name)
        evidence: list[dict[str, Any]] = []

        for concept in concepts:
            edges = self.get_edges_to_node(concept.id)
            for edge in edges:
                if edge.relation_type in ("appears_in", "contains"):
                    evidence.append({
                        "source_id": edge.source_id,
                        "relation": edge.relation_type,
                        "confidence": edge.confidence,
                        "provenance_bundle_id": edge.provenance_bundle_id,
                    })

        return evidence

    # ------------------------------------------------------------------
    # Path queries
    # ------------------------------------------------------------------

    def find_path(
        self, start_id: str, end_id: str, max_depth: int = 5,
    ) -> list[str] | None:
        """Find shortest path between two nodes using BFS."""
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

    def find_all_paths(
        self, start_id: str, end_id: str, max_depth: int = 4,
    ) -> list[list[str]]:
        """Find all paths between two nodes."""
        all_paths: list[list[str]] = []
        self._dfs_paths(start_id, end_id, max_depth, [start_id], set(), all_paths)
        return all_paths

    def _dfs_paths(
        self,
        current: str,
        end: str,
        max_depth: int,
        path: list[str],
        visited: set[str],
        all_paths: list[list[str]],
    ) -> None:
        """DFS helper for finding all paths."""
        if current == end:
            all_paths.append(list(path))
            return

        if len(path) > max_depth:
            return

        for neighbor in self.get_neighbors(current):
            if neighbor.id not in visited:
                visited.add(neighbor.id)
                path.append(neighbor.id)
                self._dfs_paths(neighbor.id, end, max_depth, path, visited, all_paths)
                path.pop()
                visited.discard(neighbor.id)

    # ------------------------------------------------------------------
    # Neighbors
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

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self) -> KnowledgeGraphMetrics:
        """Get comprehensive graph metrics."""
        book_count = len(self.get_nodes_by_type("book"))
        chapter_count = len(self.get_nodes_by_type("chapter"))
        topic_count = len(self.get_nodes_by_type("topic"))
        concept_count = len(self.get_nodes_by_type("concept"))

        agreements = len(self.get_edges_by_type(RelationType.SUPPORTS))
        conflicts = len(self.get_edges_by_type(RelationType.CONTRADICTS))
        complementary = len(self.get_edges_by_type(RelationType.COMPLEMENTS))
        contains_edges = len(self.get_edges_by_type(RelationType.CONTAINS))
        appears_in_edges = len(self.get_edges_by_type(RelationType.APPEARS_IN))
        belongs_to_edges = len(self.get_edges_by_type(RelationType.BELONGS_TO))
        related_to_edges = len(self.get_edges_by_type(RelationType.RELATED_TO))

        total_nodes = len(self._nodes)
        concept_density = concept_count / total_nodes if total_nodes > 0 else 0.0
        topic_density = topic_count / total_nodes if total_nodes > 0 else 0.0

        active = sum(1 for e in self._edges.values() if e.is_active)
        inactive = sum(1 for e in self._edges.values() if not e.is_active)

        avg_confidence = 0.0
        if self._edges:
            avg_confidence = sum(e.confidence for e in self._edges.values()) / len(self._edges)

        return KnowledgeGraphMetrics(
            node_count=total_nodes,
            book_count=book_count,
            chapter_count=chapter_count,
            topic_count=topic_count,
            concept_count=concept_count,
            edge_count=len(self._edges),
            agreements=agreements,
            conflicts=conflicts,
            complementary=complementary,
            contains_edges=contains_edges,
            appears_in_edges=appears_in_edges,
            belongs_to_edges=belongs_to_edges,
            related_to_edges=related_to_edges,
            concept_density=concept_density,
            topic_density=topic_density,
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
                {"id": n.id, "node_type": n.node_type, "title": n.title, "version": n.version}
                for n in self._nodes.values()
            ],
            "edges": [
                {"id": e.id, "source_id": e.source_id, "target_id": e.target_id,
                 "relation_type": e.relation_type, "confidence": e.confidence, "version": e.version}
                for e in self._edges.values()
            ],
        }

    def __len__(self) -> int:
        """Get total node count."""
        return len(self._nodes)

    def __contains__(self, node_id: str) -> bool:
        """Check if a node exists (only current nodes)."""
        return node_id in self._nodes and self._nodes[node_id].is_current
