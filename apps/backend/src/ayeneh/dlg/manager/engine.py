"""DLG-01 Dialogue Manager engine.

Transforms cognition into interaction through a 9-phase canonical pipeline:
User Input -> Intent Detection -> Working Memory Construction -> Inference ->
Dialogue Planning -> Response Construction -> Self-Evaluation ->
Response Delivery -> Memory Update.

Specification: DLG-01 Dialogue Manager.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from ayeneh.dlg.manager.evaluation import SelfEvaluator
from ayeneh.dlg.manager.types import (
    ActiveWorkingMemory,
    Confidence,
    ConversationIdentifier,
    CurrentCognitiveFocus,
    DetectedIntent,
    DialogueIdentifier,
    DialogueMode,
    DialogueObjective,
    DialoguePlan,
    DialogueResponse,
    DialogueGranularity,
    DialogueObject,
    EvaluationResult,
    FollowUpOpportunity,
    FollowUpOpportunities,
    PrimaryObjective,
    ReferencedEvidence,
    ReferencedMemories,
    ResponseStrategy,
    Uncertainty,
    VersionMetadata,
)

logger = structlog.get_logger(__name__)

# Pipeline phase names for logging
PIPELINE_PHASES: list[str] = [
    'user_input',
    'intent_detection',
    'working_memory_construction',
    'inference',
    'dialogue_planning',
    'response_construction',
    'self_evaluation',
    'response_delivery',
    'memory_update',
]

# Intent detection keyword maps
_INTENT_KEYWORDS: dict[str, list[str]] = {
    'information_seeking': [
        'what', 'how', 'explain', 'tell me', 'describe', 'define',
    ],
    'reflection': [
        'i notice', 'i think', 'i feel', 'reflecting', 'realize',
    ],
    'planning': [
        'plan', 'strategy', 'approach', 'roadmap', 'steps',
    ],
    'debugging': [
        'error', 'bug', 'broken', 'fix', 'issue', 'problem',
    ],
    'decision_support': [
        'should i', 'which', 'decide', 'choose', 'compare',
    ],
    'learning': [
        'teach', 'learn', 'understand', 'concept', 'study',
    ],
    'emotional_processing': [
        'feel', 'emotion', 'anxious', 'stressed', 'happy', 'sad',
    ],
    'narrative_exploration': [
        'story', 'narrative', 'journey', 'experience', 'happened',
    ],
    'identity_exploration': [
        'who am i', 'identity', 'values', 'beliefs', 'purpose',
    ],
    'reality_calibration': [
        'is it true', 'actually', 'really', 'fact', 'evidence',
    ],
    'meta_cognitive_observation': [
        'thinking about thinking', 'metacognition', 'awareness', 'observe my',
    ],
}

# Mode selection keyword hints
_MODE_HINTS: dict[str, list[str]] = {
    'teacher': ['teach', 'explain', 'learn', 'concept'],
    'socratic_guide': ['think', 'consider', 'what if', 'why'],
    'reflective_mirror': ['notice', 'feel', 'pattern', 'always'],
    'technical_architect': ['architecture', 'design', 'system', 'code'],
    'project_planner': ['plan', 'roadmap', 'timeline', 'milestone'],
    'reality_calibration_assistant': ['true', 'real', 'fact', 'evidence'],
    'analytical_reviewer': ['review', 'analyze', 'evaluate', 'assess'],
    'research_partner': ['research', 'study', 'investigate', 'hypothesis'],
    'silent_observer': [],
}

# Granularity keywords
_GRANULARITY_HINTS: dict[str, list[str]] = {
    'brief': ['quick', 'short', 'brief', 'summary'],
    'structured': [],
    'deep_analysis': ['deep', 'detailed', 'comprehensive', 'thorough'],
    'longitudinal_reflection': ['over time', 'history', 'evolution', 'journey'],
    'architectural_review': ['architecture', 'design', 'structure', 'system'],
    'scientific_discussion': ['research', 'evidence', 'data', 'study'],
}


class DialogueManager:
    """Executive layer that transforms cognition into interaction.

    Every user-facing response shall pass through this 9-phase pipeline.
    No response bypasses the Dialogue Manager.
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._evaluator = SelfEvaluator()
        self._turn_count: int = 0
        self._conversation_history: list[dict[str, Any]] = []

    def process(
        self,
        user_input: str,
        context: dict[str, Any] | None = None,
    ) -> DialogueObject:
        """Run the full 9-phase dialogue pipeline."""
        ctx = context or {}
        start = time.monotonic()

        logger.info(
            "dlg01_pipeline_start",
            input_length=len(user_input),
            turn=self._turn_count,
        )

        # Phase 1: User Input
        normalized_input = self._process_user_input(user_input, ctx)

        # Phase 2: Intent Detection
        detected_intent = self._detect_intent(normalized_input, ctx)

        # Phase 3: Working Memory Construction
        working_memory = self._construct_working_memory(
            normalized_input, detected_intent, ctx,
        )

        # Phase 4: Inference
        cognitive_focus, referenced_memories, referenced_evidence = (
            self._run_inference(normalized_input, detected_intent, working_memory, ctx)
        )

        # Phase 5: Dialogue Planning
        dialogue_plan, primary_objective, response_strategy = (
            self._plan_dialogue(
                normalized_input, detected_intent, cognitive_focus,
                working_memory, ctx,
            )
        )

        # Phase 6: Response Construction
        dialogue_response = self._construct_response(
            normalized_input, dialogue_plan, detected_intent,
            cognitive_focus, working_memory, referenced_evidence, ctx,
        )

        # Phase 7: Self-Evaluation
        evaluation_result, dialogue_response = self._self_evaluate(
            dialogue_response, dialogue_plan, ctx,
        )

        # Phase 8: Response Delivery
        delivered_response = self._deliver_response(
            dialogue_response, evaluation_result, ctx,
        )

        # Phase 9: Memory Update
        self._update_memory(
            normalized_input, detected_intent, dialogue_plan,
            delivered_response, ctx,
        )

        # Build the final DialogueObject
        dialogue_object = self._build_dialogue_object(
            detected_intent=detected_intent,
            cognitive_focus=cognitive_focus,
            working_memory=working_memory,
            primary_objective=primary_objective,
            response_strategy=response_strategy,
            referenced_memories=referenced_memories,
            referenced_evidence=referenced_evidence,
            dialogue_plan=dialogue_plan,
            evaluation_result=evaluation_result,
        )

        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "dlg01_pipeline_complete",
            intent=detected_intent.intent_type,
            confidence=round(dialogue_object.confidence.overall, 3),
            evaluation_quality=round(evaluation_result.overall_quality, 3),
            latency_ms=round(elapsed_ms, 2),
        )

        return dialogue_object

    # ------------------------------------------------------------------
    # Phase 1: User Input Processing
    # ------------------------------------------------------------------

    def _process_user_input(
        self, user_input: str, ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize and preprocess user input."""
        normalized = user_input.strip()
        return {
            'raw_input': user_input,
            'normalized_input': normalized,
            'input_length': len(normalized),
            'word_count': len(normalized.split()),
            'turn_number': self._turn_count,
            'conversation_context': ctx,
        }

    # ------------------------------------------------------------------
    # Phase 2: Intent Detection
    # ------------------------------------------------------------------

    def _detect_intent(
        self,
        processed_input: dict[str, Any],
        ctx: dict[str, Any],
    ) -> DetectedIntent:
        """Classify conversational intent from user input."""
        text = processed_input['normalized_input'].lower()
        scores: dict[str, float] = {}

        for intent, keywords in _INTENT_KEYWORDS.items():
            matches = [kw for kw in keywords if kw in text]
            if matches:
                scores[intent] = min(1.0, 0.4 + len(matches) * 0.2)

        if not scores:
            scores['information_seeking'] = 0.3

        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_intents[0]
        secondary = tuple(s[0] for s in sorted_intents[1:3])

        return DetectedIntent(
            intent_type=primary[0],
            confidence=primary[1],
            description=f"Detected {primary[0]} intent",
            parameters={},
            secondary_intents=secondary,
        )

    # ------------------------------------------------------------------
    # Phase 3: Working Memory Construction
    # ------------------------------------------------------------------

    def _construct_working_memory(
        self,
        processed_input: dict[str, Any],
        intent: DetectedIntent,
        ctx: dict[str, Any],
    ) -> ActiveWorkingMemory:
        """Construct active working memory for the current turn."""
        history = ctx.get('recent_facts', [])
        entities = ctx.get('active_entities', [])
        goals = ctx.get('active_goals', [])

        recent_facts = tuple(history[-5:]) if history else ()
        active_entities = tuple(entities[-10:]) if entities else ()
        active_goals = tuple(goals[-5:]) if goals else ()

        capacity = len(recent_facts) + len(active_entities) + len(active_goals)
        capacity_used = min(1.0, capacity / 20.0)

        return ActiveWorkingMemory(
            active_entities=active_entities,
            active_relations=(),
            recent_facts=recent_facts,
            active_goals=active_goals,
            emotional_state=ctx.get('emotional_state', 'neutral'),
            capacity_used=capacity_used,
        )

    # ------------------------------------------------------------------
    # Phase 4: Inference
    # ------------------------------------------------------------------

    def _run_inference(
        self,
        processed_input: dict[str, Any],
        intent: DetectedIntent,
        working_memory: ActiveWorkingMemory,
        ctx: dict[str, Any],
    ) -> tuple[CurrentCognitiveFocus, ReferencedMemories, ReferencedEvidence]:
        """Run inference to determine focus, recall memories, gather evidence."""
        focus_type = self._determine_cognitive_focus(intent)
        focus = CurrentCognitiveFocus(
            focus_type=focus_type,
            target_entities=working_memory.active_entities,
            attention_weight=min(1.0, intent.confidence + 0.2),
            reasoning_mode=self._select_reasoning_mode(intent),
        )

        referenced_memories = ReferencedMemories(
            memory_ids=ctx.get('relevant_memory_ids', ()),
            memory_types=ctx.get('relevant_memory_types', ()),
            relevance_scores=ctx.get('relevance_scores', ()),
            retrieval_reasons=ctx.get('retrieval_reasons', ()),
        )

        referenced_evidence = ReferencedEvidence(
            evidence_ids=ctx.get('evidence_ids', ()),
            evidence_types=ctx.get('evidence_types', ()),
            strength_scores=ctx.get('evidence_strength', ()),
            source_references=ctx.get('evidence_sources', ()),
        )

        return focus, referenced_memories, referenced_evidence

    def _determine_cognitive_focus(self, intent: DetectedIntent) -> str:
        """Map intent to a cognitive focus type."""
        focus_map: dict[str, str] = {
            'information_seeking': 'factual_recall',
            'reflection': 'meta_cognitive_observation',
            'planning': 'strategic_planning',
            'debugging': 'causal_reasoning',
            'decision_support': 'causal_reasoning',
            'learning': 'factual_recall',
            'emotional_processing': 'emotional_processing',
            'narrative_exploration': 'narrative_construction',
            'identity_exploration': 'identity_exploration',
            'reality_calibration': 'reality_calibration',
            'meta_cognitive_observation': 'meta_cognitive_obspection',
        }
        return focus_map.get(intent.intent_type, 'factual_recall')

    def _select_reasoning_mode(self, intent: DetectedIntent) -> str:
        """Select reasoning mode based on intent."""
        mode_map: dict[str, str] = {
            'information_seeking': 'deductive',
            'reflection': 'inductive',
            'planning': 'abductive',
            'debugging': 'deductive',
            'decision_support': 'comparative',
            'learning': 'explanatory',
            'emotional_processing': 'empathic',
            'narrative_exploration': 'interpretive',
            'identity_exploration': 'exploratory',
            'reality_calibration': 'evidential',
            'meta_cognitive_observation': 'meta_cognitive',
        }
        return mode_map.get(intent.intent_type, 'default')

    # ------------------------------------------------------------------
    # Phase 5: Dialogue Planning
    # ------------------------------------------------------------------

    def _plan_dialogue(
        self,
        processed_input: dict[str, Any],
        intent: DetectedIntent,
        focus: CurrentCognitiveFocus,
        working_memory: ActiveWorkingMemory,
        ctx: dict[str, Any],
    ) -> tuple[DialoguePlan, PrimaryObjective, ResponseStrategy]:
        """Construct an explicit dialogue plan before response generation."""
        objective_type = self._map_intent_to_objective(intent)
        mode = self._select_dialogue_mode(intent, processed_input)
        granularity = self._select_granularity(intent, processed_input)

        primary_objective = PrimaryObjective(
            objective_type=objective_type,
            description=f"Optimize for {objective_type}",
            priority=0.8 if intent.confidence > 0.6 else 0.5,
            expected_outcome=f"User benefits from {objective_type} response",
        )

        response_strategy = ResponseStrategy(
            strategy_type=self._select_strategy_type(intent),
            granularity=granularity,
            mode=mode,
            information_budget=self._estimate_information_budget(
                intent, processed_input,
            ),
            clarification_threshold=0.3,
        )

        plan = DialoguePlan(
            primary_objective=objective_type,
            secondary_objectives=tuple(
                s for s in intent.secondary_intents
            ),
            required_memories=working_memory.active_entities,
            required_reasoning=(focus.reasoning_mode,),
            required_evidence=(),
            expected_user_benefit=f"Improved understanding through {objective_type}",
            cognitive_load_estimate=self._estimate_cognitive_load(
                processed_input, granularity,
            ),
        )

        return plan, primary_objective, response_strategy

    def _map_intent_to_objective(self, intent: DetectedIntent) -> str:
        """Map intent type to dialogue objective."""
        mapping: dict[str, str] = {
            'information_seeking': DialogueObjective.ANSWER_QUESTION.value,
            'reflection': DialogueObjective.SUPPORT_REFLECTION.value,
            'planning': DialogueObjective.PLAN_ACTION.value,
            'debugging': DialogueObjective.ANSWER_QUESTION.value,
            'decision_support': DialogueObjective.ANSWER_QUESTION.value,
            'learning': DialogueObjective.SUMMARIZE_KNOWLEDGE.value,
            'emotional_processing': DialogueObjective.SUPPORT_REFLECTION.value,
            'narrative_exploration': DialogueObjective.EXPLORE_UNCERTAINTY.value,
            'identity_exploration': DialogueObjective.GENERATE_INSIGHT.value,
            'reality_calibration': DialogueObjective.CALIBRATE_REALITY.value,
            'meta_cognitive_observation': DialogueObjective.GENERATE_INSIGHT.value,
        }
        return mapping.get(intent.intent_type, DialogueObjective.ANSWER_QUESTION.value)

    def _select_dialogue_mode(
        self, intent: DetectedIntent, processed_input: dict[str, Any],
    ) -> str:
        """Select dialogue mode based on intent and input."""
        text = processed_input.get('normalized_input', '').lower()
        for mode, hints in _MODE_HINTS.items():
            if any(h in text for h in hints):
                return mode

        intent_mode_map: dict[str, str] = {
            'information_seeking': 'teacher',
            'reflection': 'reflective_mirror',
            'planning': 'project_planner',
            'debugging': 'technical_architect',
            'decision_support': 'socratic_guide',
            'identity_exploration': 'socratic_guide',
            'reality_calibration': 'reality_calibration_assistant',
        }
        return intent_mode_map.get(intent.intent_type, 'teacher')

    def _select_granularity(
        self, intent: DetectedIntent, processed_input: dict[str, Any],
    ) -> str:
        """Select response granularity."""
        text = processed_input.get('normalized_input', '').lower()
        for level, hints in _GRANULARITY_HINTS.items():
            if any(h in text for h in hints):
                return level
        return DialogueGranularity.STRUCTURED.value

    def _select_strategy_type(self, intent: DetectedIntent) -> str:
        """Select response strategy type based on intent."""
        strategy_map: dict[str, str] = {
            'information_seeking': 'direct_answer',
            'reflection': 'reflective_question',
            'planning': 'progressive_disclosure',
            'debugging': 'direct_answer',
            'decision_support': 'socratic_inquiry',
            'learning': 'progressive_disclosure',
            'emotional_processing': 'empathic_reflection',
            'narrative_exploration': 'narrative_mirror',
            'identity_exploration': 'socratic_inquiry',
            'reality_calibration': 'reality_check',
            'meta_cognitive_observation': 'reflective_question',
        }
        return strategy_map.get(intent.intent_type, 'direct_answer')

    def _estimate_information_budget(
        self, intent: DetectedIntent, processed_input: dict[str, Any],
    ) -> str:
        """Estimate cognitive information budget for the response."""
        word_count = processed_input.get('word_count', 0)
        if word_count < 5:
            return 'minimal'
        if word_count < 15:
            return 'focused'
        if word_count < 40:
            return 'moderate'
        return 'comprehensive'

    def _estimate_cognitive_load(
        self, processed_input: dict[str, Any], granularity: str,
    ) -> float:
        """Estimate the cognitive load of the planned response."""
        base_load = 0.3
        word_count = processed_input.get('word_count', 0)
        length_factor = min(0.3, word_count / 100.0)
        granularity_factor = {
            'brief': 0.0,
            'structured': 0.1,
            'deep_analysis': 0.3,
            'longitudinal_reflection': 0.25,
            'architectural_review': 0.35,
            'scientific_discussion': 0.3,
        }.get(granularity, 0.1)
        return min(1.0, base_load + length_factor + granularity_factor)

    # ------------------------------------------------------------------
    # Phase 6: Response Construction
    # ------------------------------------------------------------------

    def _construct_response(
        self,
        processed_input: dict[str, Any],
        plan: DialoguePlan,
        intent: DetectedIntent,
        focus: CurrentCognitiveFocus,
        working_memory: ActiveWorkingMemory,
        evidence: ReferencedEvidence,
        ctx: dict[str, Any],
    ) -> DialogueResponse:
        """Construct the dialogue response based on the plan."""
        response_content = ctx.get('generated_response', '')
        uncertainty_markers: list[str] = []

        if intent.confidence < 0.5:
            uncertainty_markers.append('low_intent_confidence')
        if not evidence.evidence_ids:
            uncertainty_markers.append('limited_evidence')
        if working_memory.capacity_used > 0.8:
            uncertainty_markers.append('high_cognitive_load')

        return DialogueResponse(
            content=response_content,
            response_type='text',
            granularity=plan.estimated_response_length or 'moderate',
            emotional_tone=working_memory.emotional_state or 'neutral',
            explicit_uncertainty_markers=tuple(uncertainty_markers),
        )

    # ------------------------------------------------------------------
    # Phase 7: Self-Evaluation
    # ------------------------------------------------------------------

    def _self_evaluate(
        self,
        response: DialogueResponse,
        plan: DialoguePlan,
        ctx: dict[str, Any],
    ) -> tuple[EvaluationResult, DialogueResponse]:
        """Evaluate response quality before delivery."""
        evaluation = self._evaluator.evaluate(response, plan)

        if evaluation.revision_needed:
            logger.info(
                "dlg01_self_evaluation_revision",
                quality=round(evaluation.overall_quality, 3),
                notes=evaluation.revision_notes,
            )
            response = self._revise_response(response, evaluation)

        return evaluation, response

    def _revise_response(
        self, response: DialogueResponse, evaluation: EvaluationResult,
    ) -> DialogueResponse:
        """Revise a response that failed self-evaluation."""
        revised_content = response.content
        if not revised_content:
            revised_content = ""

        return DialogueResponse(
            content=revised_content,
            response_type=response.response_type,
            granularity=response.granularity,
            emotional_tone=response.emotional_tone,
            explicit_uncertainty_markers=response.explicit_uncertainty_markers,
            evidence_citations=response.evidence_citations,
            questions_raised=response.questions_raised,
            action_suggestions=response.action_suggestions,
        )

    # ------------------------------------------------------------------
    # Phase 8: Response Delivery
    # ------------------------------------------------------------------

    def _deliver_response(
        self,
        response: DialogueResponse,
        evaluation: EvaluationResult,
        ctx: dict[str, Any],
    ) -> DialogueResponse:
        """Finalize and deliver the response."""
        self._turn_count += 1
        logger.info(
            "dlg01_response_delivered",
            turn=self._turn_count,
            quality=round(evaluation.overall_quality, 3),
            passes=evaluation.passes_threshold,
        )
        return response

    # ------------------------------------------------------------------
    # Phase 9: Memory Update
    # ------------------------------------------------------------------

    def _update_memory(
        self,
        processed_input: dict[str, Any],
        intent: DetectedIntent,
        plan: DialoguePlan,
        response: DialogueResponse,
        ctx: dict[str, Any],
    ) -> None:
        """Update conversation memory with the interaction."""
        self._conversation_history.append({
            'turn': self._turn_count,
            'user_input': processed_input.get('raw_input', ''),
            'intent': intent.intent_type,
            'objective': plan.primary_objective,
            'response_preview': response.content[:100] if response.content else '',
        })
        logger.info(
            "dlg01_memory_updated",
            turn=self._turn_count,
            history_length=len(self._conversation_history),
        )

    # ------------------------------------------------------------------
    # DialogueObject construction
    # ------------------------------------------------------------------

    def _build_dialogue_object(
        self,
        detected_intent: DetectedIntent,
        cognitive_focus: CurrentCognitiveFocus,
        working_memory: ActiveWorkingMemory,
        primary_objective: PrimaryObjective,
        response_strategy: ResponseStrategy,
        referenced_memories: ReferencedMemories,
        referenced_evidence: ReferencedEvidence,
        dialogue_plan: DialoguePlan,
        evaluation_result: EvaluationResult,
    ) -> DialogueObject:
        """Assemble the final DialogueObject from pipeline outputs."""
        confidence = Confidence(
            overall=evaluation_result.overall_quality,
            intent_confidence=detected_intent.confidence,
            evidence_confidence=(
                sum(referenced_evidence.strength_scores)
                / len(referenced_evidence.strength_scores)
                if referenced_evidence.strength_scores else 0.0
            ),
            strategy_confidence=response_strategy.clarification_threshold,
        )

        uncertainty = Uncertainty(
            identified_gaps=tuple(dialogue_plan.potential_misunderstandings),
            unresolved_questions=dialogue_plan.follow_up_opportunities,
        )

        follow_ups = FollowUpOpportunities(
            opportunities=tuple(
                FollowUpOpportunity(
                    description=fu,
                    cognitive_purpose='continue_exploration',
                    priority_score=0.5,
                )
                for fu in dialogue_plan.follow_up_opportunities
            ),
        )

        return DialogueObject(
            dialogue_identifier=DialogueIdentifier(),
            conversation_identifier=ConversationIdentifier(
                turn_number=self._turn_count,
            ),
            detected_intent=detected_intent,
            current_cognitive_focus=cognitive_focus,
            active_working_memory=working_memory,
            primary_objective=primary_objective,
            response_strategy=response_strategy,
            confidence=confidence,
            uncertainty=uncertainty,
            referenced_memories=referenced_memories,
            referenced_evidence=referenced_evidence,
            follow_up_opportunities=follow_ups,
            version_metadata=VersionMetadata(),
        )
