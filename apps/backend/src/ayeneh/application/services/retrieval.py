"""Retrieval service — unified retrieval across all cognitive sources including Goals.

Goals are retrieved as a separate context block alongside memories,
patterns, reflections, and knowledge. Goal retrieval is independent
from Memory retrieval — no duplication, no coupling.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class EpistemicMetadata:
    """Concise epistemic explanations for prompt context."""

    selection_reasons: list[str] = field(default_factory=list)
    outranking_reasons: list[str] = field(default_factory=list)
    confidence_explanations: list[str] = field(default_factory=list)
    applicability_explanations: list[str] = field(default_factory=list)
    domain_distribution: dict[str, int] = field(default_factory=dict)
    authority_distribution: dict[str, int] = field(default_factory=dict)
    scope_filtered_count: int = 0
    ranking_latency_ms: float = 0.0


@dataclass
class RetrievalResult:
    """Aggregated retrieval context from all sources."""

    memories: list[dict[str, Any]] = field(default_factory=list)
    patterns: list[dict[str, Any]] = field(default_factory=list)
    reflections: list[dict[str, Any]] = field(default_factory=list)
    knowledge_chunks: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    token_budget: int = 8000
    tokens_used: int = 0
    evolved_memory_count: int = 0
    superseded_memory_count: int = 0

    # Goal context — independent from memory retrieval
    active_goals: list[dict[str, Any]] = field(default_factory=list)
    blocked_goals: list[dict[str, Any]] = field(default_factory=list)
    urgent_goals: list[dict[str, Any]] = field(default_factory=list)
    recent_goal_progress: list[dict[str, Any]] = field(default_factory=list)
    goal_count: int = 0

    # Epistemic metadata — populated when epistemic strategy is available
    epistemic_metadata: EpistemicMetadata | None = None


class RetrievalService:
    """Aggregates retrieval across all data sources.

    Goal retrieval is provided via an optional goal_retrieval parameter.
    Goals are independent from memory retrieval and never replace it.
    Epistemic retrieval is provided via an optional epistemic_strategy parameter.
    If absent, existing behavior remains unchanged.
    """

    def __init__(
        self,
        memory_service: Any | None = None,
        knowledge_service: Any | None = None,
        pattern_service: Any | None = None,
        reflection_service: Any | None = None,
        evolution_aware_strategy: Any | None = None,
        evolution_service: Any | None = None,
        goal_retrieval: Any | None = None,
        goal_service: Any | None = None,
        epistemic_strategy: Any | None = None,
    ) -> None:
        self._memory_service = memory_service
        self._knowledge_service = knowledge_service
        self._pattern_service = pattern_service
        self._reflection_service = reflection_service
        self._evolution_aware = evolution_aware_strategy
        self._evolution_service = evolution_service
        self._goal_retrieval = goal_retrieval
        self._goal_service = goal_service
        self._epistemic_strategy = epistemic_strategy

    async def retrieve_context(
        self,
        user_id: str,
        query: str,
        *,
        token_budget: int = 8000,
    ) -> RetrievalResult:
        result = RetrievalResult(token_budget=token_budget)

        if self._knowledge_service:
            try:
                kb_ctx = await self._knowledge_service.retrieve(
                    uuid.UUID(user_id), query
                )
                for rc in kb_ctx.chunks:
                    result.knowledge_chunks.append({
                        "content": rc.chunk.content,
                        "book_title": rc.book.title,
                        "author": rc.book.author,
                        "section": rc.chunk.section_heading,
                        "score": rc.final_score,
                    })
                    if rc.citation:
                        result.citations.append({
                            "book_title": rc.citation.book_title,
                            "author": rc.citation.author,
                            "section": rc.citation.section_heading,
                            "excerpt": rc.citation.excerpt,
                            "score": rc.citation.score,
                        })
                result.tokens_used += kb_ctx.total_tokens_estimate
            except Exception as exc:
                logger.warning("knowledge_retrieval_failed", error=str(exc))

        result.memories = await self._retrieve_memories(user_id, query)
        result.patterns = await self._retrieve_patterns(user_id)
        result.reflections = await self._retrieve_reflections(user_id)
        result.active_goals, result.blocked_goals, result.urgent_goals, result.recent_goal_progress = \
            await self._retrieve_goals(user_id)

        # Epistemic metadata — if strategy is available
        if self._epistemic_strategy:
            result.epistemic_metadata = self._retrieve_epistemic_metadata(query)

        result.evolved_memory_count = sum(
            1 for m in result.memories if m.get("evolution_version", 1) > 1
        )
        result.superseded_memory_count = sum(
            1 for m in result.memories if m.get("status") == "superseded"
        )
        result.goal_count = len(result.active_goals) + len(result.blocked_goals) + len(result.urgent_goals)

        return result

    async def _retrieve_goals(
        self, user_id: str
    ) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
        """Retrieve goals independently. Returns (active, blocked, urgent, recent_progress)."""
        if not self._goal_retrieval or not self._goal_service:
            return [], [], [], []

        try:
            active = await self._goal_service.get_active_goals(user_id)
            active_dicts = [
                {"id": g.id, "title": g.title, "progress": g.progress,
                 "priority": g.priority, "deadline": g.deadline,
                 "importance": g.importance, "category": g.category}
                for g in active[:10]
            ]

            blocked = await self._goal_retrieval.retrieve_blocked(user_id)
            blocked_dicts = [
                {"id": g.id, "title": g.title, "dependencies": len(g.dependencies)}
                for g in blocked[:5]
            ]

            urgent = await self._goal_retrieval.retrieve_urgent(user_id)
            urgent_dicts = [
                {"id": g.id, "title": g.title, "deadline": g.deadline,
                 "progress": g.progress}
                for g in urgent[:5]
            ]

            recent = []
            for g in active:
                if g.last_progress_at:
                    recent.append({
                        "goal": g.title, "progress": g.progress,
                        "at": g.last_progress_at,
                    })
            recent = recent[:5]

            return active_dicts, blocked_dicts, urgent_dicts, recent
        except Exception as exc:
            logger.warning("goal_retrieval_failed", error=str(exc))
            return [], [], [], []

    async def _retrieve_memories(
        self, user_id: str, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        try:
            if self._evolution_aware:
                ctx = await self._evolution_aware.retrieve(
                    uuid.UUID(user_id), query, limit=limit
                )
            elif self._memory_service:
                ctx = await self._memory_service.retrieve(
                    uuid.UUID(user_id), query, limit=limit
                )
            else:
                return []

            memories = []
            for ms in ctx.scores:
                mem_data = {
                    "id": str(ms.memory.id),
                    "type": ms.memory.type.value,
                    "content": ms.memory.content,
                    "confidence": ms.memory.confidence,
                    "score": ms.final_score,
                }
                ev_ver = getattr(ms.memory, "evolution_version", None)
                if ev_ver is not None:
                    mem_data["evolution_version"] = ev_ver
                status = getattr(ms.memory, "status", None)
                if status is not None:
                    mem_data["status"] = status
                conf_hist = getattr(ms.memory, "confidence_history", None)
                if conf_hist and isinstance(conf_hist, dict):
                    mem_data["confidence_history"] = conf_hist
                memories.append(mem_data)
            return memories
        except Exception as exc:
            logger.warning("memory_retrieval_failed", error=str(exc))
            return []

    async def _retrieve_patterns(
        self, user_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        if not self._pattern_service:
            return []
        try:
            return await self._pattern_service.list_patterns(user_id, limit=limit)
        except Exception:
            return []

    async def _retrieve_reflections(
        self, user_id: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        if not self._reflection_service:
            return []
        try:
            return await self._reflection_service.list_reflections(user_id, limit=limit)
        except Exception:
            return []

    def _retrieve_epistemic_metadata(self, query: str) -> EpistemicMetadata:
        """Retrieve epistemic metadata from the strategy.

        This is synchronous because the strategy analyzes the query
        and doesn't need to access external services.
        """
        if not self._epistemic_strategy:
            return EpistemicMetadata()

        try:
            analysis = self._epistemic_strategy.analyze_request(query)
            # Note: Full ranking requires profiles, which would come from the
            # epistemic profile repository. For now, we just analyze the request.
            return EpistemicMetadata(
                selection_reasons=[],
                outranking_reasons=[],
                confidence_explanations=[],
                applicability_explanations=[],
                domain_distribution={},
                authority_distribution={},
                scope_filtered_count=0,
                ranking_latency_ms=0.0,
            )
        except Exception as exc:
            logger.warning("epistemic_metadata_retrieval_failed", error=str(exc))
            return EpistemicMetadata()
