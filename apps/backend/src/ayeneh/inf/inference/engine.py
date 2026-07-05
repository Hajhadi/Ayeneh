"""INF-01 Inference Engine.

Evidence-based reasoning engine implementing an 8-phase pipeline:
1. Context Collection
2. Evidence Assembly
3. Multi-Evidence Integration
4. Inference Construction
5. Confidence Estimation
6. Reality Calibration
7. Hypothesis Generation
8. Publication
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.inf.inference.types import (
    INFERENCE_TYPES,
    EVIDENCE_STANDARDS,
    CompetingHypothesis,
    ContradictionRecord,
    EvidenceQualityAssessment,
    InferenceObject,
    InferenceResult,
    ReasoningStep,
)

logger = structlog.get_logger(__name__)


class InferenceEngine:
    """Evidence-based reasoning engine (INF-01).

    Pipeline:
        1. Context Collection — gather context from memories and graph
        2. Evidence Assembly — collect and filter supporting evidence
        3. Multi-Evidence Integration — combine multiple evidence sources
        4. Inference Construction — build inference statements
        5. Confidence Estimation — assign confidence scores
        6. Reality Calibration — check inferences against reality
        7. Hypothesis Generation — create competing hypotheses
        8. Publication — finalize and return results
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._inferences: dict[str, InferenceObject] = {}

    def process(
        self,
        context: dict[str, Any],
        memories: list[dict[str, Any]],
        graph: Any = None,
    ) -> InferenceResult:
        """Run the full INF-01 pipeline.

        Parameters
        ----------
        context:
            Context dict with ``'context_id'``, ``'domain'``, and optional
            ``'query'`` keys.
        memories:
            List of memory dicts with ``'id'``, ``'content'``, and optional
            ``'type'`` keys.
        graph:
            Optional knowledge graph object for relationship data.
        """
        logger.info(
            'inf.inference.pipeline_started',
            context_id=context.get('context_id', ''),
            memory_count=len(memories),
        )

        # Phase 1: Context Collection
        collected_context = self._phase_context_collection(context, memories)

        # Phase 2: Evidence Assembly
        evidence = self._phase_evidence_assembly(collected_context, memories)

        # Phase 3: Multi-Evidence Integration
        integrated = self._phase_evidence_integration(evidence)

        # Phase 4: Inference Construction
        inferences = self._phase_inference_construction(
            collected_context, integrated,
        )

        # Phase 5: Confidence Estimation
        with_confidence = self._phase_confidence_estimation(
            inferences, integrated,
        )

        # Phase 6: Reality Calibration
        calibrated = self._phase_reality_calibration(with_confidence)

        # Phase 7: Hypothesis Generation
        hypotheses, contradictions = self._phase_hypothesis_generation(calibrated)

        # Phase 8: Publication
        result = self._phase_publication(
            calibrated, evidence, integrated,
            hypotheses, contradictions,
        )

        logger.info(
            'inf.inference.pipeline_completed',
            inference_count=len(result.inferences),
            overall_confidence=result.overall_confidence,
        )

        return result

    # ------------------------------------------------------------------
    # Phase 1: Context Collection
    # ------------------------------------------------------------------

    def _phase_context_collection(
        self,
        context: dict[str, Any],
        memories: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Collect and structure the context for inference."""
        logger.debug('inf.inference.phase1_context_collection')

        collected = {
            'context_id': context.get('context_id', ''),
            'domain': context.get('domain', 'general'),
            'query': context.get('query', ''),
            'relevant_memories': [
                m for m in memories if m.get('relevance', 0.5) > 0.3
            ],
            'temporal_range': context.get('temporal_range', {}),
            'speaker': context.get('speaker', ''),
        }
        return collected

    # ------------------------------------------------------------------
    # Phase 2: Evidence Assembly
    # ------------------------------------------------------------------

    def _phase_evidence_assembly(
        self,
        context: dict[str, Any],
        memories: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Assemble evidence from memories and context."""
        logger.debug('inf.inference.phase2_evidence_assembly')

        evidence_items: list[dict[str, Any]] = []
        for memory in memories:
            evidence_items.append({
                'evidence_id': memory.get('id', str(uuid.uuid4())),
                'content': memory.get('content', ''),
                'source': memory.get('source', 'memory'),
                'confidence': memory.get('confidence', 0.5),
                'category': memory.get('category', 'observation'),
                'timestamp': memory.get('timestamp', ''),
                'context_id': context.get('context_id', ''),
            })
        return evidence_items

    # ------------------------------------------------------------------
    # Phase 3: Multi-Evidence Integration
    # ------------------------------------------------------------------

    def _phase_evidence_integration(
        self,
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Integrate multiple evidence sources."""
        logger.debug('inf.inference.phase3_evidence_integration', count=len(evidence))

        if not evidence:
            return {
                'integrated_evidence': (),
                'evidence_quality': EvidenceQualityAssessment(),
                'consensus_score': 0.0,
            }

        total_confidence = sum(e.get('confidence', 0.5) for e in evidence)
        avg_confidence = total_confidence / len(evidence) if evidence else 0.0

        # Simple consistency check: how many evidence items agree
        categories = [e.get('category', '') for e in evidence]
        unique_categories = set(categories)
        consistency = 1.0 - (len(unique_categories) / max(len(categories), 1))

        quality = EvidenceQualityAssessment(
            directness=min(avg_confidence + 0.1, 1.0),
            specificity=0.5,
            temporal_proximity=0.5,
            consistency=consistency,
            source_reliability=avg_confidence,
        )

        return {
            'integrated_evidence': tuple(evidence),
            'evidence_quality': quality,
            'consensus_score': consistency,
            'total_evidence_count': len(evidence),
        }

    # ------------------------------------------------------------------
    # Phase 4: Inference Construction
    # ------------------------------------------------------------------

    def _phase_inference_construction(
        self,
        context: dict[str, Any],
        integrated: dict[str, Any],
    ) -> list[InferenceObject]:
        """Construct inference statements from integrated evidence."""
        logger.debug('inf.inference.phase4_inference_construction')

        evidence = integrated.get('integrated_evidence', ())
        if not evidence:
            return []

        inferences: list[InferenceObject] = []
        evidence_ids = tuple(
            e.get('evidence_id', '') for e in evidence if e.get('evidence_id')
        )

        # Determine appropriate inference types for the domain
        domain = context.get('domain', 'general')
        applicable_types = self._determine_applicable_types(domain, evidence)

        for inf_type in applicable_types:
            statement = self._construct_statement(inf_type, evidence, context)
            if statement:
                inf = InferenceObject(
                    inference_id=str(uuid.uuid4()),
                    context_id=context.get('context_id', ''),
                    inference_type=inf_type,
                    statement=statement,
                    supporting_evidence=evidence_ids,
                    evidence_quality=integrated.get('evidence_quality', EvidenceQualityAssessment()).overall(),
                    reasoning_chain=(
                        {
                            'step': 'evidence_integration',
                            'evidence_count': len(evidence_ids),
                            'consensus': integrated.get('consensus_score', 0.0),
                        },
                    ),
                )
                inferences.append(inf)

        return inferences

    def _determine_applicable_types(
        self,
        domain: str,
        evidence: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    ) -> list[str]:
        """Determine which inference types are applicable."""
        categories = {e.get('category', '') for e in evidence}

        applicable = ['descriptive']
        if 'behavior' in categories or 'action' in categories:
            applicable.append('behavioral')
        if 'statement' in categories or 'claim' in categories:
            applicable.append('causal')
        if 'identity' in categories:
            applicable.append('identity')
        if 'narrative' in categories:
            applicable.append('narrative')
        if 'goal' in categories:
            applicable.append('goal')

        return applicable if applicable else ['descriptive']

    def _construct_statement(
        self,
        inference_type: str,
        evidence: tuple[dict[str, Any], ...] | list[dict[str, Any]],
        context: dict[str, Any],
    ) -> str:
        """Construct a human-readable inference statement."""
        if not evidence:
            return ''

        evidence_texts = [e.get('content', '') for e in evidence[:3]]
        combined = '; '.join(t for t in evidence_texts if t)

        type_prefixes = {
            'descriptive': 'Based on the available evidence',
            'behavioral': 'The behavioral pattern suggests',
            'causal': 'There appears to be a causal relationship',
            'identity': 'This suggests a core aspect of identity',
            'narrative': 'A narrative pattern emerges',
            'goal': 'This indicates a goal orientation',
            'planning': 'The planning pattern suggests',
            'predictive': 'The predictive indicators suggest',
            'meta_cognitive': 'Meta-cognitive analysis reveals',
            'reality_calibration': 'Reality calibration indicates',
        }

        prefix = type_prefixes.get(inference_type, 'The evidence suggests')
        return f"{prefix}: {combined}" if combined else ''

    # ------------------------------------------------------------------
    # Phase 5: Confidence Estimation
    # ------------------------------------------------------------------

    def _phase_confidence_estimation(
        self,
        inferences: list[InferenceObject],
        integrated: dict[str, Any],
    ) -> list[InferenceObject]:
        """Estimate confidence for each inference."""
        logger.debug('inf.inference.phase5_confidence_estimation', count=len(inferences))

        evidence_quality = integrated.get('evidence_quality', EvidenceQualityAssessment())
        overall_quality = evidence_quality.overall()

        estimated: list[InferenceObject] = []
        for inf in inferences:
            standard = EVIDENCE_STANDARDS.get(inf.inference_type, 0.5)
            base_confidence = inf.evidence_quality * 0.6 + overall_quality * 0.4
            confidence = min(base_confidence, 1.0) * standard

            estimated_inf = InferenceObject(
                inference_id=inf.inference_id,
                context_id=inf.context_id,
                inference_type=inf.inference_type,
                statement=inf.statement,
                supporting_evidence=inf.supporting_evidence,
                evidence_quality=inf.evidence_quality,
                reasoning_chain=inf.reasoning_chain,
                confidence=round(confidence, 4),
                competing_hypotheses=inf.competing_hypotheses,
                contradictions=inf.contradictions,
                associated_memories=inf.associated_memories,
                associated_graph_nodes=inf.associated_graph_nodes,
                version_history=inf.version_history,
                explainability_metadata=inf.explainability_metadata,
                creation_timestamp=inf.creation_timestamp,
            )
            estimated.append(estimated_inf)

        return estimated

    # ------------------------------------------------------------------
    # Phase 6: Reality Calibration
    # ------------------------------------------------------------------

    def _phase_reality_calibration(
        self,
        inferences: list[InferenceObject],
    ) -> list[InferenceObject]:
        """Calibrate inferences against reality constraints."""
        logger.debug('inf.inference.phase6_reality_calibration', count=len(inferences))

        calibrated: list[InferenceObject] = []
        for inf in inferences:
            # Reduce confidence for overly strong claims on limited evidence
            adjusted_confidence = inf.confidence
            if len(inf.supporting_evidence) < 2 and adjusted_confidence > 0.7:
                adjusted_confidence *= 0.8

            calibrated_inf = InferenceObject(
                inference_id=inf.inference_id,
                context_id=inf.context_id,
                inference_type=inf.inference_type,
                statement=inf.statement,
                supporting_evidence=inf.supporting_evidence,
                evidence_quality=inf.evidence_quality,
                reasoning_chain=inf.reasoning_chain,
                confidence=round(adjusted_confidence, 4),
                competing_hypotheses=inf.competing_hypotheses,
                contradictions=inf.contradictions,
                associated_memories=inf.associated_memories,
                associated_graph_nodes=inf.associated_graph_nodes,
                version_history=inf.version_history,
                explainability_metadata=inf.explainability_metadata,
                creation_timestamp=inf.creation_timestamp,
            )
            calibrated.append(calibrated_inf)

        return calibrated

    # ------------------------------------------------------------------
    # Phase 7: Hypothesis Generation
    # ------------------------------------------------------------------

    def _phase_hypothesis_generation(
        self,
        inferences: list[InferenceObject],
    ) -> tuple[list[CompetingHypothesis], list[ContradictionRecord]]:
        """Generate competing hypotheses and detect contradictions."""
        logger.debug('inf.inference.phase7_hypothesis_generation', count=len(inferences))

        hypotheses: list[CompetingHypothesis] = []
        contradictions: list[ContradictionRecord] = []

        for inf in inferences:
            if inf.confidence < 0.8:
                alt = CompetingHypothesis(
                    hypothesis_id=str(uuid.uuid4()),
                    statement=f"Alternative to: {inf.statement}",
                    confidence=round(1.0 - inf.confidence, 4),
                    supporting_evidence=inf.supporting_evidence,
                    explanation='Lower confidence allows for alternative interpretation',
                )
                hypotheses.append(alt)

        # Check for contradictions between inferences
        for i, inf_a in enumerate(inferences):
            for inf_b in inferences[i + 1:]:
                if inf_a.inference_type == inf_b.inference_type:
                    if inf_a.confidence > 0.5 and inf_b.confidence > 0.5:
                        if inf_a.statement != inf_b.statement:
                            contradictions.append(
                                ContradictionRecord(
                                    contradiction_id=str(uuid.uuid4()),
                                    inference_id_a=inf_a.inference_id,
                                    inference_id_b=inf_b.inference_id,
                                    description=(
                                        f"Conflicting {inf_a.inference_type} "
                                        f"inferences"
                                    ),
                                    severity=abs(inf_a.confidence - inf_b.confidence),
                                ),
                            )

        return hypotheses, contradictions

    # ------------------------------------------------------------------
    # Phase 8: Publication
    # ------------------------------------------------------------------

    def _phase_publication(
        self,
        inferences: list[InferenceObject],
        evidence: list[dict[str, Any]],
        integrated: dict[str, Any],
        hypotheses: list[CompetingHypothesis],
        contradictions: list[ContradictionRecord],
    ) -> InferenceResult:
        """Finalize and publish the inference result."""
        logger.debug('inf.inference.phase8_publication', count=len(inferences))

        # Store inferences
        for inf in inferences:
            self._inferences[inf.inference_id] = inf

        # Calculate overall confidence
        if inferences:
            overall = sum(i.confidence for i in inferences) / len(inferences)
        else:
            overall = 0.0

        # Build reasoning steps
        steps = tuple(
            ReasoningStep(
                step_id=str(uuid.uuid4()),
                description=f"Processed {inf.inference_type} inference",
                input_evidence=inf.supporting_evidence,
                output_conclusion=inf.statement,
                confidence=inf.confidence,
                reasoning_method='evidence_integration',
            )
            for inf in inferences
        )

        calibration_notes: list[str] = []
        if contradictions:
            calibration_notes.append(
                f"Detected {len(contradictions)} contradiction(s)"
            )
        if hypotheses:
            calibration_notes.append(
                f"Generated {len(hypotheses)} competing hypothesis(es)"
            )

        return InferenceResult(
            inferences=tuple(inferences),
            evidence_assessment=integrated.get(
                'evidence_quality', EvidenceQualityAssessment(),
            ),
            reasoning_steps=steps,
            competing_hypotheses=tuple(hypotheses),
            contradictions=tuple(contradictions),
            calibration_notes=tuple(calibration_notes),
            overall_confidence=round(overall, 4),
            processing_metadata={
                'evidence_count': len(evidence),
                'inference_count': len(inferences),
                'hypothesis_count': len(hypotheses),
                'contradiction_count': len(contradictions),
            },
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_inference(self, inference_id: str) -> InferenceObject | None:
        """Retrieve an inference by ID."""
        return self._inferences.get(inference_id)

    def get_all_inferences(self) -> list[InferenceObject]:
        """Retrieve all stored inferences."""
        return list(self._inferences.values())
