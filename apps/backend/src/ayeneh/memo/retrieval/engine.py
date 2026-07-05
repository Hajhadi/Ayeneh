"""Retrieval engine (MEM-06).

Ten-phase pipeline:
1. UserInput
2. IntentDetection
3. ContextUnderstanding
4. WorkingMemoryAnalysis
5. SemanticRetrieval
6. EpisodeRetrieval
7. GraphExpansion
8. EvidenceValidation
9. Ranking
10. WorkingMemoryAssembly
"""

from __future__ import annotations

import uuid

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.retrieval.types import (
    DETECTED_INTENTS,
    RETRIEVAL_STRATEGIES,
    RankingWeights,
    RetrievedItem,
    RetrievalRequest,
    RetrievalResult,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MAX_RETRIEVAL_SIZE: int = 20
DEFAULT_CONFIDENCE_THRESHOLD: float = 0.3
DEFAULT_RANKING_WEIGHTS = RankingWeights()


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------


class RetrievalPipelineResult:
    """Result of running the retrieval pipeline."""

    __slots__ = (
        'result',
        'metadata',
    )

    def __init__(self) -> None:
        self.result: RetrievalResult | None = None
        self.metadata: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class RetrievalEngine:
    """Ten-phase retrieval pipeline.

    Processes user input through intent detection, context understanding,
    semantic/episode retrieval, graph expansion, evidence validation,
    ranking, and assembly into working memory.
    """

    def __init__(
        self,
        max_retrieval_size: int = DEFAULT_MAX_RETRIEVAL_SIZE,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        ranking_weights: RankingWeights | None = None,
        ai_router: Any = None,
    ) -> None:
        self._max_size = max_retrieval_size
        self._confidence_threshold = confidence_threshold
        self._weights = ranking_weights or DEFAULT_RANKING_WEIGHTS
        self._ai_router = ai_router
        self._semantic_store: dict[str, dict[str, Any]] = {}
        self._episode_store: dict[str, dict[str, Any]] = {}
        self._knowledge_graph: dict[str, list[str]] = {}
        self._retrieval_history: list[RetrievalResult] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_pipeline(
        self,
        request: RetrievalRequest,
        *,
        semantic_memories: list[dict[str, Any]] | None = None,
        episodic_memories: list[dict[str, Any]] | None = None,
        knowledge_graph: dict[str, list[str]] | None = None,
    ) -> RetrievalPipelineResult:
        """Run the full 10-phase retrieval pipeline."""
        pipeline_result = RetrievalPipelineResult()

        # Phase 1: UserInput — captured as request.conversation_context

        # Phase 2: IntentDetection
        detected_intent = self._detect_intent(request)
        logger.debug('phase_2_intent_detected', intent=detected_intent)

        # Phase 3: ContextUnderstanding
        context = self._understand_context(request, detected_intent)
        logger.debug('phase_3_context_understood', context_keys=list(context.keys()))

        # Phase 4: WorkingMemoryAnalysis
        wm_analysis = self._analyze_working_memory(request)
        logger.debug('phase_4_wm_analyzed', items=wm_analysis.get('active_count', 0))

        # Phase 5: SemanticRetrieval
        semantic_results = self._semantic_retrieve(
            request, semantic_memories or []
        )
        logger.debug('phase_5_semantic_retrieved', count=len(semantic_results))

        # Phase 6: EpisodeRetrieval
        episode_results = self._episode_retrieve(
            request, episodic_memories or []
        )
        logger.debug('phase_6_episode_retrieved', count=len(episode_results))

        # Phase 7: GraphExpansion
        graph_results = self._graph_expand(
            semantic_results + episode_results,
            knowledge_graph or {},
        )
        logger.debug('phase_7_graph_expanded', count=len(graph_results))

        # Phase 8: EvidenceValidation
        validated = self._validate_evidence(
            semantic_results + episode_results + graph_results
        )
        logger.debug('phase_8_evidence_validated', count=len(validated))

        # Phase 9: Ranking
        ranked = self._rank(validated, request)
        logger.debug('phase_9_ranked', count=len(ranked))

        # Phase 10: WorkingMemoryAssembly
        assembled = self._assemble(ranked, request)
        logger.debug('phase_10_assembled', count=len(assembled))

        result = RetrievalResult(
            request_id=request.request_identifier,
            retrieved_items=tuple(assembled),
            strategy_used=request.ranking_strategy,
            total_candidates_evaluated=len(semantic_results) + len(episode_results) + len(graph_results),
        )

        pipeline_result.result = result
        self._retrieval_history.append(result)

        return pipeline_result

    def retrieve(
        self,
        query: str,
        *,
        intent: str = 'recall',
        max_results: int | None = None,
        strategy: str = 'composite',
        semantic_memories: list[dict[str, Any]] | None = None,
        episodic_memories: list[dict[str, Any]] | None = None,
    ) -> RetrievalResult:
        """Convenience method for simple retrieval."""
        request = RetrievalRequest(
            request_identifier=f"req_{uuid.uuid4().hex[:12]}",
            conversation_context=query,
            detected_intent=intent,
            maximum_retrieval_size=max_results or self._max_size,
            ranking_strategy=strategy,
        )

        pipeline_result = self.run_pipeline(
            request,
            semantic_memories=semantic_memories,
            episodic_memories=episodic_memories,
        )

        return pipeline_result.result or RetrievalResult(request_id=request.request_identifier)

    def get_retrieval_history(self) -> list[RetrievalResult]:
        """Return the retrieval history."""
        return list(self._retrieval_history)

    # ------------------------------------------------------------------
    # Phase 2: IntentDetection
    # ------------------------------------------------------------------

    def _detect_intent(self, request: RetrievalRequest) -> str:
        """Detect the intent from the request."""
        if request.detected_intent and request.detected_intent != 'recall':
            return request.detected_intent

        context = request.conversation_context.lower()
        if any(kw in context for kw in ('why', 'explain')):
            return 'explain'
        if any(kw in context for kw in ('compare', 'difference')):
            return 'compare'
        if any(kw in context for kw in ('plan', 'should')):
            return 'plan'
        if any(kw in context for kw in ('reflect', 'think')):
            return 'reflect'
        return 'recall'

    # ------------------------------------------------------------------
    # Phase 3: ContextUnderstanding
    # ------------------------------------------------------------------

    def _understand_context(
        self,
        request: RetrievalRequest,
        intent: str,
    ) -> dict[str, Any]:
        """Understand the context of the retrieval request."""
        return {
            'intent': intent,
            'has_focus': request.has_focus,
            'focus': request.current_cognitive_focus,
            'project_count': len(request.relevant_projects),
            'episode_count': len(request.relevant_episodes),
            'cognitive_object_count': len(request.relevant_cognitive_objects),
        }

    # ------------------------------------------------------------------
    # Phase 4: WorkingMemoryAnalysis
    # ------------------------------------------------------------------

    def _analyze_working_memory(self, request: RetrievalRequest) -> dict[str, Any]:
        """Analyze current working memory state."""
        return {
            'active_count': len(request.relevant_cognitive_objects) + len(
                request.relevant_projects
            ),
            'focus': request.current_cognitive_focus,
        }

    # ------------------------------------------------------------------
    # Phase 5: SemanticRetrieval
    # ------------------------------------------------------------------

    def _semantic_retrieve(
        self,
        request: RetrievalRequest,
        semantic_memories: list[dict[str, Any]],
    ) -> list[RetrievedItem]:
        """Retrieve semantically relevant memories."""
        items: list[RetrievedItem] = []
        query_words = set(request.conversation_context.lower().split())

        for mem in semantic_memories:
            content = mem.get('content', '').lower()
            content_words = set(content.split())

            # Simple word overlap scoring
            overlap = len(query_words & content_words)
            total = len(query_words | content_words)
            relevance = overlap / total if total > 0 else 0.0

            if relevance >= self._confidence_threshold * 0.5:
                item = RetrievedItem(
                    memory_id=mem.get('id', f"sem_{uuid.uuid4().hex[:8]}"),
                    memory_type='semantic_personal',
                    content=mem.get('content', ''),
                    relevance_score=relevance,
                    confidence_score=mem.get('confidence', 0.5),
                    final_score=relevance * 0.6 + mem.get('confidence', 0.5) * 0.4,
                )
                items.append(item)

        return items

    # ------------------------------------------------------------------
    # Phase 6: EpisodeRetrieval
    # ------------------------------------------------------------------

    def _episode_retrieve(
        self,
        request: RetrievalRequest,
        episodic_memories: list[dict[str, Any]],
    ) -> list[RetrievedItem]:
        """Retrieve relevant episodes."""
        items: list[RetrievedItem] = []
        query_words = set(request.conversation_context.lower().split())

        for mem in episodic_memories:
            summary = mem.get('summary', '').lower()
            summary_words = set(summary.split())

            overlap = len(query_words & summary_words)
            total = len(query_words | summary_words)
            relevance = overlap / total if total > 0 else 0.0

            # Boost for explicitly relevant episodes
            if mem.get('id', '') in request.relevant_episodes:
                relevance = min(1.0, relevance + 0.3)

            if relevance >= self._confidence_threshold * 0.5:
                item = RetrievedItem(
                    memory_id=mem.get('id', f"ep_{uuid.uuid4().hex[:8]}"),
                    memory_type='episodic',
                    content=mem.get('summary', ''),
                    relevance_score=relevance,
                    confidence_score=mem.get('confidence', 0.5),
                    importance_score=mem.get('importance', 0.5),
                    final_score=relevance * 0.5 + mem.get('confidence', 0.5) * 0.3 + mem.get('importance', 0.5) * 0.2,
                )
                items.append(item)

        return items

    # ------------------------------------------------------------------
    # Phase 7: GraphExpansion
    # ------------------------------------------------------------------

    def _graph_expand(
        self,
        seed_items: list[RetrievedItem],
        knowledge_graph: dict[str, list[str]],
    ) -> list[RetrievedItem]:
        """Expand retrieval via knowledge graph connections."""
        if not knowledge_graph:
            return []

        expanded: list[RetrievedItem] = []
        visited: set[str] = set()

        for item in seed_items:
            if item.memory_id in visited:
                continue
            visited.add(item.memory_id)

            # One-hop expansion
            neighbors = knowledge_graph.get(item.memory_id, [])
            for neighbor_id in neighbors[:3]:  # Limit hops
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    expanded.append(RetrievedItem(
                        memory_id=neighbor_id,
                        memory_type='graph_expansion',
                        relevance_score=item.relevance_score * 0.7,
                        confidence_score=item.confidence_score * 0.8,
                        final_score=item.final_score * 0.6,
                        retrieval_path=(item.memory_id, neighbor_id),
                    ))

        return expanded

    # ------------------------------------------------------------------
    # Phase 8: EvidenceValidation
    # ------------------------------------------------------------------

    def _validate_evidence(
        self,
        items: list[RetrievedItem],
    ) -> list[RetrievedItem]:
        """Validate evidence for retrieved items."""
        validated: list[RetrievedItem] = []

        for item in items:
            # Items with supporting evidence or high confidence pass validation
            if item.confidence_score >= self._confidence_threshold or item.supporting_evidence:
                validated.append(item)
            elif item.final_score >= self._confidence_threshold:
                validated.append(item)

        return validated

    def _try_llm_relevance_scoring(self, items: list[RetrievedItem], query: str) -> list[RetrievedItem] | None:
        """Attempt LLM-assisted relevance scoring for retrieved items."""
        if self._ai_router is None or not items:
            return None
        try:
            import asyncio
            from ayeneh.ai_router.types import AITask, AITaskType
            item_summaries = '; '.join(
                f'{item.memory_id}:{item.content[:50]}' for item in items[:10]
            )
            prompt = (
                f'Score the relevance of each memory to the query: "{query}"\n'
                'Return a JSON list of objects with keys: memory_id, relevance_score (0.0-1.0).\n\n'
                f'Memories:\n{item_summaries}'
            )
            task = AITask(
                task_type=AITaskType.CONVERSATION_GENERATION,
                content=prompt,
                max_tokens=1024,
                temperature=0.3,
            )
            messages = [
                {'role': 'system', 'content': 'You are a memory analysis assistant.'},
                {'role': 'user', 'content': prompt},
            ]
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return None
            result = loop.run_until_complete(self._ai_router.chat(task, messages))
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            scores = self._parse_llm_scores(content)
            if scores is None:
                return None
            score_map = {s['memory_id']: s.get('relevance_score', 0.5) for s in scores}
            enhanced: list[RetrievedItem] = []
            for item in items:
                if item.memory_id in score_map:
                    llm_score = score_map[item.memory_id]
                    blended = item.relevance_score * 0.6 + llm_score * 0.4
                    enhanced.append(RetrievedItem(
                        memory_id=item.memory_id,
                        memory_type=item.memory_type,
                        content=item.content,
                        relevance_score=blended,
                        recency_score=item.recency_score,
                        importance_score=item.importance_score,
                        confidence_score=item.confidence_score,
                        final_score=item.final_score,
                        retrieval_path=item.retrieval_path,
                        supporting_evidence=item.supporting_evidence,
                        explainability_metadata=item.explainability_metadata,
                    ))
                else:
                    enhanced.append(item)
            return enhanced
        except Exception:
            return None

    def _parse_llm_scores(self, content: str) -> list[dict[str, Any]] | None:
        """Parse LLM JSON response for relevance scores."""
        import json
        try:
            start = content.find('[')
            end = content.rfind(']') + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    # ------------------------------------------------------------------
    # Phase 9: Ranking
    # ------------------------------------------------------------------

    def _rank(
        self,
        items: list[RetrievedItem],
        request: RetrievalRequest,
    ) -> list[RetrievedItem]:
        """Rank retrieved items by composite score."""
        weights = self._weights.normalize()

        # Try LLM-assisted scoring
        llm_enhanced = self._try_llm_relevance_scoring(items, request.conversation_context)
        if llm_enhanced is not None:
            items = llm_enhanced

        ranked: list[RetrievedItem] = []
        for item in items:
            composite = (
                item.relevance_score * weights.relevance
                + item.recency_score * weights.recency
                + item.importance_score * weights.importance
                + item.confidence_score * weights.confidence
            )

            ranked_item = RetrievedItem(
                memory_id=item.memory_id,
                memory_type=item.memory_type,
                content=item.content,
                relevance_score=item.relevance_score,
                recency_score=item.recency_score,
                importance_score=item.importance_score,
                confidence_score=item.confidence_score,
                final_score=composite,
                retrieval_path=item.retrieval_path,
                supporting_evidence=item.supporting_evidence,
                explainability_metadata=item.explainability_metadata,
            )
            ranked.append(ranked_item)

        ranked.sort(key=lambda x: x.final_score, reverse=True)
        return ranked

    # ------------------------------------------------------------------
    # Phase 10: WorkingMemoryAssembly
    # ------------------------------------------------------------------

    def _assemble(
        self,
        ranked: list[RetrievedItem],
        request: RetrievalRequest,
    ) -> list[RetrievedItem]:
        """Assemble the final retrieval set within size limits."""
        max_size = min(self._max_size, request.maximum_retrieval_size)
        return ranked[:max_size]
