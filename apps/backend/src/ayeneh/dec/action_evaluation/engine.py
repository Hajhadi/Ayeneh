"""DEC-04 Action Evaluation Engine — 8-phase pipeline for evaluating executed actions."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog

from ayeneh.dec.action_evaluation.types import (
    ActionEvaluationObject,
    ActionEvaluationResult,
    ComparisonResult,
    DeviationComponent,
    EvidenceItem,
    ExplainabilityMetadata,
    LessonLearned,
    OutcomeCategory,
    RecommendedRevision,
)

logger = structlog.get_logger(__name__)


class ActionEvaluationEngine:
    """Evaluates executed actions against expected outcomes through an 8-phase pipeline.

    Phases:
        1. ExecutedAction     — identify and describe the action that was taken
        2. ObservedOutcome    — capture what actually happened
        3. ExpectedOutcome    — reconstruct what was expected
        4. Comparison         — compare expected vs observed
        5. DeviationAnalysis  — decompose deviations by dimension
        6. EvidenceIntegration — gather and weight supporting evidence
        7. BehavioralLearning — extract lessons learned
        8. UpdatedCognitiveModel — update the evaluation object with all results
    """

    def __init__(self) -> None:
        pass

    def evaluate(
        self,
        action_description: str = '',
        expected_outcome: str = '',
        observed_outcome: str = '',
        context: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        associated_plan: str = '',
        associated_goal: str = '',
        session_id: str = '',
    ) -> ActionEvaluationResult:
        """Run the full 8-phase action evaluation pipeline."""
        start = time.monotonic()
        ctx = context or {}
        errors: list[str] = []

        logger.info(
            "action_evaluation_started",
            session_id=session_id,
            action=action_description[:80],
        )

        # Phase 1: ExecutedAction
        action_record = self._phase_executed_action(
            action_description, ctx, errors,
        )

        # Phase 2: ObservedOutcome
        observed = self._phase_observed_outcome(
            observed_outcome, ctx, errors,
        )

        # Phase 3: ExpectedOutcome
        expected = self._phase_expected_outcome(
            expected_outcome, ctx, errors,
        )

        # Phase 4: Comparison
        comparison = self._phase_comparison(
            expected, observed, errors,
        )

        # Phase 5: DeviationAnalysis
        deviations = self._phase_deviation_analysis(
            expected, observed, comparison, errors,
        )

        # Phase 6: EvidenceIntegration
        evidence_items = self._phase_evidence_integration(
            evidence or [], ctx, errors,
        )

        # Phase 7: BehavioralLearning
        lessons = self._phase_behavioral_learning(
            comparison, deviations, evidence_items, errors,
        )

        # Phase 8: UpdatedCognitiveModel
        eval_obj = self._phase_updated_cognitive_model(
            action_record, action_description, expected_outcome,
            observed_outcome, deviations, evidence_items, lessons,
            associated_plan, associated_goal, errors,
        )

        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "action_evaluation_completed",
            evaluation_id=eval_obj.evaluation_id,
            outcome_category=comparison.category.category if comparison else 'inconclusive',
            lessons_count=len(lessons),
            duration_ms=duration_ms,
        )

        return ActionEvaluationResult(
            evaluation_id=eval_obj.evaluation_id,
            evaluation_object=eval_obj,
            comparison=comparison,
            confidence=eval_obj.confidence,
            lessons=tuple(lessons),
            duration_ms=duration_ms,
            errors=tuple(errors),
        )

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _phase_executed_action(
        self,
        action_description: str,
        ctx: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        """Phase 1: Identify and describe the executed action."""
        try:
            action_record = {
                'action_id': str(uuid.uuid4()),
                'description': action_description,
                'action_type': ctx.get('action_type', 'general'),
                'executor': ctx.get('executor', 'system'),
                'parameters': ctx.get('action_parameters', {}),
                'execution_timestamp': ctx.get('execution_timestamp', ''),
                'dependencies': ctx.get('dependencies', []),
            }
            logger.debug("phase_executed_action_completed", action_id=action_record['action_id'])
            return action_record
        except Exception as exc:
            errors.append(f"Phase 1 (ExecutedAction) error: {exc}")
            return {'action_id': str(uuid.uuid4()), 'description': action_description}

    def _phase_observed_outcome(
        self,
        observed_outcome: str,
        ctx: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        """Phase 2: Capture what actually happened."""
        try:
            observed = {
                'description': observed_outcome,
                'outcome_indicators': ctx.get('outcome_indicators', []),
                'side_effects': ctx.get('side_effects', []),
                'timeline': ctx.get('actual_timeline', ''),
                'measurable_results': ctx.get('measurable_results', {}),
                'unexpected_events': ctx.get('unexpected_events', []),
            }
            logger.debug("phase_observed_outcome_completed")
            return observed
        except Exception as exc:
            errors.append(f"Phase 2 (ObservedOutcome) error: {exc}")
            return {'description': observed_outcome}

    def _phase_expected_outcome(
        self,
        expected_outcome: str,
        ctx: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        """Phase 3: Reconstruct what was expected."""
        try:
            expected = {
                'description': expected_outcome,
                'success_criteria': ctx.get('success_criteria', []),
                'predicted_indicators': ctx.get('predicted_indicators', []),
                'timeline_expectation': ctx.get('expected_timeline', ''),
                'confidence_at_planning': ctx.get('planning_confidence', 0.5),
                'assumptions': ctx.get('assumptions', []),
            }
            logger.debug("phase_expected_outcome_completed")
            return expected
        except Exception as exc:
            errors.append(f"Phase 3 (ExpectedOutcome) error: {exc}")
            return {'description': expected_outcome}

    def _phase_comparison(
        self,
        expected: dict[str, Any],
        observed: dict[str, Any],
        errors: list[str],
    ) -> ComparisonResult:
        """Phase 4: Compare expected vs observed outcomes."""
        try:
            dimensions: list[DeviationComponent] = []

            # Compare descriptions similarity (simple keyword overlap)
            exp_words = set((expected.get('description', '') or '').lower().split())
            obs_words = set((observed.get('description', '') or '').lower().split())
            if exp_words and obs_words:
                overlap = len(exp_words & obs_words)
                total = len(exp_words | obs_words)
                text_match = overlap / total if total else 0.0
            else:
                text_match = 0.5

            # Compare success criteria
            criteria = expected.get('success_criteria', [])
            indicators = observed.get('outcome_indicators', [])
            criteria_match = min(len(indicators) / max(len(criteria), 1), 1.0) if criteria else 0.5

            # Compare side effects
            expected_side = set(expected.get('assumptions', []))
            actual_side = set(observed.get('side_effects', []))
            side_effect_score = 1.0 - min(len(actual_side - expected_side) / max(len(expected_side), 1), 1.0)

            overall = (text_match * 0.4 + criteria_match * 0.4 + side_effect_score * 0.2)

            dimensions.append(DeviationComponent(
                dimension='textual_alignment',
                expected_value=expected.get('description', ''),
                observed_value=observed.get('description', ''),
                magnitude=abs(text_match - 1.0),
                direction='positive' if text_match >= 0.5 else 'negative',
                explanation=f"Text overlap: {text_match:.1%}",
            ))

            dimensions.append(DeviationComponent(
                dimension='criteria_fulfillment',
                expected_value=len(criteria),
                observed_value=len(indicators),
                magnitude=abs(criteria_match - 1.0),
                direction='positive' if criteria_match >= 0.5 else 'negative',
                explanation=f"Criteria match: {criteria_match:.1%}",
            ))

            dimensions.append(DeviationComponent(
                dimension='side_effects',
                expected_value=list(expected_side),
                observed_value=list(actual_side),
                magnitude=1.0 - side_effect_score,
                direction='positive' if side_effect_score >= 0.5 else 'negative',
                explanation=f"Side-effect score: {side_effect_score:.1%}",
            ))

            # Determine category
            if overall >= 0.8:
                cat = 'successful'
            elif overall >= 0.5:
                cat = 'partially_successful'
            elif overall >= 0.3:
                cat = 'neutral'
            else:
                cat = 'failed'

            # Check for unexpected
            if actual_side - expected_side and overall >= 0.5:
                cat = 'unexpectedly_beneficial'
            if side_effect_score < 0.3:
                cat = 'unexpectedly_harmful'

            category = OutcomeCategory(
                category=cat,
                confidence=overall,
                reasoning=f"Overall match: {overall:.1%}",
            )

            return ComparisonResult(
                overall_match=overall,
                dimensions=tuple(dimensions),
                category=category,
                summary=f"Outcome classified as {cat} with {overall:.1%} match",
            )
        except Exception as exc:
            errors.append(f"Phase 4 (Comparison) error: {exc}")
            return ComparisonResult(
                category=OutcomeCategory(category='inconclusive'),
                summary=f"Comparison failed: {exc}",
            )

    def _phase_deviation_analysis(
        self,
        expected: dict[str, Any],
        observed: dict[str, Any],
        comparison: ComparisonResult,
        errors: list[str],
    ) -> tuple[DeviationComponent, ...]:
        """Phase 5: Decompose deviations by dimension."""
        try:
            deviations = list(comparison.dimensions)

            # Add timeline deviation
            exp_timeline = expected.get('timeline_expectation', '')
            obs_timeline = observed.get('timeline', '')
            if exp_timeline and obs_timeline:
                direction = 'positive' if obs_timeline <= exp_timeline else 'negative'
                deviations.append(DeviationComponent(
                    dimension='timeline',
                    expected_value=exp_timeline,
                    observed_value=obs_timeline,
                    magnitude=0.5,
                    direction=direction,
                    explanation=f"Expected: {exp_timeline}, Observed: {obs_timeline}",
                ))

            logger.debug("phase_deviation_analysis_completed", count=len(deviations))
            return tuple(deviations)
        except Exception as exc:
            errors.append(f"Phase 5 (DeviationAnalysis) error: {exc}")
            return comparison.dimensions

    def _phase_evidence_integration(
        self,
        raw_evidence: list[dict[str, Any]],
        ctx: dict[str, Any],
        errors: list[str],
    ) -> tuple[EvidenceItem, ...]:
        """Phase 6: Gather and weight supporting evidence."""
        try:
            items: list[EvidenceItem] = []
            for ev in raw_evidence:
                items.append(EvidenceItem(
                    evidence_id=ev.get('evidence_id', str(uuid.uuid4())),
                    evidence_type=ev.get('evidence_type', 'direct_observation'),
                    source=ev.get('source', ''),
                    description=ev.get('description', ''),
                    reliability=ev.get('reliability', 0.5),
                    relevance=ev.get('relevance', 0.5),
                ))

            # Add automatic evidence from context
            if ctx.get('measurable_results'):
                items.append(EvidenceItem(
                    evidence_id=str(uuid.uuid4()),
                    evidence_type='measured_outcome',
                    source='system',
                    description=f"Measurable results: {ctx['measurable_results']}",
                    reliability=0.8,
                    relevance=0.9,
                ))

            logger.debug("phase_evidence_integration_completed", count=len(items))
            return tuple(items)
        except Exception as exc:
            errors.append(f"Phase 6 (EvidenceIntegration) error: {exc}")
            return ()

    def _phase_behavioral_learning(
        self,
        comparison: ComparisonResult,
        deviations: tuple[DeviationComponent, ...],
        evidence_items: tuple[EvidenceItem, ...],
        errors: list[str],
    ) -> tuple[LessonLearned, ...]:
        """Phase 7: Extract lessons learned from the evaluation."""
        try:
            lessons: list[LessonLearned] = []
            category = comparison.category.category

            if category == 'successful':
                lessons.append(LessonLearned(
                    lesson_id=str(uuid.uuid4()),
                    lesson_text=f"Action achieved expected outcome with {comparison.overall_match:.0%} match",
                    lesson_type='high_performing_strategy',
                    confidence=comparison.overall_match,
                ))
            elif category == 'failed':
                lessons.append(LessonLearned(
                    lesson_id=str(uuid.uuid4()),
                    lesson_text=f"Action failed to achieve expected outcome ({comparison.overall_match:.0%} match)",
                    lesson_type='recurring_mistake',
                    confidence=1.0 - comparison.overall_match,
                ))
            elif category == 'unexpectedly_harmful':
                lessons.append(LessonLearned(
                    lesson_id=str(uuid.uuid4()),
                    lesson_text="Action produced unexpected negative side effects",
                    lesson_type='recurring_mistake',
                    confidence=0.8,
                ))
            elif category == 'unexpectedly_beneficial':
                lessons.append(LessonLearned(
                    lesson_id=str(uuid.uuid4()),
                    lesson_text="Action produced unexpected positive outcomes",
                    lesson_type='high_performing_strategy',
                    confidence=0.7,
                ))

            # Lesson from dominant deviation
            if deviations:
                largest = max(deviations, key=lambda d: d.magnitude)
                if largest.magnitude > 0.5:
                    lessons.append(LessonLearned(
                        lesson_id=str(uuid.uuid4()),
                        lesson_text=f"Significant deviation in {largest.dimension}: {largest.explanation}",
                        lesson_type='context_sensitive',
                        confidence=1.0 - largest.magnitude,
                    ))

            # Evidence-based lesson
            high_relevance = [e for e in evidence_items if e.relevance > 0.7]
            if len(high_relevance) >= 2:
                lessons.append(LessonLearned(
                    lesson_id=str(uuid.uuid4()),
                    lesson_text=f"Multiple high-relevance evidence items ({len(high_relevance)}) support this evaluation",
                    lesson_type='skill_development',
                    confidence=sum(e.reliability for e in high_relevance) / len(high_relevance),
                ))

            logger.debug("phase_behavioral_learning_completed", count=len(lessons))
            return tuple(lessons)
        except Exception as exc:
            errors.append(f"Phase 7 (BehavioralLearning) error: {exc}")
            return ()

    def _phase_updated_cognitive_model(
        self,
        action_record: dict[str, Any],
        action_description: str,
        expected_outcome: str,
        observed_outcome: str,
        deviations: tuple[DeviationComponent, ...],
        evidence_items: tuple[EvidenceItem, ...],
        lessons: list[LessonLearned],
        associated_plan: str,
        associated_goal: str,
        errors: list[str],
    ) -> ActionEvaluationObject:
        """Phase 8: Update and return the final evaluation object."""
        try:
            explainability = ExplainabilityMetadata(
                reasoning_chain=(
                    f"Evaluated action: {action_description[:100]}",
                    f"Compared expected ({expected_outcome[:50]}) vs observed ({observed_outcome[:50]})",
                    f"Identified {len(deviations)} deviation dimensions",
                    f"Gathered {len(evidence_items)} evidence items",
                    f"Extracted {len(lessons)} lessons",
                ),
                contributing_factors=tuple(
                    {'dimension': d.dimension, 'magnitude': d.magnitude} for d in deviations
                ),
                confidence_decomposition={
                    'comparison_confidence': max((d.magnitude for d in deviations), default=0.5),
                    'evidence_quality': sum(e.reliability for e in evidence_items) / max(len(evidence_items), 1),
                },
            )

            # Compute overall confidence
            evidence_quality = (
                sum(e.reliability * e.relevance for e in evidence_items)
                / max(len(evidence_items), 1)
            )
            lesson_confidence = (
                sum(l.confidence for l in lessons) / max(len(lessons), 1)
                if lessons else 0.5
            )
            overall_confidence = (evidence_quality * 0.4 + lesson_confidence * 0.3 + 0.3)

            revision_dicts = tuple(
                {
                    'revision_id': str(uuid.uuid4()),
                    'target_plan_id': associated_plan,
                    'description': f"Revise based on lesson: {l.lesson_text[:80]}",
                    'rationale': l.lesson_type,
                    'priority': l.confidence,
                }
                for l in lessons
                if l.lesson_type == 'recurring_mistake'
            )

            eval_obj = ActionEvaluationObject(
                evaluation_id=action_record.get('action_id', str(uuid.uuid4())),
                associated_action=action_description,
                associated_plan=associated_plan,
                associated_goal=associated_goal,
                expected_outcome=expected_outcome,
                observed_outcome=observed_outcome,
                deviation_analysis=tuple(
                    {'dimension': d.dimension, 'magnitude': d.magnitude, 'direction': d.direction}
                    for d in deviations
                ),
                supporting_evidence=tuple(e.evidence_id for e in evidence_items),
                lessons_learned=tuple(l.lesson_text for l in lessons),
                confidence=overall_confidence,
                recommended_revisions=revision_dicts,
                explainability_metadata={
                    'reasoning_chain': explainability.reasoning_chain,
                    'contributing_factors': explainability.contributing_factors,
                    'confidence_decomposition': explainability.confidence_decomposition,
                },
            )

            logger.debug("phase_updated_cognitive_model_completed", evaluation_id=eval_obj.evaluation_id)
            return eval_obj
        except Exception as exc:
            errors.append(f"Phase 8 (UpdatedCognitiveModel) error: {exc}")
            return ActionEvaluationObject(
                evaluation_id=action_record.get('action_id', str(uuid.uuid4())),
                associated_action=action_description,
                expected_outcome=expected_outcome,
                observed_outcome=observed_outcome,
            )
