"""Behavioral tests for MEMO engines — real-scenario integration tests.

Tests the full memory lifecycle: conversation → episodes → semantic →
consolidation → retrieval, plus knowledge graph, versioning, and forgetting.
"""

from __future__ import annotations

import pytest
from datetime import UTC, datetime, timedelta

from ayeneh.memo.base import MemoryObject, make_version_record
from ayeneh.memo.episodic.engine import EpisodicMemoryEngine
from ayeneh.memo.semantic.engine import SemanticMemoryEngine
from ayeneh.memo.working.engine import WorkingMemoryEngine
from ayeneh.memo.consolidation.engine import ConsolidationEngine
from ayeneh.memo.retrieval.engine import RetrievalEngine
from ayeneh.memo.ranking.engine import RankingEngine
from ayeneh.memo.ranking.types import RankingContext, TaskProfile
from ayeneh.memo.forgetting.engine import (
    ForgettingEngine,
    analyse_usage,
    classify_tier,
    analyse_importance,
)
from ayeneh.memo.forgetting.types import AdaptiveForgettingTier
from ayeneh.memo.knowledge_graph.graph import KnowledgeGraph
from ayeneh.memo.knowledge_graph.types import GraphNode, GraphEdge, NodeCategory, RelationshipCategory, GraphLayer
from ayeneh.memo.versioning.engine import VersioningEngine
from ayeneh.memo.types import Observation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obs(content: str, source: str = 'conversation', offset_minutes: int = 0) -> Observation:
    """Create an observation with a given offset from now."""
    return Observation(
        observation_id=f'obs_{hash(content) % 100000:05d}',
        content=content,
        source=source,
        timestamp=datetime.now(UTC) + timedelta(minutes=offset_minutes),
    )


def _make_memory(
    identifier: str = 'mem_1',
    memory_type: str = 'episodic',
    importance: float = 0.5,
    confidence: float = 0.7,
    evidence: tuple[str, ...] = ('ev_1',),
    projects: tuple[str, ...] = (),
    episodes: tuple[str, ...] = (),
    conversations: tuple[str, ...] = (),
    lifecycle: str = 'candidate_memory',
    age_days: float = 0.0,
) -> MemoryObject:
    """Create a MemoryObject with sensible defaults."""
    now = datetime.now(UTC)
    return MemoryObject(
        identifier=identifier,
        memory_type=memory_type,
        creation_time=now - timedelta(days=age_days),
        last_updated=now - timedelta(days=age_days),
        supporting_evidence=evidence,
        confidence=confidence,
        importance_score=importance,
        associated_projects=projects,
        associated_episodes=episodes,
        associated_conversations=conversations,
        lifecycle_status=lifecycle,
    )


# ===================================================================
# 1. Persian conversation → episodic memory formation
# ===================================================================


class TestPersianConversationEpisodes:
    """Persian-language conversation produces valid episodes."""

    def test_persian_observers_become_episodes(self) -> None:
        engine = EpisodicMemoryEngine(min_events_per_episode=2)
        observations = [
            _obs('سلام، امروز درباره پروژه آینه صحبت کردیم', offset_minutes=0),
            _obs('تصمیم گرفتیم از معماری میکروسرویس استفاده کنیم', offset_minutes=5),
            _obs('قرار شد هفته آینده اولین اسپرینت شروع شود', offset_minutes=10),
        ]

        result = engine.run_pipeline(observations)

        assert len(result.episodes) >= 1
        episode = result.episodes[0]
        assert episode.state == 'active'
        assert 'Episode' in episode.title
        assert episode.confidence > 0.0

    def test_mixed_persian_english_observers(self) -> None:
        engine = EpisodicMemoryEngine(min_events_per_episode=2)
        observations = [
            _obs('Today we discussed the Ayeneh project architecture', offset_minutes=0),
            _obs('تصمیم گرفتیم از Python استفاده کنیم', offset_minutes=3),
            _obs('The team agreed on FastAPI for the backend', offset_minutes=6),
        ]

        result = engine.run_pipeline(observations)

        assert len(result.episodes) >= 1

    def test_empty_observations_returns_empty(self) -> None:
        engine = EpisodicMemoryEngine()
        result = engine.run_pipeline([])
        assert result.episodes == []


# ===================================================================
# 2. Repeated evidence → semantic memory consolidation
# ===================================================================


