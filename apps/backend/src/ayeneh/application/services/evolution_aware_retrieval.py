"""Evolution-aware retrieval strategy — prioritizes evolved memories over raw.

This module provides EvolutionAwareRetrievalStrategy, which wraps the
existing MemoryService and adds evolution-awareness: it boosts active
memories with higher evolution_version, prefers memories with confidence
history, and deprioritizes superseded or low-confidence memories.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class EvolutionAwareConfig:
    """Configuration for evolution-aware retrieval behavior."""

    evolution_boost_weight: float = 0.2
    confidence_history_boost: float = 0.1
    active_status_boost: float = 0.15
    superseded_penalty: float = -0.3
    min_evolution_version: int = 1
    max_age_for_boost_days: int = 180


@dataclass
class EvolutionAwareRetrievalStrategy:
    """Retrieval strategy that integrates memory evolution signals.

    Wraps a MemoryService and adds evolution-awareness to retrieval:
    - Active memories with higher evolution_version get boosted
    - Memories with confidence_history entries get boosted
    - Superseded memories get penalized
    - Results are re-ranked by composite evolution-aware score
    """

    memory_service: Any
    evolution_service: Any | None = None
    config: EvolutionAwareConfig = field(default_factory=EvolutionAwareConfig)

    async def retrieve(
        self,
        user_id: uuid.UUID,
        query: str,
        *,
        limit: int = 10,
        memory_types: list[str] | None = None,
    ) -> Any:
        """Retrieve memories with evolution-aware re-ranking."""
        raw_context = await self.memory_service.retrieve(
            user_id,
            query,
            limit=limit * 3,
            memory_types=memory_types,
        )

        if not self.evolution_service:
            return raw_context

        scored_memories = []
        for ms in raw_context.scores:
            evolution_bonus = await self._compute_evolution_bonus(ms.memory)
            ms.final_score += evolution_bonus
            scored_memories.append(ms)

        scored_memories.sort(key=lambda s: s.final_score, reverse=True)
        raw_context.scores = scored_memories[:limit]

        for bucket_name in ("episodic", "semantic", "pattern", "reflection"):
            bucket = getattr(raw_context, bucket_name, [])
            if bucket and len(raw_context.scores) > 0:
                kept_ids = {s.memory.id for s in raw_context.scores}
                setattr(
                    raw_context,
                    bucket_name,
                    [m for m in bucket if m.id in kept_ids],
                )

        return raw_context

    async def _compute_evolution_bonus(self, memory: Any) -> float:
        """Compute evolution-aware score bonus for a memory."""
        bonus = 0.0
        cfg = self.config

        if memory.status == "active":
            bonus += cfg.active_status_boost
        elif memory.status == "superseded":
            bonus += cfg.superseded_penalty

        ev_ver = getattr(memory, "evolution_version", 1)
        if ev_ver > cfg.min_evolution_version:
            bonus += cfg.evolution_boost_weight * min(ev_ver / 5.0, 1.0)

        conf_history = getattr(memory, "confidence_history", None)
        if conf_history and isinstance(conf_history, dict) and len(conf_history) > 1:
            bonus += cfg.confidence_history_boost * min(len(conf_history) / 5.0, 1.0)

        return bonus
