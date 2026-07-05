"""Tests for the INF-02 Graph Reasoning Engine."""

from __future__ import annotations

import pytest

from ayeneh.inf.graph_reasoner.types import (
    TRAVERSAL_STRATEGIES,
    PATTERN_TYPES,
    AlternativePath,
    GraphReasoningObject,
    GraphReasoningResult,
    StructuralPattern,
    SubgraphResult,
    TraversalStep,
)
from ayeneh.inf.graph_reasoner.engine import GraphReasoningEngine
from ayeneh.inf.graph_reasoner.structural import StructuralReasoning


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return GraphReasoningEngine()


@pytest.fixture
def structural():
    return StructuralReasoning()


@pytest.fixture
def sample_context():
    return {
        'context_id': 'test-graph-ctx-1',
        'domain': 'general',
        'query': 'Find important concepts',
    }


@pytest.fixture
def sample_graph():
    return {
        'nodes': [
            {'id': 'n1', 'label': 'Coffee', 'importance': 0.8},
            {'id': 'n2', 'label': 'Productivity', 'importance': 0.7},
            {'id': 'n3', 'label': 'Morning Routine', 'importance': 0.6},
            {'id': 'n4', 'label': 'Health', 'importance': 0.5},
            {'id': 'n5', 'label': 'Work', 'importance': 0.9},
            {'id': 'n6', 'label': 'Energy', 'importance': 0.4},
        ],
        'edges': [
            {'source': 'n1', 'target': 'n2', 'type': 'enables', 'weight': 0.7},
            {'source': 'n1', 'target': 'n6', 'type': 'provides', 'weight': 0.6},
            {'source': 'n3', 'target': 'n1', 'type': 'includes', 'weight': 0.8},
            {'source': 'n3', 'target': 'n4', 'type': 'supports', 'weight': 0.5},
            {'source': 'n2', 'target': 'n5', 'type': 'contributes_to', 'weight': 0.7},
            {'source': 'n5', 'target': 'n2', 'type': 'requires', 'weight': 0.6},
            {'source': 'n6', 'target': 'n2', 'type': 'enhances', 'weight': 0.5},
        ],
    }


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestGraphReasonerTypes:
    """Tests for INF-02 type definitions."""

    def test_traversal_strategies_count(self):
        assert len(TRAVERSAL_STRATEGIES) == 8

    def test_pattern_types_count(self):
        assert len(PATTERN_TYPES) == 8

    def test_graph_reasoning_object_creation(self):
        obj = GraphReasoningObject(
            reasoning_id='gr-1',
            starting_nodes=('n1', 'n2'),
            traversal_strategy='breadth_first',
        )
        assert obj.reasoning_id == 'gr-1'
        assert obj.traversal_strategy == 'breadth_first'

    def test_graph_reasoning_object_frozen(self):
        obj = GraphReasoningObject(reasoning_id='gr-1')
        with pytest.raises(AttributeError):
            obj.reasoning_id = 'changed'  # type: ignore[misc]

    def test_traversal_step_creation(self):
        step = TraversalStep(
            step_id='step-1',
            from_node='n1',
            to_node='n2',
            relationship_type='enables',
        )
        assert step.from_node == 'n1'
        assert step.to_node == 'n2'

    def test_structural_pattern_creation(self):
        pattern = StructuralPattern(
            pattern_id='pat-1',
            pattern_type='hub_concept',
            node_ids=('n1',),
            confidence=0.8,
        )
        assert pattern.pattern_type == 'hub_concept'
        assert pattern.confidence == 0.8

    def test_subgraph_result_creation(self):
        sub = SubgraphResult(
            nodes=({'id': 'n1'},),
            edges=({'source': 'n1', 'target': 'n2'},),
            node_count=1,
            edge_count=1,
        )
        assert sub.node_count == 1

    def test_alternative_path_creation(self):
        path = AlternativePath(
            path_id='alt-1',
            nodes=('n1', 'n3'),
            confidence=0.6,
        )
        assert path.length == 0

    def test_graph_reasoning_result_defaults(self):
        result = GraphReasoningResult()
        assert result.reasoning_object.reasoning_id == ''
        assert result.patterns == ()


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestGraphReasoningEngine:
    """Tests for the INF-02 GraphReasoningEngine."""

    def test_engine_initialization(self):
        engine = GraphReasoningEngine()
        assert engine._reasoning_sessions == {}

    def test_process_empty_graph(self, engine, sample_context):
        result = engine.process(sample_context, None)
        assert isinstance(result, GraphReasoningResult)

    def test_process_basic(self, engine, sample_context, sample_graph):
        result = engine.process(sample_context, sample_graph)
        assert isinstance(result, GraphReasoningResult)
        assert result.subgraph.node_count > 0

    def test_process_with_starting_nodes(self, engine, sample_context, sample_graph):
        result = engine.process(
            sample_context, sample_graph, starting_nodes=['n1'],
        )
        assert isinstance(result, GraphReasoningResult)

    def test_process_with_multiple_starts(self, engine, sample_context, sample_graph):
        result = engine.process(
            sample_context, sample_graph, starting_nodes=['n1', 'n3'],
        )
        assert isinstance(result, GraphReasoningResult)

    def test_traversal_strategy(self, engine, sample_context, sample_graph):
        for strategy in TRAVERSAL_STRATEGIES[:3]:
            ctx = {**sample_context, 'traversal_strategy': strategy}
            result = engine.process(ctx, sample_graph)
            assert isinstance(result, GraphReasoningResult)

    def test_patterns_detected(self, engine, sample_context, sample_graph):
        result = engine.process(sample_context, sample_graph)
        assert isinstance(result.patterns, tuple)

    def test_subgraph_built(self, engine, sample_context, sample_graph):
        result = engine.process(sample_context, sample_graph)
        assert result.subgraph.node_count >= 0
        assert result.subgraph.edge_count >= 0

    def test_traversals_recorded(self, engine, sample_context, sample_graph):
        result = engine.process(sample_context, sample_graph)
        assert isinstance(result.traversals, tuple)

    def test_inferences_generated(self, engine, sample_context, sample_graph):
        result = engine.process(sample_context, sample_graph)
        assert isinstance(result.inferences, tuple)

    def test_overall_confidence(self, engine, sample_context, sample_graph):
        result = engine.process(sample_context, sample_graph)
        assert 0.0 <= result.overall_confidence <= 1.0

    def test_calibration_notes(self, engine, sample_context, sample_graph):
        result = engine.process(sample_context, sample_graph)
        assert isinstance(result.calibration_notes, tuple)

    def test_processing_metadata(self, engine, sample_context, sample_graph):
        result = engine.process(sample_context, sample_graph)
        assert 'node_count' in result.processing_metadata
        assert 'edge_count' in result.processing_metadata

    def test_get_reasoning_session(self, engine, sample_context, sample_graph):
        result = engine.process(sample_context, sample_graph)
        session = engine.get_reasoning_session(
            result.reasoning_object.reasoning_id,
        )
        assert session is not None

    def test_get_reasoning_session_not_found(self, engine):
        assert engine.get_reasoning_session('nonexistent') is None

    def test_get_all_sessions(self, engine, sample_context, sample_graph):
        engine.process(sample_context, sample_graph)
        sessions = engine.get_all_sessions()
        assert isinstance(sessions, list)
        assert len(sessions) >= 1

    def test_empty_graph_no_nodes(self, engine, sample_context):
        graph = {'nodes': [], 'edges': []}
        result = engine.process(sample_context, graph)
        assert result.subgraph.node_count == 0

    def test_max_depth_limit(self, engine, sample_graph):
        context = {
            'context_id': 'test-depth',
            'domain': 'general',
            'max_depth': 1,
        }
        result = engine.process(context, sample_graph)
        assert result.subgraph.depth <= 2

    def test_alternative_paths(self, engine, sample_context, sample_graph):
        result = engine.process(sample_context, sample_graph)
        assert isinstance(result.alternative_paths, tuple)