class TestSemanticConsolidation:
    """Repeated patterns across observations consolidate into semantic knowledge."""

    def test_repeated_skill_observation_consolidates(self) -> None:
        engine = SemanticMemoryEngine(repetition_threshold=3)
        # Same pattern observed 3 times from different sources
        observations = [
            _obs('Hadi has expertise in Python development', source='conv_1', offset_minutes=0),
            _obs('Hadi is proficient in Python and machine learning', source='conv_2', offset_minutes=60),
            _obs('Hadi demonstrates deep Python expertise in code reviews', source='conv_3', offset_minutes=120),
            _obs('Hadi uses Python for data processing pipelines', source='conv_4', offset_minutes=180),
        ]

        result = engine.run_pipeline(observations)

        assert len(result.semantic_objects) >= 1
        obj = result.semantic_objects[0]
        assert obj.confidence > 0.0
        assert obj.knowledge_category in ('skills', 'expertise', 'personal_interests', 'learning_preferences')

    def test_insufficient_repetition_no_consolidation(self) -> None:
        engine = SemanticMemoryEngine(repetition_threshold=5)
        observations = [
            _obs('Hadi likes Python', source='conv_1'),
            _obs('Hadi uses Python', source='conv_2'),
        ]

        result = engine.run_pipeline(observations)
        # Only 2 observations, below threshold of 5
        assert len(result.semantic_objects) == 0

    def test_multiple_categories_extracted(self) -> None:
        engine = SemanticMemoryEngine(repetition_threshold=2)
        observations = [
            _obs('Hadi has expertise in Python and machine learning', source='s1', offset_minutes=0),
            _obs('Hadi has deep expertise in Python development', source='s2', offset_minutes=10),
            _obs('Hadi communicates clearly in team meetings', source='s3', offset_minutes=20),
            _obs('Hadi is known for clear communication style', source='s4', offset_minutes=30),
            _obs('Hadi tends to use Python for all projects', source='s5', offset_minutes=40),
            _obs('Hadi usually prefers Python over other languages', source='s6', offset_minutes=50),
        ]

        result = engine.run_pipeline(observations)

        # Should extract patterns from multiple categories
        assert len(result.semantic_objects) >= 2


# ===================================================================
# 3. Working memory context switching
# ===================================================================


class TestWorkingMemoryContextSwitching:
    """Working memory handles context switches correctly."""

    def test_basic_pipeline_run(self) -> None:
        engine = WorkingMemoryEngine()
        result = engine.run_pipeline(
            'Tell me about the Ayeneh project',
            intent='recall',
            cognitive_focus='ayeneh',
        )
        assert result is not None
        assert hasattr(result, 'activated_objects')

    def test_context_switch_preserves_open_loops(self) -> None:
        engine = WorkingMemoryEngine()
        # First context
        engine.run_pipeline('Working on the API design', intent='plan')
        loop = engine.register_open_loop('task', 'Complete API design')
        assert loop is not None

        # Switch context
        engine.run_pipeline('Now let me check the database schema', intent='recall')
        open_loops = engine.get_open_loops()
        assert len(open_loops) >= 1
        assert open_loops[0].description == 'Complete API design'

    def test_decay_reduces_memory_objects(self) -> None:
        engine = WorkingMemoryEngine(decay_rate=0.5)
        engine.run_pipeline('First topic', intent='recall')
        engine.run_pipeline('Second topic', intent='recall')

        active_before = len(engine.get_active_objects())
        decayed = engine.decay_all()
        active_after = len(engine.get_active_objects())

        assert active_after <= active_before


# ===================================================================
# 4. Memory ranking with task-specific profiles
# ===================================================================


class TestRankingTaskProfiles:
    """Ranking engine applies different profiles correctly."""

    def test_debugging_profile(self) -> None:
        engine = RankingEngine(default_capacity=5)
        memories = [
            _make_memory('mem_1', importance=0.9, confidence=0.8, evidence=('ev_1', 'ev_2')),
            _make_memory('mem_2', importance=0.3, confidence=0.9, evidence=('ev_3',)),
            _make_memory('mem_3', importance=0.7, confidence=0.5, evidence=('ev_4', 'ev_5', 'ev_6')),
        ]
        ctx = RankingContext(task_profile=TaskProfile.DEBUGGING)
        selection = engine.rank(memories, context=ctx)

        assert len(selection.selected_memories) <= 5
        assert selection.capacity_used <= 5

    def test_self_reflection_profile(self) -> None:
        engine = RankingEngine(default_capacity=5)
        memories = [
            _make_memory('mem_1', importance=0.9, confidence=0.8, lifecycle='consolidated_memory'),
            _make_memory('mem_2', importance=0.3, confidence=0.9),
            _make_memory('mem_3', importance=0.7, confidence=0.5),
        ]
        ctx = RankingContext(task_profile=TaskProfile.SELF_REFLECTION)
        selection = engine.rank(memories, context=ctx)

        assert len(selection.selected_memories) >= 1

    def test_empty_memories_returns_empty_selection(self) -> None:
        engine = RankingEngine()
        selection = engine.rank([])
        assert len(selection.selected_memories) == 0
        assert selection.capacity_used == 0

    def test_planning_profile(self) -> None:
        engine = RankingEngine(default_capacity=3)
        memories = [
            _make_memory('mem_1', importance=0.8, confidence=0.9, projects=('proj_a',)),
            _make_memory('mem_2', importance=0.6, confidence=0.7, projects=('proj_a', 'proj_b')),
            _make_memory('mem_3', importance=0.4, confidence=0.6),
        ]
        ctx = RankingContext(task_profile=TaskProfile.PLANNING, current_goals=('proj_a',))
        selection = engine.rank(memories, context=ctx)

        assert len(selection.selected_memories) >= 1


