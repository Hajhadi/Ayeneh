"""INF-04 Contradiction Resolver Engine.

8-phase pipeline for detecting and resolving contradictions between
cognitive objects:

1. Context Collection
2. Cognitive Object Collection
3. Consistency Analysis
4. Contradiction Detection
5. Conflict Classification
6. Evidence Comparison
7. Resolution Strategy
8. Updated Cognitive Model
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.inf.contradiction.classification import ConflictClassifier
from ayeneh.inf.contradiction.types import (
    CONTRADICTION_CATEGORIES,
    RESOLUTION_STRATEGIES,
    ConflictClassification,
    ContradictionObject,
    ContradictionResult,
    EvidenceComparison,
    ResolutionPlan,
)

logger = structlog.get_logger(__name__)


class ContradictionResolver:
    """Detects and manages contradictions between cognitive objects (INF-04)."""

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._classifier = ConflictClassifier()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        cognitive_objects: list[Any],
        context: dict[str, Any] | None = None,
    ) -> ContradictionResult:
        """Run the full 8-phase contradiction pipeline."""
        ctx = context or {}
        logger.info('contradiction_pipeline_start', object_count=len(cognitive_objects))

        # Phase 1 – Context Collection
        enriched_ctx = self._phase_context_collection(ctx)

        # Phase 2 – Cognitive Object Collection
        collected = self._phase_object_collection(cognitive_objects, enriched_ctx)

        # Phase 3 – Consistency Analysis
        consistency_score = self._phase_consistency_analysis(collected)

        # Phase 4 – Contradiction Detection
        contradiction_pairs = self._phase_contradiction_detection(collected, enriched_ctx)

        # Phase 5 – Conflict Classification
        classifications = self._phase_conflict_classification(contradiction_pairs)

        # Phase 6 – Evidence Comparison
        comparisons = self._phase_evidence_comparison(contradiction_pairs)

        # Phase 7 – Resolution Strategy
        resolution_plans = self._phase_resolution_strategy(
            contradiction_pairs, classifications, comparisons,
        )

        # Phase 8 – Updated Cognitive Model
        result = self._phase_updated_model(
            contradiction_pairs, classifications, comparisons,
            resolution_plans, consistency_score, enriched_ctx,
        )

        logger.info(
            'contradiction_pipeline_end',
            contradictions_found=len(result.contradictions),
            overall_consistency=result.overall_consistency,
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1 – Context Collection
    # ------------------------------------------------------------------

    def _phase_context_collection(self, context: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(context)
        enriched.setdefault('analysis_timestamp', uuid.uuid4().hex)
        enriched.setdefault('categories', list(CONTRADICTION_CATEGORIES))
        enriched.setdefault('strategies', list(RESOLUTION_STRATEGIES))
        logger.debug('phase_1_context_collected', keys=list(enriched.keys()))
        return enriched

    # ------------------------------------------------------------------
    # Phase 2 – Cognitive Object Collection
    # ------------------------------------------------------------------

    def _phase_object_collection(
        self,
        objects: list[Any],
        context: dict[str, Any],
    ) -> list[Any]:
        validated: list[Any] = []
        for obj in objects:
            if obj is None:
                continue
            if hasattr(obj, '__dict__') or isinstance(obj, dict):
                validated.append(obj)
        context['validated_count'] = len(validated)
        logger.debug('phase_2_objects_collected', count=len(validated))
        return validated

    # ------------------------------------------------------------------
    # Phase 3 – Consistency Analysis
    # ------------------------------------------------------------------

    def _phase_consistency_analysis(self, objects: list[Any]) -> float:
        if len(objects) < 2:
            return 1.0
        total_pairs = 0
        consistent_pairs = 0
        for i in range(len(objects)):
            for j in range(i + 1, len(objects)):
                total_pairs += 1
                if self._pair_consistent(objects[i], objects[j]):
                    consistent_pairs += 1
        score = consistent_pairs / total_pairs if total_pairs > 0 else 1.0
        logger.debug('phase_3_consistency', score=round(score, 4))
        return score

    def _pair_consistent(self, obj_a: Any, obj_b: Any) -> bool:
        type_a = self._extract_type(obj_a)
        type_b = self._extract_type(obj_b)
        if type_a and type_b and type_a != type_b:
            return True
        if type_a == type_b and type_a:
            stmt_a = self._extract_statement(obj_a)
            stmt_b = self._extract_statement(obj_b)
            if stmt_a and stmt_b and stmt_a != stmt_b:
                return False
        return True

    # ------------------------------------------------------------------
    # Phase 4 – Contradiction Detection
    # ------------------------------------------------------------------

    def _phase_contradiction_detection(
        self,
        objects: list[Any],
        context: dict[str, Any],
    ) -> list[tuple[Any, Any, ContradictionObject]]:
        pairs: list[tuple[Any, Any, ContradictionObject]] = []
        for i in range(len(objects)):
            for j in range(i + 1, len(objects)):
                obj_a, obj_b = objects[i], objects[j]
                if self._is_contradictory(obj_a, obj_b):
                    contra = self._build_contradiction(obj_a, obj_b)
                    pairs.append((obj_a, obj_b, contra))
        context['contradiction_count'] = len(pairs)
        logger.debug('phase_4_detection', contradictions=len(pairs))
        return pairs

    def _is_contradictory(self, obj_a: Any, obj_b: Any) -> bool:
        type_a = self._extract_type(obj_a)
        type_b = self._extract_type(obj_b)
        if type_a and type_b and type_a == type_b:
            stmt_a = self._extract_statement(obj_a)
            stmt_b = self._extract_statement(obj_b)
            if stmt_a and stmt_b and stmt_a != stmt_b:
                return True
        evid_a = getattr(obj_a, 'contradictions', ()) or ()
        obj_id_b = getattr(obj_b, 'inference_id', '') or getattr(obj_b, 'contradiction_id', '')
        if obj_id_b and obj_id_b in evid_a:
            return True
        evid_b = getattr(obj_b, 'contradictions', ()) or ()
        obj_id_a = getattr(obj_a, 'inference_id', '') or getattr(obj_a, 'contradiction_id', '')
        if obj_id_a and obj_id_a in evid_b:
            return True
        return False

    def _build_contradiction(self, obj_a: Any, obj_b: Any) -> ContradictionObject:
        id_a = getattr(obj_a, 'inference_id', '') or id(obj_a).__str__()
        id_b = getattr(obj_b, 'inference_id', '') or id(obj_b).__str__()
        conf_a = getattr(obj_a, 'confidence', 0.0)
        conf_b = getattr(obj_b, 'confidence', 0.0)
        severity = abs(conf_a - conf_b)
        return ContradictionObject(
            contradiction_id=f'contra_{uuid.uuid4().hex[:12]}',
            conflicting_objects=(id_a, id_b),
            conflict_type=self._extract_type(obj_a) or 'behavior',
            supporting_evidence=tuple(getattr(obj_a, 'supporting_evidence', ()) or ()),
            contradictory_evidence=tuple(getattr(obj_b, 'supporting_evidence', ()) or ()),
            contexts=(),
            confidence=(conf_a + conf_b) / 2.0,
            severity=severity,
            current_status='detected',
        )

    # ------------------------------------------------------------------
    # Phase 5 – Conflict Classification
    # ------------------------------------------------------------------

    def _phase_conflict_classification(
        self,
        pairs: list[tuple[Any, Any, ContradictionObject]],
    ) -> tuple[ConflictClassification, ...]:
        classifications: list[ConflictClassification] = []
        for obj_a, obj_b, _contra in pairs:
            result = self._classifier.classify(obj_a, obj_b)
            classifications.append(result['classification'])
        logger.debug('phase_5_classified', count=len(classifications))
        return tuple(classifications)

    # ------------------------------------------------------------------
    # Phase 6 – Evidence Comparison
    # ------------------------------------------------------------------

    def _phase_evidence_comparison(
        self,
        pairs: list[tuple[Any, Any, ContradictionObject]],
    ) -> tuple[EvidenceComparison, ...]:
        comparisons: list[EvidenceComparison] = []
        for obj_a, obj_b, _contra in pairs:
            id_a = getattr(obj_a, 'inference_id', '') or id(obj_a).__str__()
            id_b = getattr(obj_b, 'inference_id', '') or id(obj_b).__str__()
            evid_a = tuple(getattr(obj_a, 'supporting_evidence', ()) or ())
            evid_b = tuple(getattr(obj_b, 'supporting_evidence', ()) or ())
            conf_a = getattr(obj_a, 'confidence', 0.0)
            conf_b = getattr(obj_b, 'confidence', 0.0)
            if conf_a > conf_b:
                winner = 'a'
            elif conf_b > conf_a:
                winner = 'b'
            else:
                winner = 'tie'
            comparisons.append(EvidenceComparison(
                object_a_id=id_a,
                object_b_id=id_b,
                supporting_a=evid_a,
                supporting_b=evid_b,
                quality_a=conf_a,
                quality_b=conf_b,
                volume_a=len(evid_a),
                volume_b=len(evid_b),
                winner=winner,
            ))
        logger.debug('phase_6_compared', count=len(comparisons))
        return tuple(comparisons)

    # ------------------------------------------------------------------
    # Phase 7 – Resolution Strategy
    # ------------------------------------------------------------------

    def _phase_resolution_strategy(
        self,
        pairs: list[tuple[Any, Any, ContradictionObject]],
        classifications: tuple[ConflictClassification, ...],
        comparisons: tuple[EvidenceComparison, ...],
    ) -> tuple[ResolutionPlan, ...]:
        plans: list[ResolutionPlan] = []
        for idx, (_obj_a, _obj_b, contra) in enumerate(pairs):
            cls = classifications[idx] if idx < len(classifications) else ConflictClassification()
            comp = comparisons[idx] if idx < len(comparisons) else EvidenceComparison()
            strategy = self._select_strategy(cls, comp)
            steps = self._build_resolution_steps(strategy, cls)
            plans.append(ResolutionPlan(
                strategy=strategy,
                steps=tuple(steps),
                affected_objects=contra.conflicting_objects,
                expected_outcome=f'Resolve {cls.category} conflict via {strategy}',
                confidence=1.0 - cls.identity_impact * 0.3,
                safety_check='safe' if cls.severity in ('negligible', 'minor') else 'caution',
            ))
        logger.debug('phase_7_planned', count=len(plans))
        return tuple(plans)

    def _select_strategy(self, cls: ConflictClassification, comp: EvidenceComparison) -> str:
        if cls.category == 'identity':
            return 'identity_restructuring'
        if cls.category == 'belief':
            return 'belief_revision'
        if cls.category == 'narrative':
            return 'narrative_revision'
        if cls.category in ('goal', 'planning'):
            return 'goal_prioritization'
        if comp.winner != 'tie':
            return 'evidence_accumulation'
        if cls.scope == 'local':
            return 'context_differentiation'
        return 'deferred_resolution'

    def _build_resolution_steps(self, strategy: str, cls: ConflictClassification) -> list[str]:
        base = [f'Apply {strategy} to {cls.category} conflict']
        if cls.severity in ('major', 'critical'):
            base.append('Escalate for expert review')
        if cls.identity_impact > 0.5:
            base.append('Assess identity-level impact')
        base.append('Verify resolution correctness')
        return base

    # ------------------------------------------------------------------
    # Phase 8 – Updated Cognitive Model
    # ------------------------------------------------------------------

    def _phase_updated_model(
        self,
        pairs: list[tuple[Any, Any, ContradictionObject]],
        classifications: tuple[ConflictClassification, ...],
        comparisons: tuple[EvidenceComparison, ...],
        plans: tuple[ResolutionPlan, ...],
        consistency_score: float,
        context: dict[str, Any],
    ) -> ContradictionResult:
        contradictions = tuple(c for _, _, c in pairs)
        resolved_ids: list[str] = []
        persistent_ids: list[str] = []
        for idx, plan in enumerate(plans):
            if plan.strategy == 'deferred_resolution':
                persistent_ids.append(contradictions[idx].contradiction_id)
            else:
                resolved_ids.append(contradictions[idx].contradiction_id)

        return ContradictionResult(
            contradictions=contradictions,
            classifications=classifications,
            evidence_comparisons=comparisons,
            resolution_plans=plans,
            resolved_ids=tuple(resolved_ids),
            persistent_ids=tuple(persistent_ids),
            overall_consistency=consistency_score,
            processing_metadata=context,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_type(obj: Any) -> str:
        return getattr(obj, 'inference_type', '') or getattr(obj, 'conflict_type', '') or ''

    @staticmethod
    def _extract_statement(obj: Any) -> str:
        return getattr(obj, 'statement', '') or ''
