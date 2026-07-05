"""MEM-09 Knowledge Graph analytics.

Computes centrality, density, coherence, clustering, rigidity, and
connectivity metrics over the knowledge graph.
"""

from __future__ import annotations

from ayeneh.memo.knowledge_graph.graph import KnowledgeGraph
from ayeneh.memo.knowledge_graph.types import GraphAnalytics, GraphNode


def compute_centrality(graph: KnowledgeGraph) -> dict[str, float]:
    """Compute degree centrality for each node (normalised)."""
    max_possible = max(graph.node_count - 1, 1)
    centrality: dict[str, float] = {}
    for node_id in set(graph._adjacency.keys()) | set(graph._reverse_adj.keys()):
        out_degree = len(graph._adjacency.get(node_id, set()))
        in_degree = len(graph._reverse_adj.get(node_id, set()))
        centrality[node_id] = (out_degree + in_degree) / max_possible
    return centrality


def compute_density(graph: KnowledgeGraph) -> float:
    """Compute graph density: actual edges / possible edges."""
    n = graph.node_count
    if n <= 1:
        return 0.0
    max_edges = n * (n - 1)
    return graph.edge_count / max_edges


def compute_coherence(graph: KnowledgeGraph) -> float:
    """Compute coherence as the fraction of edges between same-layer nodes."""
    if graph.edge_count == 0:
        return 0.0
    coherent = 0
    for edge in graph._edges.values():
        src = graph.get_node(edge.source_node)
        tgt = graph.get_node(edge.target_node)
        if src and tgt and src.layer == tgt.layer:
            coherent += 1
    return coherent / graph.edge_count


def compute_clustering(graph: KnowledgeGraph) -> dict[str, float]:
    """Compute local clustering coefficient for each node."""
    clustering: dict[str, float] = {}
    for node_id in graph._nodes:
        neighbors = graph.neighbors(node_id, 'both')
        neighbor_ids = {n.node_id for n in neighbors}
        k = len(neighbor_ids)
        if k <= 1:
            clustering[node_id] = 0.0
            continue
        # Count edges among neighbors
        edges_among = 0
        for nid in neighbor_ids:
            for other in graph.neighbors(nid, 'both'):
                if other.node_id in neighbor_ids and other.node_id != nid:
                    edges_among += 1
        # Each edge counted twice
        clustering[node_id] = edges_among / (k * (k - 1))
    return clustering


def compute_rigidity(graph: KnowledgeGraph) -> float:
    """Compute rigidity: fraction of edges that are bidirectional (strong ties)."""
    if graph.edge_count == 0:
        return 0.0
    bidirectional = 0
    for edge in graph._edges.values():
        reverse = graph.edges_between(edge.target_node, edge.source_node)
        if reverse:
            bidirectional += 1
    return bidirectional / graph.edge_count


def compute_connectivity(graph: KnowledgeGraph) -> float:
    """Compute connectivity: fraction of node pairs reachable from each other."""
    nodes = list(graph._nodes.keys())
    n = len(nodes)
    if n <= 1:
        return 1.0
    reachable_pairs = 0
    total_pairs = n * (n - 1)
    # Sample if graph is large
    sample_size = min(n, 50)
    sampled = nodes[:sample_size]
    for start in sampled:
        visited: set[str] = set()
        stack = [start]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for neighbor in graph.neighbors(current, 'both'):
                if neighbor.node_id not in visited:
                    stack.append(neighbor.node_id)
        reachable_pairs += len(visited) - 1  # exclude self

    actual_pairs = sample_size * (sample_size - 1)
    return reachable_pairs / actual_pairs if actual_pairs > 0 else 0.0


def compute_all(graph: KnowledgeGraph) -> GraphAnalytics:
    """Compute all analytics and return a GraphAnalytics object."""
    return GraphAnalytics(
        centrality=compute_centrality(graph),
        density=compute_density(graph),
        coherence=compute_coherence(graph),
        clustering=compute_clustering(graph),
        rigidity=compute_rigidity(graph),
        connectivity=compute_connectivity(graph),
        node_count=graph.node_count,
        edge_count=graph.edge_count,
    )
