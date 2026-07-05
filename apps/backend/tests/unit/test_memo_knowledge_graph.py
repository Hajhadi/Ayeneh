"""Tests for MEM-09 Knowledge Graph module."""

from __future__ import annotations

import pytest

from ayeneh.memo.knowledge_graph.analytics import (
    compute_all,
    compute_centrality,
    compute_clustering,
    compute_connectivity,
    compute_coherence,
    compute_density,
    compute_rigidity,
)
from ayeneh.memo.knowledge_graph.graph import KnowledgeGraph
from ayeneh.memo.knowledge_graph.integrity import (
    IntegrityReport,
    validate_duplicate_edges,
    validate_graph,
    validate_layer_consistency,
    validate_orphan_edges,
    validate_self_loops,
    validate_node_uniqueness,
)
from ayeneh.memo.knowledge_graph.types import (
    GraphAnalytics,
    GraphEdge,
    GraphLayer,
    GraphNode,
    GraphQueryResult,
    KnowledgeGraphSnapshot,
    NodeCategory,
    RelationshipCategory,
    RelationshipExtraction,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _node(node_id: str, category: NodeCategory = NodeCategory.CONCEPTS, layer: GraphLayer = GraphLayer.SEMANTIC) -> GraphNode:
    return GraphNode(node_id=node_id, label=node_id, category=category, layer=layer)


def _edge(edge_id: str, source: str, target: str, rel: RelationshipCategory = RelationshipCategory.ASSOCIATED_WITH) -> GraphEdge:
    return GraphEdge(edge_id=edge_id, source_node=source, target_node=target, relationship=rel)


def _build_triangle_graph() -> KnowledgeGraph:
    g = KnowledgeGraph()
    g.add_node(_node('a'))
    g.add_node(_node('b'))
    g.add_node(_node('c'))
    g.add_edge(_edge('e1', 'a', 'b'))
    g.add_edge(_edge('e2', 'b', 'c'))
    g.add_edge(_edge('e3', 'c', 'a'))
    return g


# ---------------------------------------------------------------------------
# Graph node operations
# ---------------------------------------------------------------------------

class TestGraphNodeOperations:
    def test_add_and_get_node(self) -> None:
        g = KnowledgeGraph()
        n = _node('n1')
        g.add_node(n)
        assert g.get_node('n1') is n

    def test_remove_node(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('n1'))
        assert g.remove_node('n1') is True
        assert g.get_node('n1') is None

    def test_remove_nonexistent_node(self) -> None:
        g = KnowledgeGraph()
        assert g.remove_node('ghost') is False

    def test_get_nodes_by_category(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a', NodeCategory.BELIEFS))
        g.add_node(_node('b', NodeCategory.GOALS))
        g.add_node(_node('c', NodeCategory.BELIEFS))
        beliefs = g.get_nodes_by_category(NodeCategory.BELIEFS)
        assert len(beliefs) == 2

    def test_get_nodes_by_layer(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a', layer=GraphLayer.IDENTITY))
        g.add_node(_node('b', layer=GraphLayer.SEMANTIC))
        identity_nodes = g.get_nodes_by_layer(GraphLayer.IDENTITY)
        assert len(identity_nodes) == 1

    def test_version_increments(self) -> None:
        g = KnowledgeGraph()
        v0 = g.version
        g.add_node(_node('n1'))
        assert g.version > v0


# ---------------------------------------------------------------------------
# Graph edge operations
# ---------------------------------------------------------------------------

class TestGraphEdgeOperations:
    def test_add_and_get_edge(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a'))
        g.add_node(_node('b'))
        e = _edge('e1', 'a', 'b')
        g.add_edge(e)
        assert g.get_edge('e1') is e

    def test_remove_edge(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a'))
        g.add_node(_node('b'))
        g.add_edge(_edge('e1', 'a', 'b'))
        assert g.remove_edge('e1') is True
        assert g.get_edge('e1') is None

    def test_remove_node_removes_edges(self) -> None:
        g = _build_triangle_graph()
        g.remove_node('a')
        assert g.get_edge('e1') is None
        assert g.get_edge('e3') is None

    def test_edges_between(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a'))
        g.add_node(_node('b'))
        g.add_edge(_edge('e1', 'a', 'b'))
        g.add_edge(_edge('e2', 'a', 'b'))
        edges = g.edges_between('a', 'b')
        assert len(edges) == 2


# ---------------------------------------------------------------------------
# Graph queries
# ---------------------------------------------------------------------------

class TestGraphQueries:
    def test_neighbors_out(self) -> None:
        g = _build_triangle_graph()
        neighbors = g.neighbors('a', 'out')
        ids = {n.node_id for n in neighbors}
        assert 'b' in ids

    def test_neighbors_in(self) -> None:
        g = _build_triangle_graph()
        neighbors = g.neighbors('a', 'in')
        ids = {n.node_id for n in neighbors}
        assert 'c' in ids

    def test_neighbors_both(self) -> None:
        g = _build_triangle_graph()
        neighbors = g.neighbors('a', 'both')
        ids = {n.node_id for n in neighbors}
        assert 'b' in ids and 'c' in ids

    def test_find_path(self) -> None:
        g = _build_triangle_graph()
        path = g.find_path('a', 'c')
        assert path is not None
        assert path[0] == 'a'
        assert path[-1] == 'c'

    def test_find_path_no_route(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a'))
        g.add_node(_node('b'))
        assert g.find_path('a', 'b') is None

    def test_find_path_same_node(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a'))
        assert g.find_path('a', 'a') == ['a']


# ---------------------------------------------------------------------------
# Relationship extraction
# ---------------------------------------------------------------------------

class TestRelationshipExtraction:
    def test_extract_evidence_belief(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('ev', NodeCategory.EVIDENCE))
        g.add_node(_node('bel', NodeCategory.BELIEFS))
        extractions = g.extract_relationships('ev', 'bel')
        assert len(extractions) > 0
        rel_types = {e.relationship for e in extractions}
        assert RelationshipCategory.SUPPORTS in rel_types or RelationshipCategory.ASSOCIATED_WITH in rel_types

    def test_extract_unknown_pair_fallback(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('x', NodeCategory.CONCEPTS))
        g.add_node(_node('y', NodeCategory.PLACES))
        extractions = g.extract_relationships('x', 'y')
        assert any(e.relationship == RelationshipCategory.ASSOCIATED_WITH for e in extractions)

    def test_apply_extraction(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a'))
        g.add_node(_node('b'))
        ext = RelationshipExtraction(
            source_id='a',
            target_id='b',
            relationship=RelationshipCategory.SUPPORTS,
            confidence=0.8,
        )
        edge = g.apply_extraction(ext)
        assert edge is not None
        assert g.edge_count == 1

    def test_low_confidence_not_applied(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a'))
        g.add_node(_node('b'))
        ext = RelationshipExtraction(source_id='a', target_id='b', confidence=0.1)
        edge = g.apply_extraction(ext)
        assert edge is None


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

class TestSnapshot:
    def test_snapshot_captures_state(self) -> None:
        g = _build_triangle_graph()
        snap = g.snapshot()
        assert isinstance(snap, KnowledgeGraphSnapshot)
        assert len(snap.nodes) == 3
        assert len(snap.edges) == 3


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

class TestAnalytics:
    def test_centrality(self) -> None:
        g = _build_triangle_graph()
        cent = compute_centrality(g)
        assert 'a' in cent
        assert cent['a'] > 0.0

    def test_density(self) -> None:
        g = _build_triangle_graph()
        d = compute_density(g)
        assert 0.0 <= d <= 1.0

    def test_coherence(self) -> None:
        g = _build_triangle_graph()
        c = compute_coherence(g)
        assert 0.0 <= c <= 1.0

    def test_clustering(self) -> None:
        g = _build_triangle_graph()
        cl = compute_clustering(g)
        assert 'a' in cl

    def test_rigidity(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a'))
        g.add_node(_node('b'))
        g.add_edge(_edge('e1', 'a', 'b'))
        g.add_edge(_edge('e2', 'b', 'a'))
        r = compute_rigidity(g)
        assert r > 0.0

    def test_connectivity(self) -> None:
        g = _build_triangle_graph()
        c = compute_connectivity(g)
        assert c > 0.0

    def test_compute_all(self) -> None:
        g = _build_triangle_graph()
        analytics = compute_all(g)
        assert isinstance(analytics, GraphAnalytics)
        assert analytics.node_count == 3
        assert analytics.edge_count == 3

    def test_empty_graph_analytics(self) -> None:
        g = KnowledgeGraph()
        analytics = compute_all(g)
        assert analytics.node_count == 0
        assert analytics.density == 0.0


# ---------------------------------------------------------------------------
# Integrity validation
# ---------------------------------------------------------------------------

class TestIntegrity:
    def test_valid_graph(self) -> None:
        g = _build_triangle_graph()
        report = validate_graph(g)
        assert report.is_valid is True

    def test_orphan_edge(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a'))
        g.add_edge(_edge('e1', 'a', 'ghost'))
        violations = validate_orphan_edges(g)
        assert len(violations) == 1
        assert violations[0].violation_type == 'orphan_edge'

    def test_self_loop(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a'))
        g.add_edge(_edge('e1', 'a', 'a'))
        violations = validate_self_loops(g)
        assert len(violations) == 1

    def test_duplicate_edge(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a'))
        g.add_node(_node('b'))
        g.add_edge(_edge('e1', 'a', 'b', RelationshipCategory.SUPPORTS))
        g.add_edge(_edge('e2', 'a', 'b', RelationshipCategory.SUPPORTS))
        violations = validate_duplicate_edges(g)
        assert len(violations) == 1

    def test_valid_graph_has_no_violations(self) -> None:
        g = _build_triangle_graph()
        report = validate_graph(g)
        assert len(report.violations) == 0

    def test_report_fields(self) -> None:
        g = _build_triangle_graph()
        report = validate_graph(g)
        assert isinstance(report, IntegrityReport)
        assert report.node_count == 3
        assert report.edge_count == 3


# ---------------------------------------------------------------------------
# Node/edge counts
# ---------------------------------------------------------------------------

class TestCounts:
    def test_node_count(self) -> None:
        g = KnowledgeGraph()
        assert g.node_count == 0
        g.add_node(_node('a'))
        assert g.node_count == 1

    def test_edge_count(self) -> None:
        g = KnowledgeGraph()
        g.add_node(_node('a'))
        g.add_node(_node('b'))
        g.add_edge(_edge('e1', 'a', 'b'))
        assert g.edge_count == 1
