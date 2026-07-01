"""Evidence collection — gathers evidence from all cognitive sources with provenance."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.reasoning.types import Evidence, EvidenceSource

logger = structlog.get_logger(__name__)


class EvidenceCollector:
    """Collects evidence independently from all cognitive sources."""

    def __init__(
        self, goal_service: Any = None, goal_retrieval: Any = None,
        retrieval_service: Any = None,
    ) -> None:
        self._goal_service = goal_service
        self._goal_retrieval = goal_retrieval
        self._retrieval = retrieval_service

    async def collect_all(
        self, user_id: str, query: str, *,
        include_goals: bool = True,
        include_memories: bool = True,
        include_knowledge: bool = True,
        include_patterns: bool = True,
        include_reflections: bool = True,
    ) -> list[Evidence]:
        evidence: list[Evidence] = []

        if include_goals:
            evidence.extend(await self._collect_goals(user_id))
        if include_memories or include_knowledge or include_patterns or include_reflections:
            evidence.extend(await self._collect_retrieval_evidence(user_id, query))

        evidence.sort(key=lambda e: e.confidence * e.relevance, reverse=True)
        logger.info("evidence_collected", user_id=user_id, count=len(evidence))
        return evidence

    async def _collect_goals(self, user_id: str) -> list[Evidence]:
        evidence = []
        if not self._goal_service:
            return evidence
        try:
            goals = await self._goal_service.get_active_goals(user_id)
            for g in goals:
                evidence.append(Evidence(
                    source_type=EvidenceSource.GOAL,
                    source_id=g.id,
                    content=f"{g.title} (progress: {g.progress:.0%}, priority: {g.priority})",
                    confidence=g.confidence,
                    relevance=g.importance,
                    recency_days=self._days_since(g.last_progress_at or g.created_at),
                    metadata={"priority": g.priority, "progress": g.progress, "deadline": g.deadline},
                ))
        except Exception as exc:
            logger.warning("goal_evidence_failed", error=str(exc))
        return evidence

    async def _collect_retrieval_evidence(self, user_id: str, query: str) -> list[Evidence]:
        evidence = []
        if not self._retrieval:
            return evidence
        try:
            result = await self._retrieval.retrieve_context(user_id, query)

            for m in result.memories[:10]:
                evidence.append(Evidence(
                    source_type=EvidenceSource.MEMORY,
                    source_id=m.get("id", ""),
                    content=m.get("content", ""),
                    confidence=m.get("confidence", 0.5),
                    relevance=m.get("score", 0.5),
                    recency_days=0,
                    metadata={"type": m.get("type", "")},
                ))

            for k in result.knowledge_chunks[:5]:
                evidence.append(Evidence(
                    source_type=EvidenceSource.KNOWLEDGE,
                    source_id="",
                    content=k.get("content", "")[:500],
                    confidence=0.8,
                    relevance=k.get("score", 0.5),
                    metadata={"book": k.get("book_title", ""), "section": k.get("section", "")},
                ))

            for p in result.patterns[:5]:
                evidence.append(Evidence(
                    source_type=EvidenceSource.PATTERN,
                    source_id="",
                    content=p.get("description", ""),
                    confidence=0.7,
                    relevance=0.6,
                    metadata={"evidence_count": p.get("evidence_count", 0)},
                ))

            for r in result.reflections[:3]:
                evidence.append(Evidence(
                    source_type=EvidenceSource.REFLECTION,
                    source_id=r.get("id", ""),
                    content=r.get("narrative", "")[:500],
                    confidence=0.7,
                    relevance=0.5,
                ))

        except Exception as exc:
            logger.warning("retrieval_evidence_failed", error=str(exc))
            return evidence

    @staticmethod
    def _days_since(date_str: str | None) -> float:
        if not date_str:
            return 365.0
        try:
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo:
                dt = dt.replace(tzinfo=None)
            return max(0, (datetime.now(UTC).replace(tzinfo=None) - dt).total_seconds() / 86400)
        except Exception:
            return 365.0