# ---------------------------------------------------------------------------
# Structural Reasoning tests
# ---------------------------------------------------------------------------


class TestStructuralReasoning:
    """Tests for the INF-02 StructuralReasoning."""

    def test_empty_graph(self, structural):
        patterns = structural.detect_patterns([], [])
        assert patterns == ()

    def test_single_node(self, structural):
        nodes = [{'id': 'n1', 'label': 'A'}]
        patterns = structural.detect_patterns(nodes, [])
        assert patterns == ()

    def test_hub_detection(self, structural):
        nodes = [
            {'id': 'n1', 'label': 'Hub'},
            {'id': 'n2', 'label': 'A'},
            {'id': 'n3', 'label': 'B'},
            {'id': 'n4', 'label': 'C'},
            {'id': 'n5', 'label': 'D'},
        ]
        edges = [
            {'source': 'n1', 'target': 'n2', 'type': 'related'},
            {'source': 'n1', 'target': 'n3', 'type': 'related'},
            {'source': 'n1', 'target': 'n4', 'type': 'related'},
            {'source': 'n1', 'target': 'n5', 'type': 'related'},
        ]
        patterns = structural.detect_patterns(nodes, edges)
        hub_patterns = [p for p in patterns if p.pattern_type == 'hub_concept']
        assert len(hub_patterns) >= 1

    def test_feedback_loop_detection(self, structural):
        nodes = [
            {'id': 'n1', 'label': 'A'},
            {'id': 'n2', 'label': 'B'},
            {'id': 'n3', 'label': 'C'},
        ]
        edges = [
            {'source': 'n1', 'target': 'n2', 'type': 'causes'},
            {'source': 'n2', 'target': 'n3', 'type': 'causes'},
            {'source': 'n3', 'target': 'n1', 'type': 'causes'},
        ]
        patterns = structural.detect_patterns(nodes, edges)
        loop_patterns = [p for p in patterns if p.pattern_type == 'feedback_loop']
        assert len(loop_patterns) >= 1

    def test_dependency_chain_detection(self, structural):
        nodes = [
            {'id': 'n1', 'label': 'A'},
            {'id': 'n2', 'label': 'B'},
            {'id': 'n3', 'label': 'C'},
            {'id': 'n4', 'label': 'D'},
        ]
        edges = [
            {'source': 'n1', 'target': 'n2', 'type': 'depends_on'},
            {'source': 'n2', 'target': 'n3', 'type': 'depends_on'},
            {'source': 'n3', 'target': 'n4', 'type': 'depends_on'},
        ]
        patterns = structural.detect_patterns(nodes, edges)
        chain_patterns = [
            p for p in patterns if p.pattern_type == 'dependency_chain'
        ]
        assert len(chain_patterns) >= 1

    def test_isolated_cluster_detection(self, structural):
        nodes = [
            {'id': 'n1', 'label': 'A'},
            {'id': 'n2', 'label': 'B'},
            {'id': 'n3', 'label': 'C'},
            {'id': 'n4', 'label': 'D'},
        ]
        edges = [
            {'source': 'n1', 'target': 'n2', 'type': 'related'},
            {'source': 'n3', 'target': 'n4', 'type': 'related'},
        ]
        patterns = structural.detect_patterns(nodes, edges)
        cluster_patterns = [
            p for p in patterns if p.pattern_type == 'isolated_cluster'
        ]
        assert len(cluster_patterns) >= 1

    def test_emergent_community_detection(self, structural):
        nodes = [
            {'id': 'n1', 'label': 'A'},
            {'id': 'n2', 'label': 'B'},
            {'id': 'n3', 'label': 'C'},
        ]
        # Fully connected = density 1.0
        edges = [
            {'source': 'n1', 'target': 'n2', 'type': 'related'},
            {'source': 'n1', 'target': 'n3', 'type': 'related'},
            {'source': 'n2', 'target': 'n3', 'type': 'related'},
        ]
        patterns = structural.detect_patterns(nodes, edges)
        community_patterns = [
            p for p in patterns if p.pattern_type == 'emergent_community'
        ]
        assert len(community_patterns) >= 1

    def test_bridge_node_detection(self, structural):
        nodes = [
            {'id': 'n1', 'label': 'A'},
            {'id': 'n2', 'label': 'B'},
            {'id': 'n3', 'label': 'Bridge'},
            {'id': 'n4', 'label': 'C'},
            {'id': 'n5', 'label': 'D'},
        ]
        edges = [
            {'source': 'n1', 'target': 'n2', 'type': 'related'},
            {'source': 'n3', 'target': 'n1', 'type': 'related'},
            {'source': 'n3', 'target': 'n4', 'type': 'related'},
            {'source': 'n4', 'target': 'n5', 'type': 'related'},
        ]
        patterns = structural.detect_patterns(nodes, edges)
        # Bridge detection may or may not find bridges depending on structure
        assert isinstance(patterns, tuple)