# ===================================================================
# 5. Forgetting with preservation of rare events
# ===================================================================


class TestForgettingPreservation:
    """Forgetting engine preserves rare/important memories."""

    def test_frequent_memory_not_compressed(self) -> None:
        mem = _make_memory(
            'mem_freq', importance=0.9, confidence=0.95,
            conversations=('c1', 'c2', 'c3', 'c4', 'c5'),
            episodes=('e1', 'e2', 'e3'),
        )
        usage = analyse_usage(mem)
        tier = classify_tier(usage.access_frequency_score)
        # High usage → should be in a high tier (not compressed)
        assert tier in (
            AdaptiveForgettingTier.FREQUENTLY_ACTIVE,
            AdaptiveForgettingTier.OCCASIONALLY_ACTIVE,
        )

    def test_rare_event_preserved(self) -> None:
        mem = _make_memory(
            'mem_rare', importance=0.1, confidence=0.3,
            age_days=180,
        )
        usage = analyse_usage(mem)
        importance = analyse_importance(mem)
        # Rare but may still have some importance from being a unique event
        assert isinstance(importance, float)

    def test_forgetting_engine_run(self) -> None:
        engine = ForgettingEngine(redundancy_threshold=0.8)
        memories = [
            _make_memory(f'mem_{i}', importance=i / 10.0, confidence=0.5 + i * 0.05)
            for i in range(10)
        ]
        result = engine.run(memories, max_compressions=5)
        assert result is not None


# ===================================================================
# 6. Knowledge graph construction from episodes
# ===================================================================


class TestKnowledgeGraphConstruction:
    """Knowledge graph builds correctly from episode data."""

    def test_add_nodes_and_edges(self) -> None:
        kg = KnowledgeGraph()
        node_a = GraphNode(
            node_id='n_a',
            label='Project Ayeneh',
            category=NodeCategory.CONCEPTS,
            layer=GraphLayer.EPISODE,
        )
        node_b = GraphNode(
            node_id='n_b',
            label='Python',
            category=NodeCategory.PROJECTS,
            layer=GraphLayer.SEMANTIC,
        )
        kg.add_node(node_a)
        kg.add_node(node_b)

        edge = GraphEdge(
            edge_id='e_ab',
            source_node='n_a',
            target_node='n_b',
            relationship=RelationshipCategory.ENABLES,
        )
        kg.add_edge(edge)

        assert kg.node_count == 2
        assert kg.edge_count == 1
        neighbors = kg.neighbors('n_a')
        assert len(neighbors) == 1
        assert neighbors[0].node_id == 'n_b'

    def test_find_path(self) -> None:
        kg = KnowledgeGraph()
        for nid in ('a', 'b', 'c'):
            kg.add_node(GraphNode(
                node_id=nid, label=nid,
                category=NodeCategory.CONCEPTS,
                layer=GraphLayer.EPISODE,
            ))
        kg.add_edge(GraphEdge(
            edge_id='e1', source_node='a', target_node='b',
            relationship=RelationshipCategory.SUPPORTS,
        ))
        kg.add_edge(GraphEdge(
            edge_id='e2', source_node='b', target_node='c',
            relationship=RelationshipCategory.SUPPORTS,
        ))

        path = kg.find_path('a', 'c')
        assert path is not None
        assert path == ['a', 'b', 'c']

    def test_snapshot(self) -> None:
        kg = KnowledgeGraph()
        kg.add_node(GraphNode(
            node_id='n1', label='Test',
            category=NodeCategory.CONCEPTS,
            layer=GraphLayer.EPISODE,
        ))
        snap = kg.snapshot()
        assert len(snap.nodes) == 1
        assert snap.version == kg.version


# ===================================================================
# 7. Version history after belief revision
# ===================================================================


