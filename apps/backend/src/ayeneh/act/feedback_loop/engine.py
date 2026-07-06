"""ACT-04 Feedback Loop Coordinator.

7-phase pipeline:
    1. ObservedOutcome — collect observed outcomes
    2. ActionEvaluation — evaluate actions against expectations
    3. Reflection — reflect on patterns and insights
    4. RealityCalibration — calibrate confidence and predictions
    5. KnowledgeUpdate — update knowledge based on learnings
    6. StrategyRevision — revise strategies based on feedback
    7. BehavioralAdaptation — adapt behaviors from accumulated feedback
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.act.feedback_loop.propagation import FeedbackPropagation
from ayeneh.act.feedback_loop.types import (
    FEEDBACK_TYPES,
    FEEDBACK_SEVERITY_LEVELS,
    LEARNING_CATEGORIES,
    ActionEvaluation,
    BehavioralAdaptation,
    FeedbackObject,
    FeedbackResult,
    KnowledgeUpdate,
    ObservedOutcome,
    RealityCalibration,
    ReflectionEntry,
    StrategyRevision,
)

logger = structlog.get_logger(__name__)


class FeedbackLoopCoordinator:
    """Feedback loop coordinator engine (ACT-04).

    Pipeline:
        1. ObservedOutcome — collect observed outcomes
        2. ActionEvaluation — evaluate actions against expectations
        3. Reflection — reflect on patterns and insights
        4. RealityCalibration — calibrate confidence and predictions
        5. KnowledgeUpdate — update knowledge based on learnings
        6. StrategyRevision — revise strategies based on feedback
        7. BehavioralAdaptation — adapt behaviors from accumulated feedback
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._propagation = FeedbackPropagation()
        self._feedback_store: dict[str, FeedbackObject] = {}

    def process(
        self,
        feedback_request: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> FeedbackResult:
        """Run the full ACT-04 pipeline.

        Parameters
        ----------
        feedback_request:
            Dict with ``'feedback_id'``, ``'source_event'``, and optional fields.
        context:
            Optional context dict with outcomes, evaluations, etc.
        """
        ctx = context or {}

        logger.info(
            'act.feedback_loop.pipeline_started',
            feedback_id=feedback_request.get('feedback_id', ''),
        )

        # Phase 1: ObservedOutcome
        outcomes = self._phase_observed_outcome(feedback_request, ctx)

        # Phase 2: ActionEvaluation
        evaluations = self._phase_action_evaluation(outcomes, ctx)

        # Phase 3: Reflection
        reflections = self._phase_reflection(evaluations, ctx)

        # Phase 4: RealityCalibration
        calibrations = self._phase_reality_calibration(reflections, ctx)

        # Phase 5: KnowledgeUpdate
        knowledge_updates = self._phase_knowledge_update(reflections, calibrations, ctx)

        # Phase 6: StrategyRevision
        strategy_revisions = self._phase_strategy_revision(reflections, knowledge_updates, ctx)

        # Phase 7: BehavioralAdaptation
        adaptations = self._phase_behavioral_adaptation(strategy_revisions, calibrations, ctx)

        # Build feedback object
        feedback = self._build_feedback_object(
            feedback_request, outcomes, evaluations, reflections,
            calibrations, knowledge_updates, strategy_revisions, adaptations,
        )

        # Propagate feedback
        self._propagation.propagate(feedback)

        phases = (
            'ObservedOutcome',
            'ActionEvaluation',
            'Reflection',
            'RealityCalibration',
            'KnowledgeUpdate',
            'StrategyRevision',
            'BehavioralAdaptation',
        )

        result = FeedbackResult(
            feedback=feedback,
            observed_outcomes=outcomes,
            action_evaluations=evaluations,
            reflections=reflections,
            calibrations=calibrations,
            knowledge_updates=knowledge_updates,
            strategy_revisions=strategy_revisions,
            behavioral_adaptations=adaptations,
            pipeline_phases_completed=phases,
        )

        logger.info(
            'act.feedback_loop.pipeline_completed',
            feedback_id=feedback.feedback_id,
            outcomes=len(outcomes),
            evaluations=len(evaluations),
            reflections=len(reflections),
            adaptations=len(adaptations),
        )

        return result

    # -------------------------------------------------------------------
    # Phase 1: ObservedOutcome
    # -------------------------------------------------------------------

    def _phase_observed_outcome(
        self,
        request: dict[str, Any],
        ctx: dict[str, Any],
    ) -> tuple[ObservedOutcome, ...]:
        """Collect observed outcomes from context."""
        raw_outcomes = ctx.get('observed_outcomes', [])
        outcomes: list[ObservedOutcome] = []

        for raw in raw_outcomes:
            outcome = ObservedOutcome(
                outcome_id=raw.get('outcome_id', str(uuid.uuid4())),
                source_event=raw.get('source_event', request.get('source_event', '')),
                outcome_type=raw.get('outcome_type', 'general'),
                description=raw.get('description', ''),
                expected_value=raw.get('expected_value'),
                actual_value=raw.get('actual_value'),
                deviation_magnitude=raw.get('deviation_magnitude', 0.0),
                confidence=raw.get('confidence', 0.5),
                metadata=dict(raw.get('metadata', {})),
            )
            outcomes.append(outcome)

        if not outcomes and request.get('source_event'):
            outcomes.append(
                ObservedOutcome(
                    outcome_id=str(uuid.uuid4()),
                    source_event=request.get('source_event', ''),
                    outcome_type=request.get('outcome_type', 'general'),
                    description=request.get('description', ''),
                    confidence=request.get('confidence', 0.5),
                ),
            )

        logger.debug(
            'act.feedback_loop.phase_observed_outcome',
            outcomes_count=len(outcomes),
        )
        return tuple(outcomes)

    # -------------------------------------------------------------------
    # Phase 2: ActionEvaluation
    # -------------------------------------------------------------------

    def _phase_action_evaluation(
        self,
        outcomes: tuple[ObservedOutcome, ...],
        ctx: dict[str, Any],
    ) -> tuple[ActionEvaluation, ...]:
        """Evaluate actions against expected outcomes."""
        evaluations: list[ActionEvaluation] = []

        for outcome in outcomes:
            success_score = self._compute_success_score(outcome)
            factors = self._identify_contributing_factors(outcome)
            failures = self._identify_failure_reasons(outcome)

            evaluation = ActionEvaluation(
                evaluation_id=str(uuid.uuid4()),
                action_description=outcome.description,
                expected_outcome=str(outcome.expected_value) if outcome.expected_value else '',
                observed_outcome=str(outcome.actual_value) if outcome.actual_value else '',
                outcome_match=outcome.deviation_magnitude < 0.2,
                success_score=success_score,
                contributing_factors=tuple(factors),
                failure_reasons=tuple(failures),
                confidence=outcome.confidence,
            )
            evaluations.append(evaluation)

        # Also include any raw evaluations from context
        for raw in ctx.get('action_evaluations', []):
            evaluation = ActionEvaluation(
                evaluation_id=raw.get('evaluation_id', str(uuid.uuid4())),
                action_description=raw.get('action_description', ''),
                expected_outcome=raw.get('expected_outcome', ''),
                observed_outcome=raw.get('observed_outcome', ''),
                outcome_match=raw.get('outcome_match', False),
                success_score=raw.get('success_score', 0.5),
                contributing_factors=tuple(raw.get('contributing_factors', ())),
                failure_reasons=tuple(raw.get('failure_reasons', ())),
                confidence=raw.get('confidence', 0.5),
            )
            evaluations.append(evaluation)

        logger.debug(
            'act.feedback_loop.phase_action_evaluation',
            evaluations_count=len(evaluations),
        )
        return tuple(evaluations)

    def _compute_success_score(self, outcome: ObservedOutcome) -> float:
        """Compute a success score for an outcome."""
        if outcome.expected_value is None:
            return 0.5
        if outcome.deviation_magnitude <= 0.0:
            return 1.0
        if outcome.deviation_magnitude >= 1.0:
            return 0.0
        return max(0.0, 1.0 - outcome.deviation_magnitude)

    def _identify_contributing_factors(
        self, outcome: ObservedOutcome,
    ) -> list[str]:
        """Identify factors that contributed to the outcome."""
        factors: list[str] = []
        if outcome.confidence >= 0.7:
            factors.append('high_confidence_prediction')
        if outcome.deviation_magnitude < 0.1:
            factors.append('accurate_prediction')
        if outcome.metadata.get('context_rich'):
            factors.append('rich_context')
        return factors

    def _identify_failure_reasons(
        self, outcome: ObservedOutcome,
    ) -> list[str]:
        """Identify reasons for outcome failure."""
        reasons: list[str] = []
        if outcome.deviation_magnitude > 0.5:
            reasons.append('significant_deviation')
        if outcome.confidence < 0.3:
            reasons.append('low_prediction_confidence')
        if outcome.expected_value is None:
            reasons.append('no_expected_baseline')
        return reasons

    # -------------------------------------------------------------------
    # Phase 3: Reflection
    # -------------------------------------------------------------------

    def _phase_reflection(
        self,
        evaluations: tuple[ActionEvaluation, ...],
        ctx: dict[str, Any],
    ) -> tuple[ReflectionEntry, ...]:
        """Reflect on patterns and insights from evaluations."""
        reflections: list[ReflectionEntry] = []

        successful = [e for e in evaluations if e.outcome_match]
        failed = [e for e in evaluations if not e.outcome_match]

        if evaluations:
            avg_score = sum(e.success_score for e in evaluations) / len(evaluations)
            insights: list[str] = []

            if successful:
                insights.append(
                    f'{len(successful)} successful outcome(s) — '
                    f'avg score: {sum(e.success_score for e in successful) / len(successful):.2f}',
                )
            if failed:
                insights.append(
                    f'{len(failed)} failed outcome(s) — '
                    f'common reasons: {", ".join(r for e in failed for r in e.failure_reasons[:2])}',
                )

            patterns = self._identify_patterns(evaluations)

            reflections.append(
                ReflectionEntry(
                    reflection_id=str(uuid.uuid4()),
                    reflection_type='evaluation_summary',
                    source_evaluations=tuple(e.evaluation_id for e in evaluations),
                    insights=tuple(insights),
                    patterns_identified=tuple(patterns),
                    confidence=avg_score,
                ),
            )

        # Include any raw reflections from context
        for raw in ctx.get('reflections', []):
            reflection = ReflectionEntry(
                reflection_id=raw.get('reflection_id', str(uuid.uuid4())),
                reflection_type=raw.get('reflection_type', 'general'),
                source_evaluations=tuple(raw.get('source_evaluations', ())),
                insights=tuple(raw.get('insights', ())),
                patterns_identified=tuple(raw.get('patterns_identified', ())),
                confidence=raw.get('confidence', 0.5),
            )
            reflections.append(reflection)

        logger.debug(
            'act.feedback_loop.phase_reflection',
            reflections_count=len(reflections),
        )
        return tuple(reflections)

    def _identify_patterns(
        self, evaluations: tuple[ActionEvaluation, ...],
    ) -> list[str]:
        """Identify patterns across evaluations."""
        patterns: list[str] = []

        all_factors: list[str] = []
        for e in evaluations:
            all_factors.extend(e.contributing_factors)

        factor_counts: dict[str, int] = {}
        for f in all_factors:
            factor_counts[f] = factor_counts.get(f, 0) + 1

        for factor, count in factor_counts.items():
            if count >= 2:
                patterns.append(f'recurring_factor:{factor}')

        success_rate = (
            sum(1 for e in evaluations if e.outcome_match) / len(evaluations)
            if evaluations else 0.0
        )
        if success_rate > 0.8:
            patterns.append('high_success_rate')
        elif success_rate < 0.3:
            patterns.append('low_success_rate')

        return patterns

    # -------------------------------------------------------------------
    # Phase 4: RealityCalibration
    # -------------------------------------------------------------------

    def _phase_reality_calibration(
        self,
        reflections: tuple[ReflectionEntry, ...],
        ctx: dict[str, Any],
    ) -> tuple[RealityCalibration, ...]:
        """Calibrate confidence and predictions based on reality."""
        calibrations: list[RealityCalibration] = []

        for reflection in reflections:
            if reflection.confidence > 0 and reflection.insights:
                prev_conf = ctx.get('previous_confidence', 0.5)
                adjustment = self._compute_calibration_adjustment(
                    prev_conf, reflection.confidence, reflection,
                )

                calibrations.append(
                    RealityCalibration(
                        calibration_id=str(uuid.uuid4()),
                        calibration_type='confidence',
                        previous_value=prev_conf,
                        adjusted_value=prev_conf + adjustment,
                        adjustment_reason=self._summarize_adjustment_reason(reflection),
                        evidence=reflection.insights,
                        confidence=abs(adjustment),
                    ),
                )

        # Include any raw calibrations from context
        for raw in ctx.get('calibrations', []):
            calibrations.append(
                RealityCalibration(
                    calibration_id=raw.get('calibration_id', str(uuid.uuid4())),
                    calibration_type=raw.get('calibration_type', 'confidence'),
                    previous_value=raw.get('previous_value', 0.0),
                    adjusted_value=raw.get('adjusted_value', 0.0),
                    adjustment_reason=raw.get('adjustment_reason', ''),
                    evidence=tuple(raw.get('evidence', ())),
                    confidence=raw.get('confidence', 0.5),
                ),
            )

        logger.debug(
            'act.feedback_loop.phase_reality_calibration',
            calibrations_count=len(calibrations),
        )
        return tuple(calibrations)

    def _compute_calibration_adjustment(
        self,
        previous: float,
        current: float,
        reflection: ReflectionEntry,
    ) -> float:
        """Compute how much to adjust calibration."""
        diff = current - previous
        factor = 0.1
        if reflection.patterns_identified:
            factor += 0.05 * len(reflection.patterns_identified)
        adjustment = diff * min(factor, 0.5)
        return max(-0.3, min(0.3, adjustment))

    def _summarize_adjustment_reason(self, reflection: ReflectionEntry) -> str:
        """Summarize the reason for a calibration adjustment."""
        if reflection.patterns_identified:
            return f'Patterns detected: {", ".join(reflection.patterns_identified[:3])}'
        return 'Evaluation-based calibration'

    # -------------------------------------------------------------------
    # Phase 5: KnowledgeUpdate
    # -------------------------------------------------------------------

    def _phase_knowledge_update(
        self,
        reflections: tuple[ReflectionEntry, ...],
        calibrations: tuple[RealityCalibration, ...],
        ctx: dict[str, Any],
    ) -> tuple[KnowledgeUpdate, ...]:
        """Update knowledge based on learnings."""
        updates: list[KnowledgeUpdate] = []

        for reflection in reflections:
            if reflection.insights:
                updates.append(
                    KnowledgeUpdate(
                        update_id=str(uuid.uuid4()),
                        update_type='addition',
                        affected_module=ctx.get('affected_module', 'general'),
                        previous_knowledge='',
                        new_knowledge='; '.join(reflection.insights),
                        confidence_delta=reflection.confidence,
                        source_reflections=(reflection.reflection_id,),
                        confidence=reflection.confidence,
                    ),
                )

        for calibration in calibrations:
            if calibration.adjustment_reason:
                updates.append(
                    KnowledgeUpdate(
                        update_id=str(uuid.uuid4()),
                        update_type='calibration',
                        affected_module=ctx.get('affected_module', 'general'),
                        previous_knowledge=f'confidence:{calibration.previous_value}',
                        new_knowledge=f'confidence:{calibration.adjusted_value}',
                        confidence_delta=calibration.adjusted_value - calibration.previous_value,
                        source_reflections=(),
                        confidence=calibration.confidence,
                    ),
                )

        # Include any raw knowledge updates from context
        for raw in ctx.get('knowledge_updates', []):
            updates.append(
                KnowledgeUpdate(
                    update_id=raw.get('update_id', str(uuid.uuid4())),
                    update_type=raw.get('update_type', 'addition'),
                    affected_module=raw.get('affected_module', ''),
                    previous_knowledge=raw.get('previous_knowledge', ''),
                    new_knowledge=raw.get('new_knowledge', ''),
                    confidence_delta=raw.get('confidence_delta', 0.0),
                    source_reflections=tuple(raw.get('source_reflections', ())),
                    confidence=raw.get('confidence', 0.5),
                ),
            )

        logger.debug(
            'act.feedback_loop.phase_knowledge_update',
            updates_count=len(updates),
        )
        return tuple(updates)

    # -------------------------------------------------------------------
    # Phase 6: StrategyRevision
    # -------------------------------------------------------------------

    def _phase_strategy_revision(
        self,
        reflections: tuple[ReflectionEntry, ...],
        knowledge_updates: tuple[KnowledgeUpdate, ...],
        ctx: dict[str, Any],
    ) -> tuple[StrategyRevision, ...]:
        """Revise strategies based on accumulated feedback."""
        revisions: list[StrategyRevision] = []

        for reflection in reflections:
            if 'low_success_rate' in reflection.patterns_identified:
                revisions.append(
                    StrategyRevision(
                        revision_id=str(uuid.uuid4()),
                        affected_strategy=ctx.get('current_strategy', 'default'),
                        revision_type='major_change',
                        previous_approach='current_approach',
                        new_approach='needs_reassessment',
                        rationale='Low success rate detected in evaluations',
                        source_reflections=(reflection.reflection_id,),
                        confidence=reflection.confidence,
                    ),
                )
            elif 'high_success_rate' in reflection.patterns_identified:
                revisions.append(
                    StrategyRevision(
                        revision_id=str(uuid.uuid4()),
                        affected_strategy=ctx.get('current_strategy', 'default'),
                        revision_type='reinforcement',
                        previous_approach='current_approach',
                        new_approach='continue_current_approach',
                        rationale='High success rate confirms current strategy',
                        source_reflections=(reflection.reflection_id,),
                        confidence=reflection.confidence,
                    ),
                )

        # Include any raw strategy revisions from context
        for raw in ctx.get('strategy_revisions', []):
            revisions.append(
                StrategyRevision(
                    revision_id=raw.get('revision_id', str(uuid.uuid4())),
                    affected_strategy=raw.get('affected_strategy', ''),
                    revision_type=raw.get('revision_type', 'adjustment'),
                    previous_approach=raw.get('previous_approach', ''),
                    new_approach=raw.get('new_approach', ''),
                    rationale=raw.get('rationale', ''),
                    source_reflections=tuple(raw.get('source_reflections', ())),
                    confidence=raw.get('confidence', 0.5),
                ),
            )

        logger.debug(
            'act.feedback_loop.phase_strategy_revision',
            revisions_count=len(revisions),
        )
        return tuple(revisions)

    # -------------------------------------------------------------------
    # Phase 7: BehavioralAdaptation
    # -------------------------------------------------------------------

    def _phase_behavioral_adaptation(
        self,
        strategy_revisions: tuple[StrategyRevision, ...],
        calibrations: tuple[RealityCalibration, ...],
        ctx: dict[str, Any],
    ) -> tuple[BehavioralAdaptation, ...]:
        """Adapt behaviors from accumulated feedback."""
        adaptations: list[BehavioralAdaptation] = []

        for revision in strategy_revisions:
            if revision.revision_type == 'major_change':
                adaptations.append(
                    BehavioralAdaptation(
                        adaptation_id=str(uuid.uuid4()),
                        adaptation_type='strategy_shift',
                        target_behavior=revision.affected_strategy,
                        previous_pattern=revision.previous_approach,
                        new_pattern=revision.new_approach,
                        expected_impact='improved_outcomes',
                        confidence=revision.confidence,
                    ),
                )
            elif revision.revision_type == 'reinforcement':
                adaptations.append(
                    BehavioralAdaptation(
                        adaptation_id=str(uuid.uuid4()),
                        adaptation_type='strategy_reinforcement',
                        target_behavior=revision.affected_strategy,
                        previous_pattern=revision.previous_approach,
                        new_pattern=revision.new_approach,
                        expected_impact='maintained_performance',
                        confidence=revision.confidence,
                    ),
                )

        for calibration in calibrations:
            if abs(calibration.adjusted_value - calibration.previous_value) > 0.1:
                adaptations.append(
                    BehavioralAdaptation(
                        adaptation_id=str(uuid.uuid4()),
                        adaptation_type='confidence_adjustment',
                        target_behavior='prediction_confidence',
                        previous_pattern=str(calibration.previous_value),
                        new_pattern=str(calibration.adjusted_value),
                        expected_impact='better_calibrated_predictions',
                        confidence=calibration.confidence,
                    ),
                )

        # Include any raw adaptations from context
        for raw in ctx.get('behavioral_adaptations', []):
            adaptations.append(
                BehavioralAdaptation(
                    adaptation_id=raw.get('adaptation_id', str(uuid.uuid4())),
                    adaptation_type=raw.get('adaptation_type', 'habit_adjustment'),
                    target_behavior=raw.get('target_behavior', ''),
                    previous_pattern=raw.get('previous_pattern', ''),
                    new_pattern=raw.get('new_pattern', ''),
                    expected_impact=raw.get('expected_impact', ''),
                    confidence=raw.get('confidence', 0.5),
                ),
            )

        logger.debug(
            'act.feedback_loop.phase_behavioral_adaptation',
            adaptations_count=len(adaptations),
        )
        return tuple(adaptations)

    # -------------------------------------------------------------------
    # Helper: build FeedbackObject
    # -------------------------------------------------------------------

    def _build_feedback_object(
        self,
        request: dict[str, Any],
        outcomes: tuple[ObservedOutcome, ...],
        evaluations: tuple[ActionEvaluation, ...],
        reflections: tuple[ReflectionEntry, ...],
        calibrations: tuple[RealityCalibration, ...],
        knowledge_updates: tuple[KnowledgeUpdate, ...],
        strategy_revisions: tuple[StrategyRevision, ...],
        adaptations: tuple[BehavioralAdaptation, ...],
    ) -> FeedbackObject:
        """Build the core FeedbackObject."""
        feedback_id = request.get('feedback_id', str(uuid.uuid4()))
        affected = tuple(
            set(
                [o.source_event for o in outcomes if o.source_event]
                + [u.affected_module for u in knowledge_updates if u.affected_module]
            ),
        )
        evidence = tuple(
            [e.action_description for e in evaluations]
        )
        learning = ''
        if reflections:
            all_insights = []
            for r in reflections:
                all_insights.extend(r.insights)
            learning = '; '.join(all_insights[:3])

        revisions_dicts = tuple(
            {
                'revision_id': r.revision_id,
                'affected_strategy': r.affected_strategy,
                'revision_type': r.revision_type,
                'new_approach': r.new_approach,
            }
            for r in strategy_revisions
        )

        remaining: list[str] = []
        if calibrations:
            for c in calibrations:
                if abs(c.adjusted_value - c.previous_value) > 0.2:
                    remaining.append(
                        f'Large calibration adjustment needed for {c.calibration_type}',
                    )

        avg_confidence = 0.0
        all_conf = (
            [e.confidence for e in evaluations]
            + [r.confidence for r in reflections]
        )
        if all_conf:
            avg_confidence = sum(all_conf) / len(all_conf)

        return FeedbackObject(
            feedback_id=feedback_id,
            source_event=request.get('source_event', ''),
            affected_modules=affected,
            observed_evidence=evidence,
            learning_outcome=learning,
            confidence=avg_confidence,
            propagation_targets=request.get('propagation_targets', ()),
            applied_revisions=revisions_dicts,
            remaining_questions=tuple(remaining),
            explainability_metadata={
                'outcomes_count': len(outcomes),
                'evaluations_count': len(evaluations),
                'reflections_count': len(reflections),
                'calibrations_count': len(calibrations),
                'knowledge_updates_count': len(knowledge_updates),
                'strategy_revisions_count': len(strategy_revisions),
                'adaptations_count': len(adaptations),
            },
        )

    # -------------------------------------------------------------------
    # Public helpers
    # -------------------------------------------------------------------

    def get_feedback(self, feedback_id: str) -> FeedbackObject | None:
        """Retrieve a feedback object by ID."""
        return self._feedback_store.get(feedback_id)

    def list_feedback(self) -> list[FeedbackObject]:
        """Return all stored feedback objects."""
        return list(self._feedback_store.values())

    def get_propagation_history(
        self,
        module: str | None = None,
    ) -> list:
        """Get propagation history from the propagation subsystem."""
        return self._propagation.get_propagation_history(module)

    def get_saturation_status(self) -> dict[str, dict[str, Any]]:
        """Get saturation status from the propagation subsystem."""
        return self._propagation.get_saturation_status()
