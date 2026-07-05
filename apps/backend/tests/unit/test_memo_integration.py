"""End-to-end integration tests for the MEMO memory architecture.

Tests the full pipeline: conversation → episodic → semantic → consolidation → retrieval,
working memory assembly, knowledge graph construction, version tracking, ranking, and forgetting.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ayeneh.infrastructure.persistence.base import Base
from ayeneh.infrastructure.persistence.models.user import UserModel
from ayeneh.memo.persistence.repository import MEMRepository


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="module")
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(eng.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture()
async def session_factory(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture()
async def user(session_factory):
    s = session_factory()
    async with s.begin():
        u = UserModel(
            id=uuid.uuid4(),
            email=f"integration-{uuid.uuid4().hex[:8]}@example.com",
            display_name="Integration Test User",
            status="active",
            preferences={},
        )
        s.add(u)
        user_id = str(u.id)
    await s.close()
    return user_id


@pytest_asyncio.fixture()
async def repo(session_factory):
    s = session_factory()
    yield MEMRepository(s)
    await s.rollback()
    await s.close()


# ---------------------------------------------------------------------------
# Full pipeline: conversation → episodic → semantic → consolidation → retrieval
# ---------------------------------------------------------------------------

class TestFullMemoryPipeline:
    @pytest.mark.asyncio
    async def test_episode_to_semantic_to_consolidation(self, repo: MEMRepository, user):
        # 1. Create episodic memory from a conversation
        episode_id = await repo.save_episode(user, {
            "title": "Deep Python Discussion",
            "summary": "Discussed advanced Python patterns with team",
            "episode_type": "learning",
            "state": "active",
            "confidence": 0.6,
            "importance": 0.7,
            "primary_context": "work",
            "primary_project": "ayeneh",
            "primary_people": ["alice", "bob"],
            "major_decisions": ["Use async patterns"],
        })
        assert episode_id is not None

        # 2. Load and verify episode
        episodes = await repo.load_episodes(user, state="active")
        assert len(episodes) >= 1
        ep = episodes[0]
        assert ep["title"] == "Deep Python Discussion"
        assert ep["primary_people"] == ["alice", "bob"]

        # 3. Extract semantic knowledge from the episode
        semantic_id = await repo.save_semantic(user, {
            "knowledge_statement": "User has expertise in advanced Python patterns",
            "category": "skills",
            "confidence": 0.6,
            "importance": 0.7,
            "temporal_stability": "long_term",
            "supporting_episodes": [episode_id],
        })
        assert semantic_id is not None

        # 4. Consolidate the memory
        consolidation_id = await repo.save_consolidation(user, {
            "target_memory_id": semantic_id,
            "evidence_summary": "Episode discussion confirms Python expertise",
            "supporting_episodes": [episode_id],
            "confidence_before": 0.6,
            "confidence_after": 0.8,
            "decision": "promote",
            "consolidation_level": "emerging_pattern",
        })
        assert consolidation_id is not None

        # 5. Update episode state after consolidation
        success = await repo.update_episode(episode_id, {
            "state": "completed",
            "confidence": 0.8,
        })
        assert success is True

        # 6. Verify final state
        episodes = await repo.load_episodes(user, state="completed")
        assert len(episodes) >= 1

        consolidations = await repo.load_consolidations(user, decision="promote")
        assert len(consolidations) >= 1
        assert consolidations[0]["confidence_after"] == 0.8


# ---------------------------------------------------------------------------
# Working memory assembly with context switching
# ---------------------------------------------------------------------------

class TestWorkingMemoryAssembly:
    @pytest.mark.asyncio
    async def test_create_and_activate_working_items(self, repo: MEMRepository, user):
        # Create several working memory items
        w1 = await repo.save_working(user, {
            "source_memory_id": "ep-1",
            "activation_reason": "Current conversation topic",
            "activation_score": 0.9,
            "priority_score": 0.8,
            "temporal_relevance": 0.95,
            "estimated_lifetime_s": 300,
            "status": "active",
        })
        w2 = await repo.save_working(user, {
            "source_memory_id": "sem-1",
            "activation_reason": "Related semantic knowledge",
            "activation_score": 0.6,
            "priority_score": 0.5,
            "temporal_relevance": 0.7,
            "estimated_lifetime_s": 600,
            "status": "active",
        })
        w3 = await repo.save_working(user, {
            "source_memory_id": "ep-2",
            "activation_reason": "Historical context",
            "activation_score": 0.3,
            "priority_score": 0.2,
            "temporal_relevance": 0.4,
            "estimated_lifetime_s": 120,
            "status": "expired",
        })

        # Load active working memory
        active = await repo.load_working(user, status="active")
        assert len(active) >= 2

        # Simulate context switch - deactivate w1, activate new
        await repo.update_working(w1, {"status": "inactive"})
        w4 = await repo.save_working(user, {
            "source_memory_id": "ep-3",
            "activation_reason": "New topic detected",
            "activation_score": 0.95,
            "priority_score": 0.9,
            "temporal_relevance": 1.0,
            "estimated_lifetime_s": 300,
            "status": "active",
        })

        active_after = await repo.load_working(user, status="active")
        assert len(active_after) >= 2
        active_ids = [a["id"] for a in active_after]
        assert w4 in active_ids
        assert w1 not in active_ids


# ---------------------------------------------------------------------------
# Knowledge graph construction and traversal
# ---------------------------------------------------------------------------

class TestKnowledgeGraphConstruction:
    @pytest.mark.asyncio
    async def test_build_graph_and_query(self, repo: MEMRepository, user):
        # Create nodes
        n1 = await repo.save_kg_node(user, {
            "label": "Python",
            "category": "skills",
            "layer": "semantic",
            "confidence": 0.95,
        })
        n2 = await repo.save_kg_node(user, {
            "label": "Async Programming",
            "category": "concepts",
            "layer": "semantic",
            "confidence": 0.9,
        })
        n3 = await repo.save_kg_node(user, {
            "label": "Deep Learning",
            "category": "skills",
            "layer": "semantic",
            "confidence": 0.7,
        })

        # Create edges
        e1 = await repo.save_kg_edge(user, {
            "source_node_id": n1,
            "target_node_id": n2,
            "relationship": "contains",
            "weight": 0.9,
        })
        e2 = await repo.save_kg_edge(user, {
            "source_node_id": n1,
            "target_node_id": n3,
            "relationship": "associated_with",
            "weight": 0.5,
        })

        # Query graph
        nodes = await repo.load_kg_nodes(user)
        assert len(nodes) >= 3

        edges = await repo.load_kg_edges(user)
        assert len(edges) >= 2

        # Filter by category
        skills = await repo.load_kg_nodes(user, category="skills")
        assert len(skills) >= 2
        labels = [n["label"] for n in skills]
        assert "Python" in labels
        assert "Deep Learning" in labels

        # Get specific node
        node = await repo.get_kg_node(n1)
        assert node is not None
        assert node["label"] == "Python"


# ---------------------------------------------------------------------------
# Version creation and lineage tracking
# ---------------------------------------------------------------------------

class TestVersionLineage:
    @pytest.mark.asyncio
    async def test_version_chain(self, repo: MEMRepository, user):
        memory_id = f"mem-{uuid.uuid4().hex[:8]}"

        # Create version 1
        v1 = await repo.save_version(user, {
            "target_memory_id": memory_id,
            "version_number": 1,
            "revision_type": "expansion",
            "reason": "Initial creation",
            "confidence_before": 0.0,
            "confidence_after": 0.5,
        })

        # Create version 2
        v2 = await repo.save_version(user, {
            "target_memory_id": memory_id,
            "parent_version_id": v1,
            "version_number": 2,
            "revision_type": "correction",
            "reason": "Corrected confidence based on new evidence",
            "confidence_before": 0.5,
            "confidence_after": 0.8,
            "supporting_evidence": ["ev-1", "ev-2"],
        })

        # Create version 3
        await repo.save_version(user, {
            "target_memory_id": memory_id,
            "parent_version_id": v2,
            "version_number": 3,
            "revision_type": "refinement",
            "reason": "Refined after review",
            "confidence_before": 0.8,
            "confidence_after": 0.9,
        })

        # Load all versions for this memory
        versions = await repo.load_versions(user, memory_id=memory_id)
        assert len(versions) == 3
        assert versions[0]["version_number"] == 1
        assert versions[1]["version_number"] == 2
        assert versions[2]["version_number"] == 3

        # Verify version 2 has evidence
        assert versions[1]["supporting_evidence"] == ["ev-1", "ev-2"]

        # Verify chain
        assert versions[1]["parent_version_id"] == v1
        assert versions[2]["parent_version_id"] == v2


# ---------------------------------------------------------------------------
# Ranking with diversity preservation
# ---------------------------------------------------------------------------

class TestRankingDiversity:
    @pytest.mark.asyncio
    async def test_rank_across_task_profiles(self, repo: MEMRepository, user):
        memory_id = f"mem-{uuid.uuid4().hex[:8]}"

        # Rank for different task profiles
        profiles = ["Debugging", "SelfReflection", "Planning", "RealityCalibration"]
        for profile in profiles:
            await repo.save_ranking(user, {
                "target_memory_id": memory_id,
                "overall_score": 0.7,
                "relevance_score": 0.8,
                "importance_score": 0.6,
                "task_profile": profile,
                "explanation": f"Ranked for {profile}",
            })

        # Load rankings
        rankings = await repo.load_rankings(user, memory_id=memory_id)
        assert len(rankings) >= 4

        task_profiles = [r["task_profile"] for r in rankings]
        for p in profiles:
            assert p in task_profiles

        # Verify ranking for specific profile
        debugging = [r for r in rankings if r["task_profile"] == "Debugging"]
        assert len(debugging) >= 1
        assert debugging[0]["overall_score"] == 0.7


# ---------------------------------------------------------------------------
# Forgetting with compression and preservation
# ---------------------------------------------------------------------------

class TestForgettingWithPreservation:
    @pytest.mark.asyncio
    async def test_compression_and_tier_tracking(self, repo: MEMRepository, user):
        # Create forgetting records with different tiers
        f1 = await repo.save_forgetting(user, {
            "affected_memory_ids": ["mem-old-1", "mem-old-2"],
            "compression_strategy": "redundancy",
            "reason": "Redundant information detected",
            "knowledge_preserved": "Core fact retained",
            "information_reduced": 0.6,
            "recoverability_status": "recoverable",
            "tier": "dormant",
            "access_count": 3,
            "access_frequency_score": 0.3,
        })

        f2 = await repo.save_forgetting(user, {
            "affected_memory_ids": ["mem-archived-1"],
            "compression_strategy": "conversation",
            "reason": "Old conversation compressed",
            "knowledge_preserved": "Summary retained",
            "information_reduced": 0.8,
            "recoverability_status": "partial",
            "tier": "archived",
            "access_count": 1,
            "access_frequency_score": 0.1,
        })

        # Load by tier
        dormant = await repo.load_forgettings(user, tier="dormant")
        assert len(dormant) >= 1
        assert dormant[0]["recoverability_status"] == "recoverable"

        archived = await repo.load_forgettings(user, tier="archived")
        assert len(archived) >= 1
        assert archived[0]["information_reduced"] == 0.8

        # Verify affected memory IDs are preserved as JSON
        f1_detail = await repo.get_forgetting(f1)
        assert f1_detail is not None
        assert "mem-old-1" in f1_detail["affected_memory_ids"]
        assert "mem-old-2" in f1_detail["affected_memory_ids"]


# ---------------------------------------------------------------------------
# Cross-module: Episode → Semantic update → Version tracking
# ---------------------------------------------------------------------------

class TestCrossModuleIntegration:
    @pytest.mark.asyncio
    async def test_episode_update_creates_semantic_and_version(self, repo: MEMRepository, user):
        # 1. Create episode
        ep_id = await repo.save_episode(user, {
            "title": "Research Session",
            "episode_type": "research",
            "state": "active",
            "confidence": 0.5,
        })

        # 2. Create semantic knowledge derived from episode
        sem_id = await repo.save_semantic(user, {
            "knowledge_statement": "User is researching memory systems",
            "category": "research_domains",
            "confidence": 0.5,
            "supporting_episodes": [ep_id],
        })

        # 3. Update semantic after episode completion
        await repo.update_semantic(sem_id, {
            "confidence": 0.8,
            "lifecycle_state": "validated",
        })

        # 4. Record version
        await repo.save_version(user, {
            "target_memory_id": sem_id,
            "version_number": 1,
            "revision_type": "confidence_update",
            "reason": "Episode confirmed research interest",
            "confidence_before": 0.5,
            "confidence_after": 0.8,
        })

        # 5. Complete episode
        await repo.update_episode(ep_id, {"state": "completed", "confidence": 0.9})

        # Verify everything persisted correctly
        episodes = await repo.load_episodes(user, state="completed")
        assert any(e["id"] == ep_id for e in episodes)

        semantics = await repo.load_semantics(user, category="research_domains")
        validated = [s for s in semantics if s["lifecycle_state"] == "validated"]
        assert len(validated) >= 1

        versions = await repo.load_versions(user, memory_id=sem_id)
        assert len(versions) >= 1
        assert versions[0]["revision_type"] == "confidence_update"


# ---------------------------------------------------------------------------
# Retrieval scoring
# ---------------------------------------------------------------------------

class TestRetrievalScoring:
    @pytest.mark.asyncio
    async def test_retrieval_with_scores(self, repo: MEMRepository, user):
        # Create retrieval records with different scores
        request_id = f"req-{uuid.uuid4().hex[:8]}"

        for i in range(5):
            await repo.save_retrieval(user, {
                "request_id": request_id,
                "memory_id": f"mem-{i}",
                "memory_type": "episodic" if i % 2 == 0 else "semantic",
                "relevance_score": 0.9 - i * 0.1,
                "final_score": 0.9 - i * 0.1,
                "strategy_used": "composite",
            })

        # Load retrievals
        retrievals = await repo.load_retrievals(user, request_id=request_id)
        assert len(retrievals) == 5

        # Verify sorted by final_score descending
        scores = [r["final_score"] for r in retrievals]
        assert scores == sorted(scores, reverse=True)

        # Filter by type
        episodic = [r for r in retrievals if r["memory_type"] == "episodic"]
        assert len(episodic) == 3  # indices 0, 2, 4


# ---------------------------------------------------------------------------
# Orchestrator full pipeline (no DB)
# ---------------------------------------------------------------------------

class TestOrchestratorPipeline:
    def test_process_returns_all_stage_results(self):
        """The orchestrator should return results for every engine stage."""
        from ayeneh.memo.pipeline.orchestrator import MEMOPipelineOrchestrator

        orchestrator = MEMOPipelineOrchestrator()
        messages = [
            {'role': 'user', 'content': 'I learned about Python async patterns today'},
            {'role': 'assistant', 'content': 'Great! Async programming is very useful'},
            {'role': 'user', 'content': 'I also realized how decorators work'},
        ]

        results = orchestrator.process('test_user', messages)

        # Should contain results for every stage
        expected_keys = [
            'episodic', 'semantic', 'working', 'consolidation',
            'retrieval', 'ranking', 'forgetting', 'knowledge_graph',
            'versioning', 'timings', 'pipeline_metadata',
        ]
        for key in expected_keys:
            assert key in results, f"Missing key: {key}"

        # Timing should be recorded
        assert isinstance(results['timings'], dict)
        assert len(results['timings']) >= 5  # at least 5 stages timed

        # Metadata should have counts
        meta = results['pipeline_metadata']
        assert meta['user_id'] == 'test_user'
        assert meta['message_count'] == 3

    def test_process_with_empty_messages(self):
        """Pipeline should handle empty message list gracefully."""
        from ayeneh.memo.pipeline.orchestrator import MEMOPipelineOrchestrator

        orchestrator = MEMOPipelineOrchestrator()
        results = orchestrator.process('test_user', [])

        assert 'episodic' in results
        assert 'pipeline_metadata' in results
        assert results['pipeline_metadata']['message_count'] == 0

    def test_process_with_context(self):
        """Pipeline should accept and pass through context."""
        from ayeneh.memo.pipeline.orchestrator import MEMOPipelineOrchestrator

        orchestrator = MEMOPipelineOrchestrator()
        messages = [
            {'role': 'user', 'content': 'What are my goals for this project?'},
        ]
        context = {'intent': 'recall', 'projects': ['ayeneh']}

        results = orchestrator.process('test_user', messages, context)
        assert 'pipeline_metadata' in results


# ---------------------------------------------------------------------------
# Multi-hop graph traversal
# ---------------------------------------------------------------------------

class TestMultiHopTraversal:
    def test_traverse_graph_bfs(self):
        """traverse_graph should return nodes reachable within max_hops."""
        from ayeneh.memo.retrieval.adaptive import MultiHopRetriever

        retriever = MultiHopRetriever(max_hops=3)
        graph = {
            'A': ['B', 'C'],
            'B': ['D'],
            'C': ['E'],
            'D': ['F'],
            'E': [],
            'F': [],
        }

        result = retriever.traverse_graph('A', graph, max_hops=2)
        assert 'A' in result
        assert 'B' in result
        assert 'C' in result
        assert 'D' in result
        assert 'E' in result
        # F is 3 hops away, should NOT be included at max_hops=2
        assert 'F' not in result

    def test_traverse_graph_with_object(self):
        """traverse_graph should work with objects that have a neighbors method."""
        from ayeneh.memo.retrieval.adaptive import MultiHopRetriever

        class MockGraphNode:
            def __init__(self, nid):
                self.node_id = nid

        class MockGraph:
            def __init__(self, adj):
                self._adj = adj
            def neighbors(self, node_id):
                return [MockGraphNode(nid) for nid in self._adj.get(node_id, [])]

        graph = MockGraph({'X': ['Y'], 'Y': ['Z'], 'Z': []})
        retriever = MultiHopRetriever()
        result = retriever.traverse_graph('X', graph, max_hops=2)
        assert result == ['X', 'Y', 'Z']


# ---------------------------------------------------------------------------
# Forgetting eviction
# ---------------------------------------------------------------------------

class TestForgettingEviction:
    def test_evict_dormant_memories(self):
        """evict should identify memories with dormant/archived lifecycle states."""
        from ayeneh.memo.forgetting.engine import ForgettingEngine
        from ayeneh.memo.base import MemoryObject
        from datetime import UTC, datetime

        engine = ForgettingEngine()
        now = datetime.now(UTC)

        mem_active = MemoryObject(
            identifier='mem_active',
            memory_type='semantic',
            creation_time=now,
            confidence=0.8,
            importance_score=0.7,
            lifecycle_status='consolidated_memory',
            last_updated=now,
        )
        mem_dormant = MemoryObject(
            identifier='mem_dormant',
            memory_type='semantic',
            creation_time=now,
            confidence=0.3,
            importance_score=0.2,
            lifecycle_status='dormant',
            last_updated=now,
        )
        mem_archived = MemoryObject(
            identifier='mem_archived',
            memory_type='semantic',
            creation_time=now,
            confidence=0.1,
            importance_score=0.1,
            lifecycle_status='archived',
            last_updated=now,
        )

        evicted = engine.evict('user1', [mem_active, mem_dormant, mem_archived])
        assert 'mem_active' not in evicted
        assert 'mem_dormant' in evicted
        assert 'mem_archived' in evicted

    def test_evict_empty_list(self):
        """evict should handle empty memory list."""
        from ayeneh.memo.forgetting.engine import ForgettingEngine

        engine = ForgettingEngine()
        evicted = engine.evict('user1', [])
        assert evicted == []


# ---------------------------------------------------------------------------
# Working memory compression grouping
# ---------------------------------------------------------------------------

class TestWorkingMemoryCompressGroup:
    def test_compress_group_by_source(self):
        """compress_group should group items by source_memory."""
        from ayeneh.memo.working.compression import WorkingMemoryCompressor
        from ayeneh.memo.working.types import WorkingMemoryObject

        compressor = WorkingMemoryCompressor()
        items = [
            WorkingMemoryObject(identifier='wm1', source_memory='episodic_memory', activation_reason='r1'),
            WorkingMemoryObject(identifier='wm2', source_memory='episodic_memory', activation_reason='r2'),
            WorkingMemoryObject(identifier='wm3', source_memory='semantic_personal_memory', activation_reason='r3'),
        ]

        result = compressor.compress_group(items)
        assert result['original_count'] == 3
        assert result['compressed_count'] == 2  # episodic group + semantic individual
        assert result['compressed_count'] < result['original_count']

        # The episodic group should be compressed
        grouped = result['grouped']
        compressed_groups = [g for g in grouped if isinstance(g, dict) and g.get('compressed')]
        assert len(compressed_groups) == 1
        assert compressed_groups[0]['source_type'] == 'episodic_memory'
        assert compressed_groups[0]['item_count'] == 2

    def test_compress_group_empty(self):
        """compress_group should handle empty list."""
        from ayeneh.memo.working.compression import WorkingMemoryCompressor

        compressor = WorkingMemoryCompressor()
        result = compressor.compress_group([])
        assert result == {'grouped': [], 'original_count': 0, 'compressed_count': 0}


# ---------------------------------------------------------------------------
# Snapshot capture
# ---------------------------------------------------------------------------

class TestSnapshotCapture:
    def test_capture_snapshot_counts(self):
        """capture_snapshot should count active vs dormant memories."""
        from ayeneh.memo.versioning.snapshot import SnapshotStore
        from ayeneh.memo.base import MemoryObject
        from datetime import UTC, datetime

        store = SnapshotStore()
        now = datetime.now(UTC)

        memories = [
            MemoryObject(
                identifier='m1', memory_type='semantic', creation_time=now,
                confidence=0.9, importance_score=0.8,
                lifecycle_status='consolidated_memory', last_updated=now,
            ),
            MemoryObject(
                identifier='m2', memory_type='semantic', creation_time=now,
                confidence=0.3, importance_score=0.2,
                lifecycle_status='dormant', last_updated=now,
            ),
            MemoryObject(
                identifier='m3', memory_type='semantic', creation_time=now,
                confidence=0.5, importance_score=0.5,
                lifecycle_status='longitudinal_memory', last_updated=now,
            ),
        ]

        result = store.capture_snapshot('user1', memories, beliefs=['b1'], narratives=['n1'])
        assert result['user_id'] == 'user1'
        assert result['memories'] == 3
        assert result['active_memories'] == 2  # consolidated + longitudinal
        assert result['dormant_memories'] == 1
        assert result['beliefs'] == 1
        assert result['narratives'] == 1
        assert 'timestamp' in result

        # Snapshot should be stored
        assert len(store.list_snapshots()) >= 1
