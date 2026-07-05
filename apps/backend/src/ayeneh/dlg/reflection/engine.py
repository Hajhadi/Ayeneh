"""DLG-04 Reflection Timing engine.

8-phase pipeline for detecting and timing reflection opportunities:

1. ContextObject — ingest context
2. ConversationState — assess dialogue state
3. CognitiveReadinessEstimation — estimate user readiness
4. OpportunityDetection — find reflection opportunities
5. InterventionSelection — select intervention strategy
6. TimingEvaluation — evaluate optimal timing
7. DialoguePlanning — plan dialogue delivery
8. ReflectionDelivery — prepare reflection output
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.dlg.reflection.trigger import ReflectionTriggerDetector
from ayeneh.dlg.reflection.types import (
    REFLECTION_CATEGORIES,
    REFLECTION_TRIGGERS,
    DetectedPattern,
    EstimatedBenefit,
    EstimatedReadiness,
    EstimatedRisk,
    OpportunityIdentifier,
    ReflectionEvidence,
    ReflectionIntensity,
    ReflectionOpportunity,
)

logger = structlog.get_logger(__name__)


class ReflectionTimingEngine:
    """Detects and times reflection opportunities (DLG-04)."""

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._trigger_detector = ReflectionTriggerDetector()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        context: Any,
        conversation_history: list[Any] | None = None,
        behavioral_patterns: list[Any] | None = None,
    ) -> ReflectionOpportunity | None:
        """Run the full 8-phase reflection timing pipeline."""
        logger.info('reflection_pipeline_start')

        # Phase 1 — ContextObject
        enriched_ctx = self._phase_context_object(context)

        # Phase 2 — ConversationState
        conv_state = self._phase_conversation_state(enriched_ctx)

        # Phase 3 — CognitiveReadinessEstimation
        readiness = self._phase_cognitive_readiness(enriched_ctx, conv_state)

        # Phase 4 — OpportunityDetection
        opportunities = self._phase_opportunity_detection(
            enriched_ctx, conversation_history, behavioral_patterns,
        )

        # Phase 5 — InterventionSelection
        selected = self._phase_intervention_selection(opportunities, readiness)

        # Phase 6 — TimingEvaluation
        timed = self._phase_timing_evaluation(selected, conv_state)

        # Phase 7 — DialoguePlanning
        planned = self._phase_dialogue_planning(timed, readiness)

        # Phase 8 — ReflectionDelivery
        result = self._phase_reflection_delivery(planned)

        logger.info(
            'reflection_pipeline_end',
            has_opportunity=result is not None,
        )
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
    # Phase 2 — ConversationState
    # ------------------------------------------------------------------

    def _phase_conversation_state(self, ctx: dict[str, Any]) -> dict[str, Any]:
        state: dict[str, Any] = {
            'depth': ctx.get('depth', 0),
            'emotional_valence': ctx.get('emotional_valence', 0.0),
            'engagement_level': ctx.get('engagement_level', 0.5),
            'phase': ctx.get('phase', 'unknown'),
        }
        logger.debug('phase_2_conversation_state')
        return state

    # ------------------------------------------------------------------
    # Phase 3 — CognitiveReadinessEstimation
    # ------------------------------------------------------------------

    def _phase_cognitive_readiness(
        self, ctx: dict[str, Any], conv_state: dict[str, Any],
    ) -> EstimatedReadiness:
        engagement = conv_state.get('engagement_level', 0.5)
        emotional = abs(conv_state.get('emotional_valence', 0.0))
        defensiveness = max(0.0, emotional - 0.5) * 2.0
        readiness_score = max(0.0, min(1.0, engagement - defensiveness * 0.3))

        readiness = EstimatedReadiness(
            cognitive_load=ctx.get('cognitive_load', 0.3),
            emotional_stability=max(0.0, 1.0 - emotional),
            openness_score=engagement,
            defensiveness_level=defensiveness,
            overall_readiness=readiness_score,
        )
        logger.debug('phase_3_readiness', score=readiness.overall_readiness)
        return readiness

    # ------------------------------------------------------------------
    # Phase 4 — OpportunityDetection
    # ------------------------------------------------------------------

    def _phase_opportunity_detection(
        self,
        ctx: dict[str, Any],
        history: list[Any] | None,
        patterns: list[Any] | None,
    ) -> list[dict[str, Any]]:
        opportunities: list[dict[str, Any]] = []

        detected = self._trigger_detector.detect(ctx)
        for pat in detected:
            opportunities.append({
                'pattern': pat,
                'trigger_type': pat.pattern_type,
                'strength': pat.strength,
            })

        if patterns:
            for p in patterns:
                pat_data = p if isinstance(p, dict) else {'raw': p}
                opportunities.append({
                    'pattern': DetectedPattern(
                        pattern_type=pat_data.get('type', 'unknown'),
                        description=pat_data.get('description', ''),
                        strength=pat_data.get('strength', 0.5),
                    ),
                    'trigger_type': pat_data.get('type', 'unknown'),
                    'strength': pat_data.get('strength', 0.5),
                })

        logger.debug('phase_4_opportunities', count=len(opportunities))
        return opportunities

    # ------------------------------------------------------------------
    # Phase 5 — InterventionSelection
    # ------------------------------------------------------------------

    def _phase_intervention_selection(
        self,
        opportunities: list[dict[str, Any]],
        readiness: EstimatedReadiness,
    ) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        for opp in opportunities:
            strength = opp.get('strength', 0.0)
            if strength < 0.2:
                continue
            intensity = self._select_intensity(strength, readiness)
            opp['intensity'] = intensity
            selected.append(opp)
        logger.debug('phase_5_selected', count=len(selected))
        return selected

    def _select_intensity(
        self, strength: float, readiness: EstimatedReadiness,
    ) -> ReflectionIntensity:
        if strength < 0.4 or readiness.overall_readiness < 0.3:
            return ReflectionIntensity.gentle()
        if strength < 0.6:
            return ReflectionIntensity.exploratory()
        if strength < 0.8:
            return ReflectionIntensity.pattern_proposal()
        return ReflectionIntensity.deep_cognitive_intervention()

    # ------------------------------------------------------------------
    # Phase 6 — TimingEvaluation
    # ------------------------------------------------------------------

    def _phase_timing_evaluation(
        self,
        selected: list[dict[str, Any]],
        conv_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        for opp in selected:
            engagement = conv_state.get('engagement_level', 0.5)
            urgency = opp.get('strength', 0.0)
            opp['timing_score'] = engagement * 0.6 + urgency * 0.4
            opp['should_deliver'] = opp['timing_score'] > 0.3
        timed = [o for o in selected if o.get('should_deliver', False)]
        logger.debug('phase_6_timing', kept=len(timed))
        return timed

    # ------------------------------------------------------------------
    # Phase 7 — DialoguePlanning
    # ------------------------------------------------------------------

    def _phase_dialogue_planning(
        self,
        timed: list[dict[str, Any]],
        readiness: EstimatedReadiness,
    ) -> dict[str, Any] | None:
        if not timed:
            return None
        best = max(timed, key=lambda o: o.get('timing_score', 0.0))
        return {
            'opportunity': best,
            'readiness': readiness,
            'delivery_plan': {
                'intensity': best.get('intensity', ReflectionIntensity.gentle()),
                'timing': 'immediate',
            },
        }

    # ------------------------------------------------------------------
    # Phase 8 — ReflectionDelivery
    # ------------------------------------------------------------------

    def _phase_reflection_delivery(
        self, planned: dict[str, Any] | None,
    ) -> ReflectionOpportunity | None:
        if planned is None:
            return None

        opp_data = planned['opportunity']
        pattern = opp_data.get('pattern', DetectedPattern())

        return ReflectionOpportunity(
            opportunity_identifier=OpportunityIdentifier(),
            detected_pattern=pattern,
            suggested_reflection=pattern.description,
            reflection_category=self._categorize(pattern.pattern_type),
            estimated_readiness=planned['readiness'],
            estimated_benefit=EstimatedBenefit(
                overall_benefit=pattern.strength * 0.7,
            ),
            estimated_risk=EstimatedRisk(overall_risk=0.2),
            urgency=pattern.strength,
            confidence=pattern.strength,
        )

    def _categorize(self, trigger_type: str) -> str:
        from ayeneh.dlg.reflection.types import TRIGGER_TO_CATEGORY
        return TRIGGER_TO_CATEGORY.get(trigger_type, 'meta_cognitive')