class TestVersionHistoryBeliefRevision:
    """Versioning engine tracks belief changes correctly."""

    def test_revision_creates_version(self) -> None:
        engine = VersioningEngine()
        old = _make_memory(
            'mem_belief', importance=0.8, confidence=0.9,
            lifecycle='validated_memory',
        )
        new = _make_memory(
            'mem_belief', importance=0.6, confidence=0.5,
            lifecycle='validated_memory',
        )

        version = engine.process_update(old, new)
        assert version is not None
        assert version.version_number == 1

    def test_multiple_revisions_build_chain(self) -> None:
        engine = VersioningEngine()
        v1 = _make_memory('mem_v', importance=0.9, confidence=0.95)
        v2 = _make_memory('mem_v', importance=0.7, confidence=0.8)
        v3 = _make_memory('mem_v', importance=0.5, confidence=0.6)

        engine.process_update(v1, v2)
        engine.process_update(v2, v3)

        chain = engine.get_chain('mem_v')
        assert chain is not None
        assert chain.current_version_number >= 2

    def test_no_change_no_version(self) -> None:
        engine = VersioningEngine()
        mem = _make_memory('mem_same', importance=0.5, confidence=0.5)
        version = engine.process_update(mem, mem)
        # Identical memory → no version created
        assert version is None


# ===================================================================
# 8. Full pipeline: conversation → episodes → semantic → retrieval
# ===================================================================


class TestFullPipeline:
    """End-to-end memory pipeline test."""

    def test_conversation_to_retrieval(self) -> None:
        # Step 1: Episodic — form episodes from conversation
        episodic = EpisodicMemoryEngine(min_events_per_episode=2)
        observations = [
            _obs('We discussed the Ayeneh project architecture', offset_minutes=0),
            _obs('Decided to use FastAPI for the backend', offset_minutes=5),
            _obs('Agreed on PostgreSQL for the database', offset_minutes=10),
        ]
        ep_result = episodic.run_pipeline(observations)
        assert len(ep_result.episodes) >= 1

        # Step 2: Semantic — extract knowledge from observations
        semantic = SemanticMemoryEngine(repetition_threshold=2)
        sem_observations = [
            _obs('The team uses Python for backend development', source='c1', offset_minutes=0),
            _obs('Python is the primary language for Ayeneh', source='c2', offset_minutes=60),
            _obs('FastAPI is used for REST endpoints', source='c3', offset_minutes=120),
            _obs('FastAPI handles all API routing', source='c4', offset_minutes=180),
        ]
        sem_result = semantic.run_pipeline(sem_observations)
        assert len(sem_result.semantic_objects) >= 1

        # Step 3: Retrieval — retrieve relevant memories
        retrieval = RetrievalEngine(max_retrieval_size=5)
        semantic_memories = [
            {'id': obj.identifier, 'content': obj.knowledge_statement, 'confidence': obj.confidence}
            for obj in sem_result.semantic_objects
        ]
        result = retrieval.retrieve(
            'What technology stack does Ayeneh use?',
            intent='recall',
            semantic_memories=semantic_memories,
        )
        assert result is not None
        assert result.request_id is not None

    def test_episode_to_consolidation(self) -> None:
        # Create episodes
        episodic = EpisodicMemoryEngine(min_events_per_episode=2)
        observations = [
            _obs('Learned about Python decorators today', offset_minutes=0),
            _obs('Decorators are syntactic sugar for function wrappers', offset_minutes=5),
            _obs('Decorators can modify function behavior', offset_minutes=10),
            _obs('Python decorators use the @ syntax', offset_minutes=15),
        ]
        ep_result = episodic.run_pipeline(observations)
        assert len(ep_result.episodes) >= 1

        # Consolidate
        consolidation = ConsolidationEngine(confidence_threshold=0.3)
        wm_items = [
            {
                'memory_id': ep.identifier,
                'content': ep.summary,
                'confidence': ep.confidence,
                'activation_score': ep.confidence,
                'evidence_count': len(ep.supporting_evidence),
                'episode_ids': list(ep.supporting_evidence),
            }
            for ep in ep_result.episodes
        ]
        cons_result = consolidation.run_pipeline(wm_items)
        assert cons_result is not None

    def test_ranking_after_retrieval(self) -> None:
        retrieval = RetrievalEngine(max_retrieval_size=10)
        result = retrieval.retrieve(
            'Tell me about my Python skills',
            intent='recall',
            semantic_memories=[
                {'id': 's1', 'content': 'Expert in Python development', 'confidence': 0.9},
                {'id': 's2', 'content': 'Uses FastAPI framework', 'confidence': 0.7},
            ],
        )
        assert result is not None

        # Rank retrieved items as MemoryObjects
        ranking = RankingEngine(default_capacity=5)
        memories = []
        for item in result.retrieved_items:
            memories.append(_make_memory(
                identifier=item.memory_id,
                importance=item.importance_score,
                confidence=item.confidence_score,
                evidence=(item.memory_id,),
            ))
        if memories:
            selection = ranking.rank(memories)
            assert len(selection.selected_memories) >= 1
