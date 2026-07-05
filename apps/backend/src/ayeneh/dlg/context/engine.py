"""DLG-03 Context Builder engine.

9-phase pipeline for building a rich ContextObject:

1. UserInput — ingest raw user input
2. IntentDetection — classify user intent
3. ConversationState — assess dialogue state
4. WorkingMemory — populate working memory
5. RelevantEpisodes — retrieve episodic memories
6. SemanticMemories — retrieve semantic memories
7. KnowledgeGraphExpansion — expand via graph traversal
8. ContextAssembly — compose the ContextObject
9. Inference — derive implied context
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.dlg.context.types import (
    ContextConfidence,
    ContextIdentifier,
    ContextObject,
    ConversationIdentifier,
    CurrentDialogueState,
    CurrentIntent,
    PrimaryCognitiveFocus,
    RelevantBehavioralPatterns,
    RelevantBeliefs,
    RelevantEpisodes,
    RelevantGoals,
    RelevantIdentityComponents,
    RelevantNarratives,
    RelevantPredictions,
    RelevantRealityObjects,
    RelevantSemanticMemories,
    WorkingMemory,
)

logger = structlog.get_logger(__name__)


class ContextBuilder:
    """Builds a ContextObject through a 9-phase pipeline (DLG-03)."""

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        user_input: str,
        conversation_id: str = '',
        session_id: str = '',
        user_id: str = '',
        turn_number: int = 0,
        prior_context: ContextObject | None = None,
        available_memories: dict[str, Any] | None = None,
    ) -> ContextObject:
        """Run the full 9-phase context-building pipeline."""
        logger.info('context_pipeline_start', conversation_id=conversation_id)

        # Phase 1 — UserInput
        raw_input = self._phase_user_input(user_input, conversation_id, user_id)

        # Phase 2 — IntentDetection
        intent = self._phase_intent_detection(raw_input)

        # Phase 3 — ConversationState
        dialogue_state = self._phase_conversation_state(
            raw_input, prior_context,
        )

        # Phase 4 — WorkingMemory
        working_mem = self._phase_working_memory(raw_input, prior_context)

        # Phase 5 — RelevantEpisodes
        episodes = self._phase_relevant_episodes(raw_input, available_memories)

        # Phase 6 — SemanticMemories
        semantic = self._phase_semantic_memories(raw_input, available_memories)

        # Phase 7 — KnowledgeGraphExpansion
        beliefs, narratives, goals, identity, behavioral, predictions, reality = (
            self._phase_knowledge_graph_expansion(raw_input, available_memories)
        )

        # Phase 8 — ContextAssembly
        context = self._phase_context_assembly(
            raw_input, conversation_id, session_id, user_id, turn_number,
            intent, dialogue_state, working_mem, episodes, semantic,
            beliefs, narratives, goals, identity, behavioral, predictions,
            reality,
        )

        # Phase 9 — Inference
        context = self._phase_inference(context)

        logger.info('context_pipeline_end', context_id=context.context_identifier.id)
        return context

    # ------------------------------------------------------------------
    # Phase 1 — UserInput
    # ------------------------------------------------------------------

    def _phase_user_input(
        self, user_input: str, conversation_id: str, user_id: str,
    ) -> dict[str, Any]:
        logger.debug('phase_1_user_input', input_length=len(user_input))
        return {
            'raw_text': user_input,
            'conversation_id': conversation_id,
            'user_id': user_id,
            'word_count': len(user_input.split()),
            'character_count': len(user_input),
        }

    # ------------------------------------------------------------------
    # Phase 2 — IntentDetection
    # ------------------------------------------------------------------

    def _phase_intent_detection(self, raw_input: dict[str, Any]) -> CurrentIntent:
        text = raw_input.get('raw_text', '')
        intent_type = 'general_inquiry'
        confidence = 0.5

        if any(w in text.lower() for w in ('how', 'why', 'what')):
            intent_type = 'information_seeking'
            confidence = 0.7
        elif any(w in text.lower() for w in ('i feel', 'i think', 'i believe')):
            intent_type = 'self_expression'
            confidence = 0.65
        elif any(w in text.lower() for w in ('help', 'need', 'want')):
            intent_type = 'assistance_request'
            confidence = 0.6

        logger.debug('phase_2_intent', intent_type=intent_type, confidence=confidence)
        return CurrentIntent(
            intent_type=intent_type,
            confidence=confidence,
            description=f'Detected intent: {intent_type}',
        )

    # ------------------------------------------------------------------
    # Phase 3 — ConversationState
    # ------------------------------------------------------------------

    def _phase_conversation_state(
        self, raw_input: dict[str, Any], prior: ContextObject | None,
    ) -> CurrentDialogueState:
        if prior is not None:
            prev_state = prior.current_dialogue_state
            return CurrentDialogueState(
                phase='continuation',
                topic=prev_state.topic or raw_input.get('raw_text', '')[:50],
                depth=prev_state.depth + 1,
                emotional_valence=prev_state.emotional_valence,
                engagement_level=min(1.0, prev_state.engagement_level + 0.05),
                pending_questions=prev_state.pending_questions,
                unresolved_topics=prev_state.unresolved_topics,
            )
        return CurrentDialogueState(
            phase='opening',
            topic='',
            depth=0,
            emotional_valence=0.0,
            engagement_level=0.5,
        )

    # ------------------------------------------------------------------
    # Phase 4 — WorkingMemory
    # ------------------------------------------------------------------

    def _phase_working_memory(
        self, raw_input: dict[str, Any], prior: ContextObject | None,
    ) -> WorkingMemory:
        words = raw_input.get('raw_text', '').split()
        entities = tuple(w for w in words if w and w[0].isupper() and len(w) > 2)

        if prior is not None:
            prev_wm = prior.working_memory
            combined = tuple(dict.fromkeys(prev_wm.active_entities + entities))
            return WorkingMemory(
                active_entities=combined[-20:],
                active_relations=prev_wm.active_relations,
                recent_facts=prev_wm.recent_facts,
                active_goals=prev_wm.active_goals,
                emotional_state=prev_wm.emotional_state,
                capacity_used=min(1.0, prev_wm.capacity_used + 0.1),
            )

        return WorkingMemory(
            active_entities=entities,
            active_relations=(),
            recent_facts=(raw_input.get('raw_text', ''),),
            active_goals=(),
            emotional_state='neutral',
            capacity_used=0.1,
        )

    # ------------------------------------------------------------------
    # Phase 5 — RelevantEpisodes
    # ------------------------------------------------------------------

    def _phase_relevant_episodes(
        self, raw_input: dict[str, Any], memories: dict[str, Any] | None,
    ) -> RelevantEpisodes:
        if memories is None:
            return RelevantEpisodes()
        episode_ids = tuple(memories.get('episode_ids', ()))
        return RelevantEpisodes(
            episode_ids=episode_ids,
            episode_summaries=tuple(memories.get('episode_summaries', ())),
            relevance_scores=tuple(memories.get('relevance_scores', ())),
            temporal_distances=tuple(memories.get('temporal_distances', ())),
            emotional_resonances=tuple(memories.get('emotional_resonances', ())),
        )

    # ------------------------------------------------------------------
    # Phase 6 — SemanticMemories
    # ------------------------------------------------------------------

    def _phase_semantic_memories(
        self, raw_input: dict[str, Any], memories: dict[str, Any] | None,
    ) -> RelevantSemanticMemories:
        if memories is None:
            return RelevantSemanticMemories()
        return RelevantSemanticMemories(
            memory_ids=tuple(memories.get('semantic_ids', ())),
            concepts=tuple(memories.get('concepts', ())),
            confidence_scores=tuple(memories.get('semantic_confidences', ())),
            source_references=tuple(memories.get('source_references', ())),
        )

    # ------------------------------------------------------------------
    # Phase 7 — KnowledgeGraphExpansion
    # ------------------------------------------------------------------

    def _phase_knowledge_graph_expansion(
        self, raw_input: dict[str, Any], memories: dict[str, Any] | None,
    ) -> tuple[
        RelevantBeliefs,
        RelevantNarratives,
        RelevantGoals,
        RelevantIdentityComponents,
        RelevantBehavioralPatterns,
        RelevantPredictions,
        RelevantRealityObjects,
    ]:
        if memories is None:
            return (
                RelevantBeliefs(),
                RelevantNarratives(),
                RelevantGoals(),
                RelevantIdentityComponents(),
                RelevantBehavioralPatterns(),
                RelevantPredictions(),
                RelevantRealityObjects(),
            )
        beliefs = RelevantBeliefs(
            belief_ids=tuple(memories.get('belief_ids', ())),
            belief_statements=tuple(memories.get('belief_statements', ())),
            confidence_levels=tuple(memories.get('belief_confidences', ())),
            supporting_evidence=tuple(memories.get('belief_supporting', ())),
            contradicting_evidence=tuple(memories.get('belief_contradicting', ())),
        )
        narratives = RelevantNarratives(
            narrative_ids=tuple(memories.get('narrative_ids', ())),
            narrative_summaries=tuple(memories.get('narrative_summaries', ())),
            activation_levels=tuple(memories.get('narrative_activations', ())),
            coherence_scores=tuple(memories.get('narrative_coherences', ())),
        )
        goals = RelevantGoals(
            goal_ids=tuple(memories.get('goal_ids', ())),
            goal_descriptions=tuple(memories.get('goal_descriptions', ())),
            priority_levels=tuple(memories.get('goal_priorities', ())),
            progress_levels=tuple(memories.get('goal_progress', ())),
            blocked=tuple(memories.get('goal_blocked', ())),
        )
        identity = RelevantIdentityComponents(
            component_ids=tuple(memories.get('identity_ids', ())),
            component_descriptions=tuple(memories.get('identity_descriptions', ())),
            activation_levels=tuple(memories.get('identity_activations', ())),
            centrality_scores=tuple(memories.get('identity_centralities', ())),
        )
        behavioral = RelevantBehavioralPatterns(
            pattern_ids=tuple(memories.get('behavioral_ids', ())),
            pattern_descriptions=tuple(memories.get('behavioral_descriptions', ())),
            frequency_scores=tuple(memories.get('behavioral_frequencies', ())),
            consistency_scores=tuple(memories.get('behavioral_consistencies', ())),
            trigger_conditions=tuple(memories.get('behavioral_triggers', ())),
        )
        predictions = RelevantPredictions(
            prediction_ids=tuple(memories.get('prediction_ids', ())),
            prediction_statements=tuple(memories.get('prediction_statements', ())),
            confidence_levels=tuple(memories.get('prediction_confidences', ())),
            time_horizons=tuple(memories.get('prediction_horizons', ())),
        )
        reality = RelevantRealityObjects(
            reality_ids=tuple(memories.get('reality_ids', ())),
            descriptions=tuple(memories.get('reality_descriptions', ())),
            calibration_scores=tuple(memories.get('reality_calibrations', ())),
            evidence_strength=tuple(memories.get('reality_evidence', ())),
        )
        return beliefs, narratives, goals, identity, behavioral, predictions, reality

    # ------------------------------------------------------------------
    # Phase 8 — ContextAssembly
    # ------------------------------------------------------------------

    def _phase_context_assembly(
        self,
        raw_input: dict[str, Any],
        conversation_id: str,
        session_id: str,
        user_id: str,
        turn_number: int,
        intent: CurrentIntent,
        dialogue_state: CurrentDialogueState,
        working_mem: WorkingMemory,
        episodes: RelevantEpisodes,
        semantic: RelevantSemanticMemories,
        beliefs: RelevantBeliefs,
        narratives: RelevantNarratives,
        goals: RelevantGoals,
        identity: RelevantIdentityComponents,
        behavioral: RelevantBehavioralPatterns,
        predictions: RelevantPredictions,
        reality: RelevantRealityObjects,
    ) -> ContextObject:
        focus = PrimaryCognitiveFocus(
            focus_type=intent.intent_type,
            target_entities=working_mem.active_entities,
            attention_weight=intent.confidence,
        )

        context = ContextObject(
            context_identifier=ContextIdentifier(),
            conversation_identifier=ConversationIdentifier(
                conversation_id=conversation_id,
                session_id=session_id,
                user_id=user_id,
                turn_number=turn_number,
            ),
            current_intent=intent,
            current_dialogue_state=dialogue_state,
            primary_cognitive_focus=focus,
            working_memory=working_mem,
            relevant_episodes=episodes,
            relevant_semantic_memories=semantic,
            relevant_beliefs=beliefs,
            relevant_narratives=narratives,
            relevant_goals=goals,
            relevant_identity_components=identity,
            relevant_behavioral_patterns=behavioral,
            relevant_predictions=predictions,
            relevant_reality_objects=reality,
        )
        logger.debug('phase_8_assembled', context_id=context.context_identifier.id)
        return context

    # ------------------------------------------------------------------
    # Phase 9 — Inference
    # ------------------------------------------------------------------

    def _phase_inference(self, context: ContextObject) -> ContextObject:
        completeness = self._estimate_completeness(context)
        relevance = context.current_intent.confidence
        recency = 1.0
        coherence = self._estimate_coherence(context)
        overall = (completeness + relevance + recency + coherence) / 4.0

        confidence = ContextConfidence(
            completeness=completeness,
            relevance=relevance,
            recency=recency,
            coherence=coherence,
            overall=overall,
        )

        return ContextObject(
            context_identifier=context.context_identifier,
            conversation_identifier=context.conversation_identifier,
            current_intent=context.current_intent,
            current_dialogue_state=context.current_dialogue_state,
            primary_cognitive_focus=context.primary_cognitive_focus,
            working_memory=context.working_memory,
            relevant_episodes=context.relevant_episodes,
            relevant_semantic_memories=context.relevant_semantic_memories,
            relevant_beliefs=context.relevant_beliefs,
            relevant_narratives=context.relevant_narratives,
            relevant_goals=context.relevant_goals,
            relevant_identity_components=context.relevant_identity_components,
            relevant_behavioral_patterns=context.relevant_behavioral_patterns,
            relevant_predictions=context.relevant_predictions,
            relevant_reality_objects=context.relevant_reality_objects,
            context_confidence=confidence,
            version_metadata=context.version_metadata,
        )

    def _estimate_completeness(self, context: ContextObject) -> float:
        filled = 0
        total = 8
        if context.relevant_episodes.episode_ids:
            filled += 1
        if context.relevant_semantic_memories.memory_ids:
            filled += 1
        if context.relevant_beliefs.belief_ids:
            filled += 1
        if context.relevant_narratives.narrative_ids:
            filled += 1
        if context.relevant_goals.goal_ids:
            filled += 1
        if context.relevant_identity_components.component_ids:
            filled += 1
        if context.relevant_behavioral_patterns.pattern_ids:
            filled += 1
        if context.relevant_predictions.prediction_ids:
            filled += 1
        return filled / total

    def _estimate_coherence(self, context: ContextObject) -> float:
        narrative_count = len(context.relevant_narratives.narrative_ids)
        if narrative_count <= 1:
            return 0.8
        avg_coherence = 0.0
        scores = context.relevant_narratives.coherence_scores
        if scores:
            avg_coherence = sum(scores) / len(scores)
        else:
            avg_coherence = 0.5
        return avg_coherence
