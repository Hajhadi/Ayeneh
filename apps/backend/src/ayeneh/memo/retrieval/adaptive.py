"""Adaptive retrieval for working memory (MEM-06).

Handles multi-hop retrieval across the knowledge graph, adaptive
retrieval triggered by new information, and dynamic strategy selection.
"""

from __future__ import annotations

import uuid

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.retrieval.types import (
    DETECTED_INTENTS,
    RETRIEVAL_STRATEGIES,
    AdaptiveRetrievalTrigger,
    EvidenceValidationResult,
    GraphExpansionResult,
    MultiHopRetrieval,
    RankingWeights,
    RetrievedItem,
    RetrievalRequest,
    RetrievalResult,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Multi-hop retriever
# ---------------------------------------------------------------------------


class MultiHopRetriever:
    """Performs recursive graph expansion until sufficient context is found.

    Follows knowledge graph edges with confidence decay to find
    connected memories that provide additional context.
    """

    def __init__(
        self,
        max_hops: int = 5,
        confidence_decay: float = 0.9,
        min_confidence: float = 0.2,
    ) -> None:
        self._max_hops = max_hops
        self._confidence_decay = confidence_decay
        self._min_confidence = min_confidence

    def retrieve(
        self,
        seed_ids: tuple[str, ...],
        knowledge_graph: dict[str, list[str]],
        memory_store: dict[str, dict[str, Any]],
    ) -> tuple[list[RetrievedItem], MultiHopRetrieval]:
        """Perform multi-hop retrieval from seed nodes."""
        all_items: list[RetrievedItem] = []
        visited: set[str] = set(seed_ids)
        current_ids = list(seed_ids)
        hop_count = 0

        while current_ids and hop_count < self._max_hops:
            next_ids: list[str] = []
            current_confidence = self._confidence_decay ** hop_count

            if current_confidence < self._min_confidence:
                break

            for node_id in current_ids:
                neighbors = knowledge_graph.get(node_id, [])
                for neighbor_id in neighbors:
                    if neighbor_id in visited:
                        continue
                    visited.add(neighbor_id)

                    # Retrieve memory data
                    mem_data = memory_store.get(neighbor_id, {})
                    item = RetrievedItem(
                        memory_id=neighbor_id,
                        memory_type=mem_data.get('type', 'graph_expansion'),
                        content=mem_data.get('content', ''),
                        relevance_score=current_confidence,
                        confidence_score=mem_data.get('confidence', 0.5) * current_confidence,
                        final_score=current_confidence * 0.5,
                        retrieval_path=(node_id, neighbor_id),
                    )
                    all_items.append(item)
                    next_ids.append(neighbor_id)

            if next_ids:
                hop_count += 1
            current_ids = next_ids

        multi_hop = MultiHopRetrieval(
            hop_id=f"mh_{uuid.uuid4().hex[:12]}",
            starting_memory_id=seed_ids[0] if seed_ids else '',
            current_memory_id=current_ids[0] if current_ids else '',
            hop_count=hop_count,
            max_hops=self._max_hops,
            visited_ids=tuple(visited),
            confidence_decay=self._confidence_decay,
        )

        logger.debug(
            'multi_hop_complete',
            hops=hop_count,
            items_found=len(all_items),
        )

        return all_items, multi_hop


# ---------------------------------------------------------------------------
# Adaptive retrieval manager
# ---------------------------------------------------------------------------


class AdaptiveRetrievalManager:
    """Manages adaptive retrieval triggered by new information.

    When new information arrives during a conversation, this manager
    determines if additional retrieval is needed and triggers it.
    """

    def __init__(self) -> None:
        self._triggers: dict[str, AdaptiveRetrievalTrigger] = {}
        self._trigger_history: list[AdaptiveRetrievalTrigger] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_triggers(
        self,
        new_information: str,
        current_results: list[RetrievedItem],
        *,
        conversation_context: str = '',
    ) -> list[AdaptiveRetrievalTrigger]:
        """Evaluate whether new information should trigger additional retrieval."""
        triggers: list[AdaptiveRetrievalTrigger] = []

        # Check for entity mentions not in current results
        new_words = set(new_information.lower().split())
        covered_words: set[str] = set()
        for item in current_results:
            covered_words.update(item.content.lower().split())

        uncovered = new_words - covered_words
        if len(uncovered) >= 2:
            trigger = AdaptiveRetrievalTrigger(
                trigger_id=f"tr_{uuid.uuid4().hex[:8]}",
                trigger_reason='new_entities_detected',
                new_information=new_information,
                suggested_strategy='semantic_first',
                priority=0.6 + min(0.4, len(uncovered) * 0.1),
            )
            triggers.append(trigger)

        # Check for contradiction indicators
        contradiction_words = {'but', 'however', 'actually', 'incorrect', 'wrong', 'unlike'}
        if new_words & contradiction_words:
            trigger = AdaptiveRetrievalTrigger(
                trigger_id=f"tr_{uuid.uuid4().hex[:8]}",
                trigger_reason='contradiction_detected',
                new_information=new_information,
                suggested_strategy='evidence_first',
                priority=0.8,
            )
            triggers.append(trigger)

        # Check for question words requiring deeper retrieval
        question_words = {'why', 'how', 'explain', 'reason'}
        if new_words & question_words and len(current_results) < 3:
            trigger = AdaptiveRetrievalTrigger(
                trigger_id=f"tr_{uuid.uuid4().hex[:8]}",
                trigger_reason='insufficient_context_for_explanation',
                new_information=new_information,
                suggested_strategy='episode_first',
                priority=0.7,
            )
            triggers.append(trigger)

        # Store triggers
        for trigger in triggers:
            self._triggers[trigger.trigger_id] = trigger
            self._trigger_history.append(trigger)

        if triggers:
            logger.debug(
                'adaptive_triggers_generated',
                count=len(triggers),
                reasons=[t.trigger_reason for t in triggers],
            )

        return triggers

    def resolve_trigger(self, trigger_id: str) -> bool:
        """Mark a trigger as resolved."""
        trigger = self._triggers.get(trigger_id)
        if trigger is None:
            return False

        resolved = AdaptiveRetrievalTrigger(
            trigger_id=trigger.trigger_id,
            trigger_reason=trigger.trigger_reason,
            new_information=trigger.new_information,
            suggested_strategy=trigger.suggested_strategy,
            priority=trigger.priority,
            created_at=trigger.created_at,
            resolved=True,
        )
        self._triggers[trigger_id] = resolved
        return True

    def get_pending_triggers(self) -> list[AdaptiveRetrievalTrigger]:
        """Return all unresolved triggers."""
        return [t for t in self._triggers.values() if not t.resolved]

    def get_trigger_history(self) -> list[AdaptiveRetrievalTrigger]:
        """Return the full trigger history."""
        return list(self._trigger_history)


# ---------------------------------------------------------------------------
# Strategy selector
# ---------------------------------------------------------------------------


class RetrievalStrategySelector:
    """Selects the optimal retrieval strategy based on context."""

    def __init__(self) -> None:
        self._strategy_scores: dict[str, float] = {
            strategy: 0.5 for strategy in RETRIEVAL_STRATEGIES
        }

    def select(
        self,
        request: RetrievalRequest,
        triggers: list[AdaptiveRetrievalTrigger] | None = None,
    ) -> str:
        """Select the best retrieval strategy for the given context."""
        triggers = triggers or []

        # Start with explicit strategy if provided (not the default 'composite')
        if (
            request.ranking_strategy in RETRIEVAL_STRATEGIES
            and request.ranking_strategy != 'composite'
        ):
            return request.ranking_strategy

        # Score strategies based on intent
        intent = request.detected_intent
        if intent == 'explain':
            return 'evidence_first'
        elif intent == 'reflect':
            return 'episode_first'
        elif intent == 'plan':
            return 'trajectory_first'
        elif intent == 'compare':
            return 'semantic_first'
        elif request.has_focus:
            return 'identity_first'

        # Check triggers for strategy hints
        for trigger in triggers:
            if trigger.is_high_priority:
                return trigger.suggested_strategy

        # Default based on context
        if request.relevant_episodes:
            return 'episode_first'
        if request.relevant_projects:
            return 'narrative_first'

        return 'composite'

    def update_scores(self, strategy: str, success: bool) -> None:
        """Update strategy scores based on success/failure."""
        if strategy in self._strategy_scores:
            delta = 0.1 if success else -0.05
            self._strategy_scores[strategy] = max(
                0.0, min(1.0, self._strategy_scores[strategy] + delta)
            )

    def get_strategy_scores(self) -> dict[str, float]:
        """Return the current strategy scores."""
        return dict(self._strategy_scores)


# ---------------------------------------------------------------------------
# Evidence validator
# ---------------------------------------------------------------------------


class EvidenceValidator:
    """Validates evidence quality for retrieved memories."""

    def __init__(self, min_support_ratio: float = 0.5) -> None:
        self._min_support_ratio = min_support_ratio

    def validate(
        self,
        items: list[RetrievedItem],
        evidence_store: dict[str, list[dict[str, Any]]],
    ) -> tuple[list[RetrievedItem], list[EvidenceValidationResult]]:
        """Validate evidence for a set of retrieved items."""
        validated: list[RetrievedItem] = []
        results: list[EvidenceValidationResult] = []

        for item in items:
            evidence_list = evidence_store.get(item.memory_id, [])
            supporting = sum(1 for e in evidence_list if e.get('supports', True))
            contradicting = len(evidence_list) - supporting

            support_ratio = supporting / len(evidence_list) if evidence_list else 0.0
            is_valid = support_ratio >= self._min_support_ratio or item.confidence_score >= 0.7

            result = EvidenceValidationResult(
                memory_id=item.memory_id,
                evidence_count=len(evidence_list),
                supporting_count=supporting,
                contradicting_count=contradicting,
                validation_score=support_ratio,
                is_valid=is_valid,
            )
            results.append(result)

            if is_valid:
                validated.append(item)

        return validated, results
