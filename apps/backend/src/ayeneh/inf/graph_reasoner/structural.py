"""INF-02 Structural Reasoning.

Detects structural patterns in knowledge graphs:
- Highly connected concepts (hubs)
- Repeated dependency chains
- Feedback loops
- Bridging nodes
- Isolated clusters
- Emergent communities
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.inf.graph_reasoner.types import (
    PATTERN_TYPES,
    StructuralPattern,
)

logger = structlog.get_logger(__name__)


class StructuralReasoning:
    """Detects structural patterns in knowledge graphs (INF-02 helper).

    Analyzes graph topology to find patterns that inform reasoning:
    - Hub concepts: nodes with many connections
    - Dependency chains: sequential dependency relationships
    - Feedback loops: cycles in the graph
    - Bridge nodes: nodes connecting separate clusters
    - Isolated clusters: disconnected subgraphs
    - Emergent communities: densely connected groups
    """

    def detect_patterns(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> tuple[StructuralPattern, ...]:
        """Detect all structural patterns in the graph."""
        logger.debug(
            'inf.graph_reasoner.structural.detect_patterns',
            node_count=len(nodes),
            edge_count=len(edges),
        )

        patterns: list[StructuralPattern] = []

        patterns.extend(self._detect_hubs(nodes, edges))
        patterns.extend(self._detect_dependency_chains(nodes, edges))
        patterns.extend(self._detect_feedback_loops(nodes, edges))
        patterns.extend(self._detect_bridge_nodes(nodes, edges))
        patterns.extend(self._detect_isolated_clusters(nodes, edges))
        patterns.extend(self._detect_emergent_communities(nodes, edges))

        return tuple(patterns)

    # ------------------------------------------------------------------
    # Pattern detectors
    # ------------------------------------------------------------------

    def _detect_hubs(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> list[StructuralPattern]:
        """Detect highly connected hub nodes."""
        connection_counts: dict[str, int] = {}
        for edge in edges:
            src = edge.get('source', '')
            tgt = edge.get('target', '')
            connection_counts[src] = connection_counts.get(src, 0) + 1
            connection_counts[tgt] = connection_counts.get(tgt, 0) + 1

        if not connection_counts:
            return []

        max_connections = max(connection_counts.values())
        threshold = max(max_connections * 0.6, 3)

        patterns: list[StructuralPattern] = []
        for node_id, count in connection_counts.items():
            if count >= threshold:
                patterns.append(StructuralPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type='hub_concept',
                    node_ids=(node_id,),
                    description=f'Node {node_id} is a hub with {count} connections',
                    confidence=min(count / max_connections, 1.0),
                    evidence_count=count,
                ))

        return patterns

    def _detect_dependency_chains(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> list[StructuralPattern]:
        """Detect repeated dependency chain patterns."""
        # Build adjacency for dependency-like edges
        dep_edges = [
            e for e in edges
            if e.get('type', '') in ('depends_on', 'requires', 'derived_from', 'causes')
        ]

        if not dep_edges:
            return []

        # Find chains: sequences of A→B→C
        adjacency: dict[str, list[str]] = {}
        for edge in dep_edges:
            src = edge.get('source', '')
            tgt = edge.get('target', '')
            adjacency.setdefault(src, []).append(tgt)

        patterns: list[StructuralPattern] = []
        visited_chains: set[tuple[str, ...]] = set()

        for start_node in adjacency:
            chain = self._trace_chain(start_node, adjacency, set(), max_depth=5)
            if len(chain) >= 3:
                chain_tuple = tuple(chain)
                if chain_tuple not in visited_chains:
                    visited_chains.add(chain_tuple)
                    patterns.append(StructuralPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type='dependency_chain',
                        node_ids=chain_tuple,
                        description=f'Dependency chain: {" → ".join(chain)}',
                        confidence=0.7,
                        evidence_count=len(chain) - 1,
                    ))

        return patterns

    def _trace_chain(
        self,
        start: str,
        adjacency: dict[str, list[str]],
        visited: set[str],
        max_depth: int = 5,
    ) -> list[str]:
        """Trace a dependency chain from a starting node."""
        if start in visited or max_depth <= 0:
            return [start]

        visited.add(start)
        chain = [start]

        targets = adjacency.get(start, [])
        if targets:
            next_node = targets[0]
            chain.extend(self._trace_chain(next_node, adjacency, visited, max_depth - 1))

        return chain

    def _detect_feedback_loops(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> list[StructuralPattern]:
        """Detect cycles/feedback loops in the graph."""
        adjacency: dict[str, list[str]] = {}
        for edge in edges:
            src = edge.get('source', '')
            tgt = edge.get('target', '')
            adjacency.setdefault(src, []).append(tgt)

        patterns: list[StructuralPattern] = []
        visited_global: set[str] = set()

        for start_node in adjacency:
            if start_node in visited_global:
                continue
            cycle = self._detect_cycle(start_node, adjacency, set())
            if cycle:
                for node in cycle:
                    visited_global.add(node)
                patterns.append(StructuralPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type='feedback_loop',
                    node_ids=tuple(cycle),
                    description=f'Feedback loop: {" → ".join(cycle)} → {cycle[0]}',
                    confidence=0.8,
                    evidence_count=len(cycle),
                ))

        return patterns

    def _detect_cycle(
        self,
        start: str,
        adjacency: dict[str, list[str]],
        visited: set[str],
    ) -> list[str] | None:
        """Detect a cycle starting from a given node."""
        if start in visited:
            return [start]

        visited.add(start)
        for target in adjacency.get(start, []):
            result = self._detect_cycle(target, adjacency, visited)
            if result:
                if result[0] == start:
                    return result
                return [start] + result

        visited.discard(start)
        return None

    def _detect_bridge_nodes(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> list[StructuralPattern]:
        """Detect bridge nodes that connect separate clusters."""
        if not nodes:
            return []

        adjacency: dict[str, set[str]] = {}
        for edge in edges:
            src = edge.get('source', '')
            tgt = edge.get('target', '')
            adjacency.setdefault(src, set()).add(tgt)
            adjacency.setdefault(tgt, set()).add(src)

        patterns: list[StructuralPattern] = []
        node_ids = [n.get('id', '') for n in nodes]

        for node_id in node_ids:
            neighbors = adjacency.get(node_id, set())
            if len(neighbors) < 2:
                continue

            # Check if removing this node disconnects the graph
            remaining = set(node_ids) - {node_id}
            if not remaining:
                continue

            # Simple bridge detection: node connects to otherwise separate groups
            neighbor_groups: list[set[str]] = []
            visited: set[str] = set()

            for neighbor in neighbors:
                if neighbor not in visited and neighbor in remaining:
                    group = self._bfs_component(neighbor, adjacency, remaining)
                    visited.update(group)
                    neighbor_groups.append(group)

            if len(neighbor_groups) > 1:
                patterns.append(StructuralPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type='bridge_node',
                    node_ids=(node_id,),
                    description=f'Node {node_id} bridges {len(neighbor_groups)} clusters',
                    confidence=0.7,
                    evidence_count=len(neighbors),
                ))

        return patterns

    def _bfs_component(
        self,
        start: str,
        adjacency: dict[str, set[str]],
        valid_nodes: set[str],
    ) -> set[str]:
        """BFS to find connected component."""
        component: set[str] = set()
        queue = [start]
        while queue:
            node = queue.pop(0)
            if node in component or node not in valid_nodes:
                continue
            component.add(node)
            for neighbor in adjacency.get(node, set()):
                if neighbor not in component and neighbor in valid_nodes:
                    queue.append(neighbor)
        return component

    def _detect_isolated_clusters(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> list[StructuralPattern]:
        """Detect isolated clusters (disconnected subgraphs)."""
        adjacency: dict[str, set[str]] = {}
        for edge in edges:
            src = edge.get('source', '')
            tgt = edge.get('target', '')
            adjacency.setdefault(src, set()).add(tgt)
            adjacency.setdefault(tgt, set()).add(src)

        node_ids = [n.get('id', '') for n in nodes]
        visited: set[str] = set()
        patterns: list[StructuralPattern] = []

        for node_id in node_ids:
            if node_id not in visited:
                component = self._bfs_component(node_id, adjacency, set(node_ids))
                visited.update(component)

                # Check if this is an isolated cluster (no external connections)
                has_external = False
                for c_node in component:
                    for neighbor in adjacency.get(c_node, set()):
                        if neighbor not in component:
                            has_external = True
                            break
                    if has_external:
                        break

                if not has_external and len(component) >= 2:
                    patterns.append(StructuralPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type='isolated_cluster',
                        node_ids=tuple(component),
                        description=f'Isolated cluster of {len(component)} nodes',
                        confidence=0.6,
                        evidence_count=len(component),
                    ))

        return patterns

    def _detect_emergent_communities(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> list[StructuralPattern]:
        """Detect emergent communities (densely connected groups)."""
        adjacency: dict[str, set[str]] = {}
        for edge in edges:
            src = edge.get('source', '')
            tgt = edge.get('target', '')
            adjacency.setdefault(src, set()).add(tgt)
            adjacency.setdefault(tgt, set()).add(src)

        node_ids = [n.get('id', '') for n in nodes]
        patterns: list[StructuralPattern] = []

        # Simple community detection: find groups where internal density > 0.5
        visited: set[str] = set()
        for node_id in node_ids:
            if node_id in visited:
                continue

            neighbors = adjacency.get(node_id, set())
            community = {node_id} | neighbors

            # Calculate internal density
            internal_edges = 0
            possible_edges = len(community) * (len(community) - 1) // 2
            if possible_edges == 0:
                continue

            for n1 in community:
                for n2 in community:
                    if n1 < n2 and n2 in adjacency.get(n1, set()):
                        internal_edges += 1

            density = internal_edges / possible_edges
            if density > 0.5 and len(community) >= 3:
                visited.update(community)
                patterns.append(StructuralPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type='emergent_community',
                    node_ids=tuple(sorted(community)),
                    description=f'Emergent community of {len(community)} nodes (density: {density:.2f})',
                    confidence=density,
                    evidence_count=internal_edges,
                ))

        return patterns
