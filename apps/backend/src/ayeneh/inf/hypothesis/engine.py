"""INF-05 Hypothesis Engine.

9-phase pipeline for generating and testing scientific hypotheses:

1. Context Collection
2. Evidence Analysis
3. Pattern Detection
4. Hypothesis Generation
5. Competing Hypotheses
6. Evidence Evaluation
7. Confidence Estimation
8. Future Evidence Planning
9. Publication
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.inf.hypothesis.bayesian import BayesianUpdater
from ayeneh.inf.hypothesis.types import (
    HYPOTHESIS_SOURCES,
    HYPOTHESIS_STATUSES,
    EvidenceGap,
    EvidenceQuality,
    HypothesisFamily,
    HypothesisObject,
    HypothesisResult,
    PredictedObservation,
)

logger = structlog.get_logger(__name__)


class HypothesisEngine:
    """Generates and tests scientific hypotheses (INF-05)."""

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._bayesian = BayesianUpdater()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        evidence: list[Any],
        graph: Any = None,
        context: dict[str, Any] | None = None,
    ) -> HypothesisResult:
        """Run the full 9-phase hypothesis pipeline."""
        ctx = context or {}
        logger.info('hypothesis_pipeline_start', evidence_count=len(evidence))

        # Phase 1 – Context Collection
        enriched_ctx = self._phase_context_collection(ctx)

        # Phase 2 – Evidence Analysis
        analysed_evidence = self._phase_evidence_analysis(evidence, enriched_ctx)

        # Phase 3 – Pattern Detection
        patterns = self._phase_pattern_detection(analysed_evidence, graph)

        # Phase 4 – Hypothesis Generation
        hypotheses = self._phase_hypothesis_generation(patterns, analysed_evidence, enriched_ctx)

        # Phase 5 – Competing Hypotheses
        hypotheses = self._phase_competing_hypotheses(hypotheses)

        # Phase 6 – Evidence Evaluation
        hypotheses, gaps = self._phase_evidence_evaluation(hypotheses, analysed_evidence)

        # Phase 7 – Confidence Estimation
        hypotheses = self._phase_confidence_estimation(hypotheses, analysed_evidence)

        # Phase 8 – Future Evidence Planning
        predictions, gaps = self._phase_future_evidence(hypotheses, gaps)

        # Phase 9 – Publication
        result = self._phase_publication(
            hypotheses, predictions, gaps, enriched_ctx,
        )

        logger.info(
            'hypothesis_pipeline_end',
            hypotheses_generated=len(result.hypotheses),
            overall_confidence=result.overall_confidence,
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1 – Context Collection
    # ------------------------------------------------------------------

    def _phase_context_collection(self, context: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(context)
        enriched.setdefault('analysis_timestamp', uuid.uuid4().hex)
        enriched.setdefault('available_sources', list(HYPOTHESIS_SOURCES))
        enriched.setdefault('available_statuses', list(HYPOTHESIS_STATUSES))
        logger.debug('phase_1_context_collected', keys=list(enriched.keys()))
        return enriched

    # ------------------------------------------------------------------
    # Phase 2 – Evidence Analysis
    # ------------------------------------------------------------------

    def _phase_evidence_analysis(
        self,
        evidence: list[Any],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        analysed: list[dict[str, Any]] = []
        for item in evidence:
            record = self._analyze_single_evidence(item)
            analysed.append(record)
        context['evidence_analysed'] = len(analysed)
        logger.debug('phase_2_evidence_analysed', count=len(analysed))
        return analysed

    def _analyze_single_evidence(self, item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return {
                'id': item.get('id', uuid.uuid4().hex[:12]),
                'type': item.get('type', 'unknown'),
                'quality': item.get('quality', 0.5),
                'content': item.get('content', ''),
                'raw': item,
            }
        return {
            'id': getattr(item, 'evidence_id', uuid.uuid4().hex[:12]),
            'type': getattr(item, 'evidence_type', 'unknown'),
            'quality': getattr(item, 'quality', 0.5),
            'content': getattr(item, 'content', ''),
            'raw': item,
        }

    # ------------------------------------------------------------------
    # Phase 3 – Pattern Detection
    # ------------------------------------------------------------------

    def _phase_pattern_detection(
        self,
        evidence: list[dict[str, Any]],
        graph: Any,
    ) -> list[dict[str, Any]]:
        patterns: list[dict[str, Any]] = []
        type_groups: dict[str, list[dict[str, Any]]] = {}
        for ev in evidence:
            t = ev.get('type', 'unknown')
            type_groups.setdefault(t, []).append(ev)
        for ev_type, items in type_groups.items():
            if len(items) >= 2:
                patterns.append({
                    'pattern_id': f'pat_{uuid.uuid4().hex[:8]}',
                    'pattern_type': 'cooccurrence',
                    'evidence_type': ev_type,
                    'evidence_ids': tuple(i['id'] for i in items),
                    'strength': min(1.0, len(items) * 0.2),
                })
        if graph is not None:
            patterns.append({
                'pattern_id': f'pat_{uuid.uuid4().hex[:8]}',
                'pattern_type': 'graph_structure',
                'evidence_type': 'graph',
                'evidence_ids': (),
                'strength': 0.3,
            })
        logger.debug('phase_3_patterns', count=len(patterns))
        return patterns

    # ------------------------------------------------------------------
    # Phase 4 – Hypothesis Generation
    # ------------------------------------------------------------------

    def _phase_hypothesis_generation(
        self,
        patterns: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[HypothesisObject]:
        hypotheses: list[HypothesisObject] = []
        for pat in patterns:
            ev_ids = pat.get('evidence_ids', ())
            hyp = HypothesisObject(
                hypothesis_id=f'hyp_{uuid.uuid4().hex[:12]}',
                originating_context=pat.get('pattern_type', ''),
                target_question=f"What drives the {pat.get('evidence_type', 'unknown')} pattern?",
                statement=f"There is a meaningful {pat.get('pattern_type', 'unknown')} pattern in {pat.get('evidence_type', 'unknown')} evidence.",
                supporting_evidence=ev_ids,
                confidence=pat.get('strength', 0.3) * 0.5,
                current_status='active',
            )
            hypotheses.append(hyp)
        if not hypotheses and evidence:
            hyp = HypothesisObject(
                hypothesis_id=f'hyp_{uuid.uuid4().hex[:12]}',
                originating_context='observed_behavior',
                target_question='What patterns exist in the observed data?',
                statement='The observed evidence contains latent patterns worth investigating.',
                supporting_evidence=tuple(e['id'] for e in evidence[:5]),
                confidence=0.2,
                current_status='active',
            )
            hypotheses.append(hyp)
        context['hypotheses_generated'] = len(hypotheses)
        logger.debug('phase_4_generated', count=len(hypotheses))
        return hypotheses

    # ------------------------------------------------------------------
    # Phase 5 – Competing Hypotheses
    # ------------------------------------------------------------------

    def _phase_competing_hypotheses(
        self,
        hypotheses: list[HypothesisObject],
    ) -> list[HypothesisObject]:
        updated: list[HypothesisObject] = []
        other_ids = [h.hypothesis_id for h in hypotheses]
        for hyp in hypotheses:
            competitors = tuple(
                oid for oid in other_ids if oid != hyp.hypothesis_id
            )
            updated.append(HypothesisObject(
                hypothesis_id=hyp.hypothesis_id,
                originating_context=hyp.originating_context,
                target_question=hyp.target_question,
                statement=hyp.statement,
                supporting_evidence=hyp.supporting_evidence,
                contradictory_evidence=hyp.contradictory_evidence,
                competing_hypotheses=competitors,
                confidence=hyp.confidence,
                expected_predictions=hyp.expected_predictions,
                evidence_requirements=hyp.evidence_requirements,
                revision_history=hyp.revision_history,
                current_status=hyp.current_status,
                version_metadata=hyp.version_metadata,
                creation_timestamp=hyp.creation_timestamp,
            ))
        logger.debug('phase_5_competing', count=len(updated))
        return updated

    # ------------------------------------------------------------------
    # Phase 6 – Evidence Evaluation
    # ------------------------------------------------------------------

    def _phase_evidence_evaluation(
        self,
        hypotheses: list[HypothesisObject],
        evidence: list[dict[str, Any]],
    ) -> tuple[list[HypothesisObject], list[EvidenceGap]]:
        evidence_by_id = {e['id']: e for e in evidence}
        gaps: list[EvidenceGap] = []
        updated: list[HypothesisObject] = []
        for hyp in hypotheses:
            supp_count = sum(
                1 for eid in hyp.supporting_evidence if eid in evidence_by_id
            )
            contra_count = sum(
                1 for eid in hyp.contradictory_evidence if eid in evidence_by_id
            )
            if supp_count + contra_count == 0:
                gaps.append(EvidenceGap(
                    gap_id=f'gap_{hyp.hypothesis_id}',
                    description=f"No evidence linked to hypothesis {hyp.hypothesis_id}",
                    importance=1.0 - hyp.confidence,
                    collection_method='observe_behavior',
                ))
            updated.append(hyp)
        logger.debug('phase_6_evaluated', gaps=len(gaps))
        return updated, gaps

    # ------------------------------------------------------------------
    # Phase 7 – Confidence Estimation
    # ------------------------------------------------------------------

    def _phase_confidence_estimation(
        self,
        hypotheses: list[HypothesisObject],
        evidence: list[dict[str, Any]],
    ) -> list[HypothesisObject]:
        updated: list[HypothesisObject] = []
        for hyp in hypotheses:
            n_supp = len(hyp.supporting_evidence)
            n_contra = len(hyp.contradictory_evidence)
            total = n_supp + n_contra
            if total > 0:
                ratio = n_supp / total
            else:
                ratio = 0.5
            new_conf = self._bayesian.update(
                prior=hyp.confidence,
                evidence_quality=0.6,
                likelihood_ratio=ratio / max(1.0 - ratio, 0.01),
            )
            status = self._derive_status(new_conf, hyp.confidence)
            updated.append(HypothesisObject(
                hypothesis_id=hyp.hypothesis_id,
                originating_context=hyp.originating_context,
                target_question=hyp.target_question,
                statement=hyp.statement,
                supporting_evidence=hyp.supporting_evidence,
                contradictory_evidence=hyp.contradictory_evidence,
                competing_hypotheses=hyp.competing_hypotheses,
                confidence=new_conf,
                expected_predictions=hyp.expected_predictions,
                evidence_requirements=hyp.evidence_requirements,
                revision_history=hyp.revision_history,
                current_status=status,
                version_metadata=hyp.version_metadata,
                creation_timestamp=hyp.creation_timestamp,
            ))
        logger.debug('phase_7_confidence_updated', count=len(updated))
        return updated

    def _derive_status(self, new_conf: float, old_conf: float) -> str:
        if new_conf >= 0.85:
            return 'confirmed'
        if new_conf <= 0.1:
            return 'rejected'
        if new_conf > old_conf + 0.05:
            return 'strengthening'
        if new_conf < old_conf - 0.05:
            return 'weakening'
        return 'active'

    # ------------------------------------------------------------------
    # Phase 8 – Future Evidence Planning
    # ------------------------------------------------------------------

    def _phase_future_evidence(
        self,
        hypotheses: list[HypothesisObject],
        existing_gaps: list[EvidenceGap],
    ) -> tuple[tuple[PredictedObservation, ...], tuple[EvidenceGap, ...]]:
        predictions: list[PredictedObservation] = []
        gaps = list(existing_gaps)
        for hyp in hypotheses:
            if hyp.current_status in ('active', 'strengthening'):
                pred = PredictedObservation(
                    prediction_id=f'pred_{hyp.hypothesis_id}',
                    description=f"If {hyp.statement[:60]}..., we should observe supporting data.",
                    evidence_type='behavioral',
                    required=True,
                )
                predictions.append(pred)
                if not hyp.supporting_evidence:
                    gaps.append(EvidenceGap(
                        gap_id=f'gap_pred_{hyp.hypothesis_id}',
                        description=f"Need evidence for prediction of {hyp.hypothesis_id}",
                        importance=0.8,
                        collection_method='observe_behavior',
                    ))
        logger.debug('phase_8_future', predictions=len(predictions), gaps=len(gaps))
        return tuple(predictions), tuple(gaps)

    # ------------------------------------------------------------------
    # Phase 9 – Publication
    # ------------------------------------------------------------------

    def _phase_publication(
        self,
        hypotheses: list[HypothesisObject],
        predictions: tuple[PredictedObservation, ...],
        gaps: tuple[EvidenceGap, ...],
        context: dict[str, Any],
    ) -> HypothesisResult:
        families = self._group_into_families(hypotheses)
        strongest = ''
        best_conf = -1.0
        for hyp in hypotheses:
            if hyp.confidence > best_conf:
                best_conf = hyp.confidence
                strongest = hyp.hypothesis_id
        avg_conf = (
            sum(h.confidence for h in hypotheses) / len(hypotheses)
            if hypotheses else 0.0
        )
        return HypothesisResult(
            hypotheses=tuple(hypotheses),
            families=tuple(families),
            evidence_gaps=gaps,
            predictions=predictions,
            strongest_hypothesis=strongest,
            overall_confidence=avg_conf,
            processing_metadata=context,
        )

    def _group_into_families(
        self,
        hypotheses: list[HypothesisObject],
    ) -> list[HypothesisFamily]:
        if not hypotheses:
            return []
        origin_groups: dict[str, list[str]] = {}
        for hyp in hypotheses:
            origin_groups.setdefault(hyp.originating_context, []).append(hyp.hypothesis_id)
        families: list[HypothesisFamily] = []
        for origin, ids in origin_groups.items():
            families.append(HypothesisFamily(
                family_id=f'fam_{uuid.uuid4().hex[:8]}',
                family_name=f"{origin} family",
                hypothesis_ids=tuple(ids),
                family_confidence=0.5,
            ))
        return families
