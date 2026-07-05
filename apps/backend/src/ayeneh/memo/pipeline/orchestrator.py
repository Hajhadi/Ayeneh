"""MEMO memory pipeline orchestrator.

Wires all 9 MEM engines (MEM-02 through MEM-10) into a single
pipeline that passes outputs between engines in dependency order
and persists intermediate results via MEMRepository.
"""

from __future__ import annotations

import time

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.types import Observation

logger = structlog.get_logger(__name__)


class MEMOPipelineOrchestrator:
    """Orchestrates the MEMO memory pipeline across all 9 engines.

    Runs engines in dependency order:
      Episodic → Semantic → Working → Consolidation → Retrieval
      → Ranking → Forgetting → KnowledgeGraph → Versioning

    Persists intermediate results to MEMRepository when provided.
    """

    def __init__(self, repository: Any = None, ai_router: Any = None) -> None:
        self._repo = repository
        self._ai_router = ai_router
        self._engines: dict[str, Any] = {}
        self._init_engines()

    def _init_engines(self) -> None:
        from ayeneh.memo.episodic.engine import EpisodicMemoryEngine
        from ayeneh.memo.semantic.engine import SemanticMemoryEngine
        from ayeneh.memo.working.engine import WorkingMemoryEngine
        from ayeneh.memo.consolidation.engine import ConsolidationEngine
        from ayeneh.memo.retrieval.engine import RetrievalEngine
        from ayeneh.memo.ranking.engine import RankingEngine
        from ayeneh.memo.forgetting.engine import ForgettingEngine
        from ayeneh.memo.knowledge_graph.graph import KnowledgeGraph
        from ayeneh.memo.versioning.engine import VersioningEngine

        self._engines = {
            'episodic': EpisodicMemoryEngine(),
            'semantic': SemanticMemoryEngine(),
            'working': WorkingMemoryEngine(),
            'consolidation': ConsolidationEngine(),
            'retrieval': RetrievalEngine(),
            'ranking': RankingEngine(),
            'forgetting': ForgettingEngine(),
            'knowledge_graph': KnowledgeGraph(),
            'versioning': VersioningEngine(),
        }

    def _get_engine(self, module: str) -> Any:
        if module not in self._engines:
            self._engines[module] = self._create_engine(module)
        return self._engines[module]

    @staticmethod
    def _create_engine(module: str) -> Any:
        if module == "episodic":
            from ayeneh.memo.episodic.engine import EpisodicMemoryEngine
            return EpisodicMemoryEngine()
        if module == "semantic":
            from ayeneh.memo.semantic.engine import SemanticMemoryEngine
            return SemanticMemoryEngine()
        if module == "working":
            from ayeneh.memo.working.engine import WorkingMemoryEngine
            return WorkingMemoryEngine()
        if module == "consolidation":
            from ayeneh.memo.consolidation.engine import ConsolidationEngine
            return ConsolidationEngine()
        if module == "retrieval":
            from ayeneh.memo.retrieval.engine import RetrievalEngine
            return RetrievalEngine()
        if module == "ranking":
            from ayeneh.memo.ranking.engine import RankingEngine
            return RankingEngine()
        if module == "forgetting":
            from ayeneh.memo.forgetting.engine import ForgettingEngine
            return ForgettingEngine()
        if module == "knowledge_graph":
            from ayeneh.memo.knowledge_graph.graph import KnowledgeGraph
            return KnowledgeGraph()
        if module == "versioning":
            from ayeneh.memo.versioning.engine import VersioningEngine
            return VersioningEngine()
        return None

    def process(self, user_id: str, messages: list[dict[str, Any]], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run the full MEMO pipeline.

        Args:
            user_id: The user whose memory is being processed.
            messages: Conversation messages as list of dicts with keys
                      'role', 'content', and optional 'timestamp'.
            context: Optional extra context (goals, projects, etc.).

        Returns:
            dict with results keyed by engine name, plus 'timings' and 'pipeline_metadata'.
        """
        timings: dict[str, float] = {}
        results: dict[str, Any] = {}
        ctx = context or {}

        # Convert messages to Observations
        observations = self._messages_to_observations(messages)
        conversation_text = ' '.join(m.get('content', '') for m in messages)

        # --- MEM-02: Episodic Memory ---
        t0 = time.monotonic()
        episodic_engine = self._engines['episodic']
        episodic_result = episodic_engine.run_pipeline(observations)
        timings['episodic'] = time.monotonic() - t0
        results['episodic'] = {
            'episodes': episodic_result.episodes,
            'milestones': episodic_result.milestones,
            'boundaries': episodic_result.boundaries,
            'emotional_landscapes': episodic_result.emotional_landscapes,
        }

        # Persist episodes
        if self._repo:
            for ep in episodic_result.episodes:
                _safe_coro(self._repo.save_episode(user_id, {
                    'title': ep.title,
                    'summary': ep.summary,
                    'episode_type': ep.category,
                    'state': ep.state,
                    'confidence': ep.confidence,
                    'primary_context': ep.primary_context,
                }))

        episode_ids = tuple(ep.identifier for ep in episodic_result.episodes)

        # --- MEM-03: Semantic Memory ---
        t0 = time.monotonic()
        semantic_engine = self._engines['semantic']
        semantic_result = semantic_engine.run_pipeline(
            observations,
            episode_ids=episode_ids,
        )
        timings['semantic'] = time.monotonic() - t0
        results['semantic'] = {
            'semantic_objects': semantic_result.semantic_objects,
            'knowledge_nodes': semantic_result.knowledge_nodes,
            'knowledge_edges': semantic_result.knowledge_edges,
        }

        # Persist semantic memories
        if self._repo:
            for sem in semantic_result.semantic_objects:
                _safe_coro(self._repo.save_semantic(user_id, {
                    'knowledge_statement': sem.knowledge_statement,
                    'category': sem.knowledge_category,
                    'confidence': sem.confidence,
                    'importance': sem.importance,
                    'temporal_stability': sem.temporal_stability,
                    'supporting_episodes': list(sem.supporting_episodes),
                }))

        # --- MEM-04: Working Memory ---
        t0 = time.monotonic()
        working_engine = self._engines['working']
        # Build retrieved_memories dicts from episodic + semantic results
        retrieved_memories = _build_retrieved_memories(
            episodic_result.episodes, semantic_result.semantic_objects
        )
        recent_conversation = [m.get('content', '') for m in messages[-5:]]
        working_result = working_engine.run_pipeline(
            conversation_text,
            intent=ctx.get('intent', 'recall'),
            cognitive_focus=ctx.get('cognitive_focus', ''),
            retrieved_memories=retrieved_memories,
            recent_conversation=recent_conversation,
        )
        timings['working'] = time.monotonic() - t0
        results['working'] = {
            'activated_objects': working_result.activated_objects,
            'deactivated_objects': working_result.deactivated_objects,
            'context_switches': working_result.context_switches,
            'open_loops': working_result.open_loops,
            'snapshot': working_result.snapshot,
        }

        # Persist working memory items
        if self._repo:
            for wm_obj in working_result.activated_objects:
                _safe_coro(self._repo.save_working(user_id, {
                    'source_memory_id': wm_obj.source_memory,
                    'activation_reason': wm_obj.activation_reason,
                    'activation_score': wm_obj.activation_score,
                    'priority_score': wm_obj.priority_score,
                    'temporal_relevance': wm_obj.temporal_relevance,
                    'estimated_lifetime_s': wm_obj.estimated_lifetime,
                    'status': 'active',
                }))

        # --- MEM-05: Consolidation ---
        t0 = time.monotonic()
        consolidation_engine = self._engines['consolidation']
        wm_items_for_consolidation = _wm_objects_to_dicts(working_result.activated_objects)
        episode_dicts = [ep_to_dict(ep) for ep in episodic_result.episodes]
        consolidation_result = consolidation_engine.run_pipeline(
            wm_items_for_consolidation,
            episodes=episode_dicts,
        )
        timings['consolidation'] = time.monotonic() - t0
        results['consolidation'] = {
            'processed_count': consolidation_result.processed_count,
            'promoted_count': consolidation_result.promoted_count,
            'rejected_count': consolidation_result.rejected_count,
            'deferred_count': consolidation_result.deferred_count,
            'consolidated_objects': consolidation_result.consolidated_objects,
        }

        # Persist consolidation decisions
        if self._repo:
            for cons in consolidation_result.consolidated_objects:
                _safe_coro(self._repo.save_consolidation(user_id, {
                    'target_memory_id': cons.target_memory,
                    'evidence_summary': cons.evidence_summary,
                    'confidence_before': cons.confidence_before,
                    'confidence_after': cons.confidence_after,
                    'decision': 'promote' if cons.is_promoted else ('reject' if cons.is_rejected else 'defer'),
                }))

        # --- MEM-06: Retrieval ---
        t0 = time.monotonic()
        retrieval_engine = self._engines['retrieval']
        semantic_dicts = [sem_to_dict(s) for s in semantic_result.semantic_objects]
        episodic_dicts = [ep_to_dict(e) for e in episodic_result.episodes]
        retrieval_result = retrieval_engine.retrieve(
            conversation_text,
            intent=ctx.get('intent', 'recall'),
            semantic_memories=semantic_dicts,
            episodic_memories=episodic_dicts,
        )
        timings['retrieval'] = time.monotonic() - t0
        results['retrieval'] = {
            'request_id': retrieval_result.request_id,
            'retrieved_items': retrieval_result.retrieved_items,
            'strategy_used': retrieval_result.strategy_used,
            'total_candidates_evaluated': retrieval_result.total_candidates_evaluated,
        }

        # --- MEM-07: Ranking ---
        t0 = time.monotonic()
        ranking_engine = self._engines['ranking']
        # Ranking needs MemoryObject instances; use semantic objects as proxies
        # The ranking engine operates on MemoryObject which has the common interface
        ranking_input = list(semantic_result.semantic_objects)
        ranking_result = ranking_engine.rank(ranking_input)
        timings['ranking'] = time.monotonic() - t0
        results['ranking'] = {
            'selected_memories': ranking_result.selected_memories,
            'capacity_used': ranking_result.capacity_used,
            'capacity_max': ranking_result.capacity_max,
        }

        # Persist rankings
        if self._repo:
            for rank_obj in ranking_result.rankings:
                _safe_coro(self._repo.save_ranking(user_id, {
                    'target_memory_id': rank_obj.target_memory,
                    'overall_score': rank_obj.overall_score,
                    'relevance_score': rank_obj.relevance_score,
                    'importance_score': rank_obj.importance_score,
                    'explanation': rank_obj.ranking_explanation,
                }))

        # --- MEM-08: Forgetting ---
        t0 = time.monotonic()
        forgetting_engine = self._engines['forgetting']
        forgetting_result = forgetting_engine.run(list(semantic_result.semantic_objects))
        timings['forgetting'] = time.monotonic() - t0
        results['forgetting'] = {
            'memories_affected': forgetting_result.memories_affected,
            'information_reduced': forgetting_result.information_reduced,
            'recoverable': forgetting_result.recoverable,
        }

        # Persist forgetting results
        if self._repo:
            for comp in forgetting_result.compressions_applied:
                _safe_coro(self._repo.save_forgetting(user_id, {
                    'affected_memory_ids': list(comp.affected_memory_objects),
                    'compression_strategy': comp.compression_strategy.value if hasattr(comp.compression_strategy, 'value') else str(comp.compression_strategy),
                    'reason': comp.reason,
                    'knowledge_preserved': comp.knowledge_preserved,
                    'information_reduced': comp.information_reduced,
                    'recoverability_status': comp.recoverability_status,
                }))

        # --- MEM-09: Knowledge Graph (integrate edges from semantic) ---
        t0 = time.monotonic()
        kg = self._engines['knowledge_graph']
        # Add semantic nodes and edges to the graph
        for node in semantic_result.knowledge_nodes:
            from ayeneh.memo.knowledge_graph.types import GraphNode, NodeCategory, GraphLayer
            graph_node = GraphNode(
                node_id=node.node_id,
                label=node.label,
                category=NodeCategory.SEMANTIC_MEMORIES if node.category in ('skills', 'expertise', 'personal_interests') else NodeCategory.CONCEPTS,
                layer=GraphLayer.SEMANTIC,
            )
            kg.add_node(graph_node)

        from ayeneh.memo.knowledge_graph.types import GraphEdge as KGEdge, RelationshipCategory
        for edge in semantic_result.knowledge_edges:
            graph_edge = KGEdge(
                edge_id=f'edge_{edge.source_node_id}_{edge.target_node_id}',
                source_node=edge.source_node_id,
                target_node=edge.target_node_id,
                relationship=RelationshipCategory.RELATED_TO,
                weight=edge.weight,
            )
            kg.add_edge(graph_edge)

        timings['knowledge_graph'] = time.monotonic() - t0
        results['knowledge_graph'] = {
            'node_count': kg.node_count,
            'edge_count': kg.edge_count,
            'version': kg.version,
        }

        # --- MEM-10: Versioning ---
        t0 = time.monotonic()
        versioning_engine = self._engines['versioning']
        versioning_result = versioning_engine.create_snapshot(
            active_projects=ctx.get('projects', ()),
            identity_state=ctx.get('identity_state'),
            belief_state=ctx.get('belief_state'),
        )
        timings['versioning'] = time.monotonic() - t0
        results['versioning'] = {
            'snapshot_id': versioning_result.snapshot_id,
            'memory_versions': versioning_result.memory_versions,
            'knowledge_graph_version': versioning_result.knowledge_graph_version,
        }

        results['timings'] = timings
        results['pipeline_metadata'] = {
            'user_id': user_id,
            'message_count': len(messages),
            'episode_count': len(episodic_result.episodes),
            'semantic_count': len(semantic_result.semantic_objects),
            'working_memory_count': len(working_result.activated_objects),
            'retrieval_count': len(retrieval_result.retrieved_items),
            'ranking_selected': len(ranking_result.selected_memories),
            'total_time_ms': sum(timings.values()) * 1000,
        }

        return results

    def _extract_evidence(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract evidence from conversation messages."""
        evidence = []
        for msg in messages:
            evidence.append({
                'text': msg.get('content', ''),
                'speaker': msg.get('role', 'user'),
                'timestamp': msg.get('timestamp', ''),
                'type': 'conversation',
            })
        return evidence

    def _messages_to_observations(self, messages: list[dict[str, Any]]) -> list[Observation]:
        """Convert raw messages to Observation objects for the episodic/semantic engines."""
        observations = []
        now = datetime.now(UTC)
        for i, msg in enumerate(messages):
            obs = Observation(
                observation_id=f"obs_{i}",
                content=msg.get('content', ''),
                source=msg.get('role', 'user'),
                timestamp=now,
                observation_type='conversation_turn',
                metadata={'role': msg.get('role', 'user')},
            )
            observations.append(obs)
        return observations


# ---------------------------------------------------------------------------
# Helpers for data conversion between engines
# ---------------------------------------------------------------------------


def _build_retrieved_memories(
    episodes: tuple,
    semantic_objects: tuple,
) -> list[dict[str, Any]]:
    """Build a list of memory dicts suitable for WorkingMemoryEngine input."""
    memories = []
    for ep in episodes:
        memories.append({
            'id': ep.identifier,
            'source': 'episodic_memory',
            'content': ep.summary,
            'reason': 'episode_context',
            'score': ep.confidence,
            'priority': ep.confidence * 0.8,
            'evidence': list(ep.supporting_evidence),
        })
    for sem in semantic_objects:
        memories.append({
            'id': sem.identifier,
            'source': 'semantic_personal_memory',
            'content': sem.knowledge_statement,
            'reason': 'semantic_context',
            'score': sem.confidence,
            'priority': sem.importance,
            'evidence': list(sem.supporting_evidence),
        })
    return memories


def _wm_objects_to_dicts(wm_objects: tuple) -> list[dict[str, Any]]:
    """Convert WorkingMemoryObject instances to dicts for ConsolidationEngine."""
    items = []
    for obj in wm_objects:
        items.append({
            'id': obj.identifier,
            'source_memory': obj.source_memory,
            'activation_score': obj.activation_score,
            'priority_score': obj.priority_score,
            'evidence': list(obj.supporting_evidence),
            'supporting_episodes': [obj.associated_episode] if obj.associated_episode else [],
        })
    return items


def ep_to_dict(ep: Any) -> dict[str, Any]:
    """Convert an EpisodeObject to a dict."""
    return {
        'id': ep.identifier,
        'title': ep.title,
        'summary': ep.summary,
        'category': ep.category,
        'confidence': ep.confidence,
        'state': ep.state,
        'primary_context': ep.primary_context,
    }


def sem_to_dict(sem: Any) -> dict[str, Any]:
    """Convert a SemanticMemoryObject to a dict."""
    return {
        'id': sem.identifier,
        'content': sem.knowledge_statement,
        'category': sem.knowledge_category,
        'confidence': sem.confidence,
        'importance': sem.importance,
    }


def _safe_coro(coro: Any) -> None:
    """Run an async coroutine synchronously if needed, or skip on failure."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        # Already in an event loop — schedule as a task (best-effort)
        loop.create_task(coro)
    except RuntimeError:
        # No running loop — safe to run sync
        try:
            asyncio.run(coro)
        except Exception:
            pass
