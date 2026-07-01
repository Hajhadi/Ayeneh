"""Adaptive context selection — decides which context to inject based on relevance and budget."""

from __future__ import annotations

import structlog
from typing import Any

from ayeneh.prompt.types import AdaptiveSelection, ReasoningPolicy

logger = structlog.get_logger(__name__)


class AdaptiveSelector:
    """Selects which context elements to inject based on relevance, confidence, and token budget."""

    def select(
        self,
        retrieval: Any,
        policy: ReasoningPolicy,
        query: str,
        token_budget: int = 12000,
    ) -> AdaptiveSelection:
        sel = AdaptiveSelection(token_budget=token_budget)
        remaining = token_budget

        if retrieval.urgent_goals:
            for g in retrieval.urgent_goals[:3]:
                tokens = _estimate_tokens(g.get("title", "") + str(g.get("deadline", "")))
                if remaining - tokens > 0:
                    sel.goals_to_inject.append(g)
                    remaining -= tokens
                else:
                    sel.rejected_items.append({"type": "goal", "id": g.get("id"), "reason": "budget"})

        if policy.goal_priority != "low":
            for g in retrieval.active_goals[:5]:
                tokens = _estimate_tokens(g.get("title", ""))
                if remaining - tokens > 0:
                    sel.goals_to_inject.append(g)
                    remaining -= tokens
                else:
                    sel.rejected_items.append({"type": "goal", "id": g.get("id"), "reason": "budget"})

        for g in retrieval.blocked_goals[:3]:
            tokens = _estimate_tokens(g.get("title", ""))
            if remaining - tokens > 0:
                sel.goals_to_inject.append(g)
                remaining -= tokens

        if policy.memory_priority != "low":
            for m in retrieval.memories[:10]:
                score = m.get("score", 0.5) * m.get("confidence", 0.5)
                tokens = _estimate_tokens(m.get("content", ""))
                if score > 0.2 and remaining - tokens > 0:
                    sel.memories_to_inject.append(m)
                    remaining -= tokens
                else:
                    sel.rejected_items.append({"type": "memory", "id": m.get("id"), "reason": "low_score" if score <= 0.2 else "budget"})

        for c in retrieval.knowledge_chunks[:5]:
            score = c.get("score", 0.5)
            tokens = _estimate_tokens(c.get("content", ""))
            if score > 0.3 and remaining - tokens > 0:
                sel.knowledge_to_inject.append(c)
                remaining -= tokens
            else:
                sel.rejected_items.append({"type": "knowledge", "reason": "low_score" if score <= 0.3 else "budget"})

        for p in retrieval.patterns[:3]:
            sel.patterns_to_inject.append(p)

        for r in retrieval.reflections[:2]:
            sel.reflections_to_inject.append(r)

        for p in retrieval.recent_goal_progress[:3]:
            sel.goals_to_inject.append(p)

        sel.total_tokens = token_budget - remaining
        return sel


def _estimate_tokens(text: str) -> int:
    return max(1, len(str(text).split()) * 4 // 3)
