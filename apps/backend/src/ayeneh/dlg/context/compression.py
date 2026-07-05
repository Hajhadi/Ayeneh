"""DLG-03 Context Compression.

Compresses ContextObject for efficiency while preserving traceability:
- Preserves: meaning, relationships, evidence, open questions, contradictions
- Never reduces explainability
"""

from __future__ import annotations

import dataclasses

import structlog

from ayeneh.dlg.context.types import ContextObject, RelevantEpisodes, WorkingMemory

logger = structlog.get_logger(__name__)


class ContextCompressor:
    """Compresses context objects while preserving traceability."""

    def __init__(self, max_entities: int = 20, max_episodes: int = 5) -> None:
        self._max_entities = max_entities
        self._max_episodes = max_episodes

    def compress(self, context: ContextObject) -> ContextObject:
        """Compress a context object, keeping the most salient items."""
        logger.debug('compress_start', context_id=context.context_identifier.id)

        wm = context.working_memory
        if len(wm.active_entities) > self._max_entities:
            wm = dataclasses.replace(
                wm, active_entities=wm.active_entities[:self._max_entities],
            )

        episodes = context.relevant_episodes
        if len(episodes.episode_ids) > self._max_episodes:
            episodes = _truncate_episodes(episodes, self._max_episodes)

        return ContextObject(
            context_identifier=context.context_identifier,
            conversation_identifier=context.conversation_identifier,
            current_intent=context.current_intent,
            current_dialogue_state=context.current_dialogue_state,
            primary_cognitive_focus=context.primary_cognitive_focus,
            working_memory=wm,
            relevant_episodes=episodes,
            relevant_semantic_memories=context.relevant_semantic_memories,
            relevant_beliefs=context.relevant_beliefs,
            relevant_narratives=context.relevant_narratives,
            relevant_goals=context.relevant_goals,
            relevant_identity_components=context.relevant_identity_components,
            relevant_behavioral_patterns=context.relevant_behavioral_patterns,
            relevant_predictions=context.relevant_predictions,
            relevant_reality_objects=context.relevant_reality_objects,
            context_confidence=context.context_confidence,
            version_metadata=context.version_metadata,
        )

    def estimate_tokens(self, context: ContextObject) -> int:
        """Estimate token count for the context."""
        count = 0
        count += len(context.working_memory.active_entities) * 3
        count += len(context.working_memory.recent_facts) * 10
        count += len(context.relevant_episodes.episode_ids) * 8
        count += len(context.relevant_semantic_memories.memory_ids) * 8
        count += len(context.relevant_beliefs.belief_statements) * 15
        count += len(context.relevant_narratives.narrative_summaries) * 15
        count += len(context.relevant_goals.goal_descriptions) * 10
        count += len(context.relevant_identity_components.component_descriptions) * 12
        count += len(context.relevant_behavioral_patterns.pattern_descriptions) * 12
        count += len(context.relevant_predictions.prediction_statements) * 10
        count += len(context.relevant_reality_objects.descriptions) * 12
        return count


def _truncate_episodes(episodes: RelevantEpisodes, max_count: int) -> RelevantEpisodes:
    return RelevantEpisodes(
        episode_ids=episodes.episode_ids[:max_count],
        episode_summaries=episodes.episode_summaries[:max_count],
        relevance_scores=episodes.relevance_scores[:max_count],
        temporal_distances=episodes.temporal_distances[:max_count],
        emotional_resonances=episodes.emotional_resonances[:max_count],
    )
