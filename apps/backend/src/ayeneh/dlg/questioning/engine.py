"""DLG-05 Question Generation engine.

8-phase pipeline for generating Socratic questions:

1. ContextObject — ingest context
2. KnowledgeGaps — identify information gaps
3. UncertaintyAnalysis — analyse uncertainties
4. ObjectiveSelection — select questioning objective
5. QuestionConstruction — construct the question
6. TimingEvaluation — evaluate optimal timing
7. DialoguePlanning — plan dialogue integration
8. QuestionDelivery — prepare question output
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.dlg.questioning.socratic import SocraticQuestionProgression
from ayeneh.dlg.questioning.types import (
    QUESTION_CATEGORIES,
    QUESTION_OBJECTIVES,
    AssociatedCognitiveObjects,
    ExpectedInformationGain,
    PrimaryObjective,
    QuestionIdentifier,
    QuestionObject,
    QuestionType,
    RelevantEvidence,
    TargetUncertainty,
    VersionMetadata,
)

logger = structlog.get_logger(__name__)


class QuestionGenerationEngine:
    """Generates Socratic questions through an 8-phase pipeline (DLG-05)."""

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._socratic = SocraticQuestionProgression()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        context: Any,
        conversation_history: list[Any] | None = None,
        existing_knowledge: dict[str, Any] | None = None,
    ) -> QuestionObject | None:
        """Run the full 8-phase question generation pipeline."""
        logger.info('question_pipeline_start')

        # Phase 1 — ContextObject
        enriched_ctx = self._phase_context_object(context)

        # Phase 2 — KnowledgeGaps
        gaps = self._phase_knowledge_gaps(enriched_ctx, existing_knowledge)

        # Phase 3 — UncertaintyAnalysis
        uncertainties = self._phase_uncertainty_analysis(enriched_ctx, gaps)

        # Phase 4 — ObjectiveSelection
        objective = self._phase_objective_selection(uncertainties, enriched_ctx)

        # Phase 5 — QuestionConstruction
        question = self._phase_question_construction(objective, enriched_ctx, gaps)

        # Phase 6 — TimingEvaluation
        timed = self._phase_timing_evaluation(question, enriched_ctx)

        # Phase 7 — DialoguePlanning
        planned = self._phase_dialogue_planning(timed, enriched_ctx)

        # Phase 8 — QuestionDelivery
        result = self._phase_question_delivery(planned)

        logger.info('question_pipeline_end', has_question=result is not None)
        return result

    # ------------------------------------------------------------------
    # Phase 1 — ContextObject
    # ------------------------------------------------------------------

    def _phase_context_object(self, context: Any) -> dict[str, Any]:
        ctx: dict[str, Any] = {}
        if isinstance(context, dict):
            ctx.update(context)
        else:
            ctx['raw_context'] = context
        ctx.setdefault('analysis_timestamp', uuid.uuid4().hex)
        logger.debug('phase_1_context')
        return ctx

    # ------------------------------------------------------------------
    # Phase 2 — KnowledgeGaps
    # ------------------------------------------------------------------

    def _phase_knowledge_gaps(
        self, ctx: dict[str, Any], knowledge: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        gaps: list[dict[str, Any]] = []
        known = knowledge or {}

        beliefs = ctx.get('relevant_beliefs', {})
        if isinstance(beliefs, dict):
            for bid in beliefs.get('belief_ids', []):
                if bid not in known:
                    gaps.append({
                        'gap_id': f'gap_belief_{bid}',
                        'type': 'belief',
                        'entity_id': bid,
                        'importance': 0.7,
                    })

        goals = ctx.get('relevant_goals', {})
        if isinstance(goals, dict):
            goal_ids = goals.get('goal_ids', [])
            goal_progress = goals.get('goal_progress', [])
            for i, gid in enumerate(goal_ids):
                progress = goal_progress[i] if i < len(goal_progress) else 0.0
                if progress < 0.3:
                    gaps.append({
                        'gap_id': f'gap_goal_{gid}',
                        'type': 'goal_progress',
                        'entity_id': gid,
                        'importance': 0.8,
                    })

        if not gaps:
            gaps.append({
                'gap_id': f'gap_general_{uuid.uuid4().hex[:8]}',
                'type': 'general',
                'entity_id': '',
                'importance': 0.4,
            })

        logger.debug('phase_2_gaps', count=len(gaps))
        return gaps

    # ------------------------------------------------------------------
    # Phase 3 — UncertaintyAnalysis
    # ------------------------------------------------------------------

    def _phase_uncertainty_analysis(
        self, ctx: dict[str, Any], gaps: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        uncertainties: list[dict[str, Any]] = []
        for gap in gaps:
            uncertainties.append({
                'uncertainty_id': f'unc_{gap["gap_id"]}',
                'type': gap.get('type', 'unknown'),
                'entity_id': gap.get('entity_id', ''),
                'current_confidence': 1.0 - gap.get('importance', 0.5),
                'target_confidence': 0.8,
                'description': f"Uncertainty about {gap.get('type', 'unknown')}",
            })

        intent = ctx.get('current_intent', {})
        if isinstance(intent, dict):
            intent_conf = intent.get('confidence', 0.5)
            if intent_conf < 0.5:
                uncertainties.append({
                    'uncertainty_id': f'unc_intent_{uuid.uuid4().hex[:8]}',
                    'type': 'intent_clarity',
                    'entity_id': '',
                    'current_confidence': intent_conf,
                    'target_confidence': 0.8,
                    'description': 'Low confidence in detected intent',
                })

        logger.debug('phase_3_uncertainties', count=len(uncertainties))
        return uncertainties

    # ------------------------------------------------------------------
    # Phase 4 — ObjectiveSelection
    # ------------------------------------------------------------------

    def _phase_objective_selection(
        self, uncertainties: list[dict[str, Any]], ctx: dict[str, Any],
    ) -> str:
        if not uncertainties:
            return 'expand_reflection'

        type_counts: dict[str, int] = {}
        for u in uncertainties:
            t = u.get('type', 'unknown')
            type_counts[t] = type_counts.get(t, 0) + 1

        most_common = max(type_counts, key=lambda k: type_counts[k])

        objective_map: dict[str, str] = {
            'belief': 'collect_evidence',
            'goal_progress': 'support_planning',
            'intent_clarity': 'clarify_ambiguity',
            'general': 'expand_reflection',
        }
        return objective_map.get(most_common, 'collect_evidence')

    # ------------------------------------------------------------------
    # Phase 5 — QuestionConstruction
    # ------------------------------------------------------------------

    def _phase_question_construction(
        self,
        objective: str,
        ctx: dict[str, Any],
        gaps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        socratic_step = self._socratic.get_current_step(ctx)
        question_text = self._build_question_text(objective, gaps, ctx)

        question_obj = QuestionObject(
            question_identifier=QuestionIdentifier(),
            question_text=question_text,
            question_type=QuestionType(
                primary_type='open_ended',
                socratic_step=socratic_step,
            ),
            primary_objective=PrimaryObjective(
                objective=objective,
                rationale=f'Address {objective} based on detected gaps',
            ),
            target_uncertainty=TargetUncertainty(
                uncertainty_id=gaps[0].get('gap_id', '') if gaps else '',
                current_confidence=0.3,
                target_confidence=0.7,
            ),
            expected_information_gain=ExpectedInformationGain(
                clarity_gain=0.5,
                evidence_gain=0.4,
                insight_gain=0.3,
                overall_gain=0.4,
            ),
            estimated_cognitive_load=0.4,
            estimated_reflection_value=0.6,
            confidence=0.6,
        )

        return {'question': question_obj, 'gaps': gaps, 'objective': objective}

    def _build_question_text(
        self, objective: str, gaps: list[dict[str, Any]], ctx: dict[str, Any],
    ) -> str:
        templates: dict[str, str] = {
            'clarify_ambiguity': 'Can you tell me more about what you mean?',
            'collect_evidence': 'What evidence supports your perspective on this?',
            'differentiate_observation_from_interpretation': 'Is this something you observed directly, or an interpretation?',
            'explore_behavioral_patterns': 'Have you noticed this pattern before in similar situations?',
            'reveal_hidden_assumptions': 'What assumptions might be underlying your thinking here?',
            'challenge_narratives': 'Is there another way to look at this story?',
            'understand_identity': 'How does this relate to who you see yourself as?',
            'support_planning': 'What would be the first step toward your goal?',
            'resolve_contradictions': 'I notice some tension between these points — how do you see it?',
            'generate_hypotheses': 'What do you think might be causing this?',
            'expand_reflection': 'What stands out to you most in this situation?',
        }
        return templates.get(objective, 'What are your thoughts on this?')

    # ------------------------------------------------------------------
    # Phase 6 — TimingEvaluation
    # ------------------------------------------------------------------

    def _phase_timing_evaluation(
        self, question_data: dict[str, Any], ctx: dict[str, Any],
    ) -> dict[str, Any]:
        engagement = ctx.get('engagement_level', 0.5)
        load = question_data['question'].estimated_cognitive_load
        timing_score = engagement * 0.6 + (1.0 - load) * 0.4
        question_data['timing_score'] = timing_score
        question_data['should_ask'] = timing_score > 0.25
        logger.debug('phase_6_timing', score=timing_score)
        return question_data

    # ------------------------------------------------------------------
    # Phase 7 — DialoguePlanning
    # ------------------------------------------------------------------

    def _phase_dialogue_planning(
        self, question_data: dict[str, Any], ctx: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not question_data.get('should_ask', False):
            return None
        question_data['dialogue_plan'] = {
            'position': 'after_response',
            'tone': 'curious',
            'framing': 'supportive',
        }
        return question_data

    # ------------------------------------------------------------------
    # Phase 8 — QuestionDelivery
    # ------------------------------------------------------------------

    def _phase_question_delivery(
        self, planned: dict[str, Any] | None,
    ) -> QuestionObject | None:
        if planned is None:
            return None
        question: QuestionObject = planned['question']
        logger.debug('phase_8_delivered', question_id=question.question_identifier.id)
        return question
