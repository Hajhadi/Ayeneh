"""Meta-Cognition Engine — COG-16.

Models the person's relationship with their own thinking. Detects awareness
events, extracts meta-cognitive objects, tracks awareness levels, and
estimates cognitive transparency.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.cog.meta_cognition.awareness import (
    AwarenessLevelTracker,
    DeIdentificationTracker,
)
from ayeneh.cog.meta_cognition.types import (
    META_COGNITIVE_LIFECYCLE_STATES,
    AWARENESS_LEVELS,
    AwarenessEvent,
    CognitiveBias,
    CognitiveResource,
    CognitiveTransparency,
    MetaCognitiveObject,
    ObserverEpisode,
    RevisionStrategy,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetaCognitionResult:
    """Output of the COG-16 Meta-Cognition pipeline."""

    objects: tuple[MetaCognitiveObject, ...]
    awareness_levels: dict[str, Any]
    transparency: CognitiveTransparency
    de_identification: dict[str, Any]
    total_extracted: int
    processing_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    self_monitoring: dict[str, Any] = field(default_factory=dict)
    detected_biases: tuple[str, ...] = ()
    confidence_calibration: dict[str, Any] = field(default_factory=dict)
    recommended_strategy: str = ''
    resource_allocation: dict[str, Any] = field(default_factory=dict)
    error_awareness: dict[str, Any] = field(default_factory=dict)
    epistemic_governance: dict[str, Any] = field(default_factory=dict)
    architecture_supervision: dict[str, Any] = field(default_factory=dict)
    longitudinal_evaluation: dict[str, Any] = field(default_factory=dict)
    governance_adaptation: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# MetaCognitionEngine
# ---------------------------------------------------------------------------


class MetaCognitionEngine:
    """Models the person's relationship with their own thinking (COG-16).

    Pipeline phases:
        1. Experience → Automatic Cognition
        2. Pattern Recognition → Awareness Events
        3. Observation → Meta-Cognitive Objects
        4. Validation
        5. Awareness Level Tracking
        6. Transparency Estimation
        7. De-Identification Tracking
    """

    def __init__(self) -> None:
        self._objects: dict[str, MetaCognitiveObject] = {}
        self._episodes: list[ObserverEpisode] = []
        self._awareness_tracker = AwarenessLevelTracker()
        self._de_id_tracker = DeIdentificationTracker()
        self._bias_history: list[dict[str, Any]] = []
        self._error_history: list[dict[str, Any]] = []
        self._prediction_accuracy_history: list[float] = []
        self._reflection_usefulness_history: list[float] = []
        self._dialogue_continuity_history: list[float] = []
        self._governance_policies: dict[str, Any] = {
            'evidence_hierarchy_enforced': True,
            'uncertainty_protection_active': True,
            'premature_certainty_prevention': True,
        }
        self._resource_budgets: dict[str, float] = {
            CognitiveResource.WORKING_MEMORY.value: 1.0,
            CognitiveResource.INFERENCE_DEPTH.value: 1.0,
            CognitiveResource.GRAPH_TRAVERSAL.value: 1.0,
            CognitiveResource.REFLECTION_SCHEDULING.value: 1.0,
            CognitiveResource.PREDICTION_COMPLEXITY.value: 1.0,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        evidence: list[dict[str, Any]],
        reflections: list[dict[str, Any]] | None = None,
        narratives: list[dict[str, Any]] | None = None,
        beliefs: list[dict[str, Any]] | None = None,
        identity: list[dict[str, Any]] | None = None,
    ) -> MetaCognitionResult:
        """Run the full COG-16 pipeline.

        Stages:
            Experience → Automatic Cognition → Pattern Recognition →
            Observation → Differentiation → Awareness → Integration
        """
        logger.info(
            'cog.meta_cognition.pipeline_started',
            evidence_count=len(evidence),
            reflection_count=len(reflections) if reflections else 0,
        )

        reflections = reflections or []
        narratives = narratives or []
        beliefs = beliefs or []
        identity = identity or []

        events = self._detect_awareness_events(evidence, reflections)
        objects = self._extract_meta_cognitive_objects(events, narratives, beliefs, identity)
        validated = self._validate(objects)
        levels = self._track_awareness_levels(validated)
        transparency = self._estimate_transparency(narratives, beliefs, identity, reflections)
        de_id = self._track_de_identification(validated)

        # Part 2 — self-evaluation and governance pipeline
        self_monitoring = self._self_monitor(validated, reflections, narratives)
        biases = self._detect_biases(validated, evidence)
        calibr = self._calibrate_confidence(validated)
        strategy = self._select_strategy(validated, calibr)
        resources = self._manage_resources(validated)
        errors = self._track_errors(validated, evidence, reflections)
        governance = self._enforce_epistemic_governance(validated, evidence)
        supervision = self._supervise_architecture(narratives, beliefs, identity, reflections)
        longitudinal = self._self_evaluate_longitudinally()
        adapt_gov = self._adapt_governance(longitudinal, governance)

        result = MetaCognitionResult(
            objects=tuple(validated),
            awareness_levels=levels,
            transparency=transparency,
            de_identification=de_id,
            total_extracted=len(validated),
            self_monitoring=self_monitoring,
            detected_biases=tuple(biases),
            confidence_calibration=calibr,
            recommended_strategy=strategy,
            resource_allocation=resources,
            error_awareness=errors,
            epistemic_governance=governance,
            architecture_supervision=supervision,
            longitudinal_evaluation=longitudinal,
            governance_adaptation=adapt_gov,
        )

        logger.info(
            'cog.meta_cognition.pipeline_completed',
            total_extracted=result.total_extracted,
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1-2: Detect awareness events
    # ------------------------------------------------------------------

    def _detect_awareness_events(
        self,
        evidence: list[dict[str, Any]],
        reflections: list[dict[str, Any]],
    ) -> list[AwarenessEvent]:
        """Detect awareness events from evidence and reflections."""
        events: list[AwarenessEvent] = []

        for ev in evidence:
            if self._is_meta_cognitive(ev):
                level = self._infer_awareness_level(ev)
                events.append(AwarenessEvent(
                    event_id=ev.get('identifier', str(uuid.uuid4())),
                    recognized_process=ev.get('text', ev.get('original_text', '')),
                    awareness_level=level,
                    evidence=(ev.get('identifier', ''),),
                ))

        for ref in reflections:
            level = self._infer_awareness_level(ref)
            events.append(AwarenessEvent(
                event_id=ref.get('identifier', str(uuid.uuid4())),
                recognized_process=ref.get('text', ref.get('reflection', '')),
                awareness_level=level,
                evidence=(ref.get('identifier', ''),),
            ))

        logger.info('cog.meta_cognition.events_detected', count=len(events))
        return events

    # ------------------------------------------------------------------
    # Phase 3: Extract meta-cognitive objects
    # ------------------------------------------------------------------

    def _extract_meta_cognitive_objects(
        self,
        events: list[AwarenessEvent],
        narratives: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
        identity: list[dict[str, Any]],
    ) -> list[MetaCognitiveObject]:
        """Extract meta-cognitive objects from awareness events."""
        objects: list[MetaCognitiveObject] = []

        for event in events:
            oid = str(uuid.uuid4())
            narr_refs = self._find_related_narratives(event, narratives)
            belief_refs = self._find_related_beliefs(event, beliefs)
            identity_refs = self._find_related_identity(event, identity)
            behavioral_effects = self._extract_behavioral_effects(event)

            obj = MetaCognitiveObject(
                identifier=oid,
                observed_cognitive_process=event.recognized_process,
                awareness_description=event.recognized_process,
                awareness_level=event.awareness_level,
                confidence=min(1.0, event.awareness_level * 0.2),
                stability=min(1.0, event.awareness_level * 0.15),
                context=event.recognized_process[:100],
                supporting_evidence=event.evidence,
                observed_behavioral_effects=tuple(behavioral_effects),
                associated_narratives=tuple(narr_refs),
                associated_beliefs=tuple(belief_refs),
            )
            objects.append(obj)
            self._objects[oid] = obj

        return objects

    # ------------------------------------------------------------------
    # Phase 4: Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(objects: list[MetaCognitiveObject]) -> list[MetaCognitiveObject]:
        """Validate meta-cognitive objects."""
        validated: list[MetaCognitiveObject] = []
        for obj in objects:
            if not obj.observed_cognitive_process.strip():
                continue
            if obj.awareness_level not in AWARENESS_LEVELS:
                continue
            validated.append(MetaCognitiveObject(
                identifier=obj.identifier,
                observed_cognitive_process=obj.observed_cognitive_process,
                awareness_description=obj.awareness_description,
                awareness_level=obj.awareness_level,
                confidence=obj.confidence,
                stability=obj.stability,
                context=obj.context,
                supporting_evidence=obj.supporting_evidence,
                supporting_conversations=obj.supporting_conversations,
                observed_behavioral_effects=obj.observed_behavioral_effects,
                associated_reflections=obj.associated_reflections,
                associated_narratives=obj.associated_narratives,
                associated_beliefs=obj.associated_beliefs,
                lifecycle_state='provisional',
            ))
        return validated

    # ------------------------------------------------------------------
    # Phase 5: Awareness level tracking
    # ------------------------------------------------------------------

    def _track_awareness_levels(
        self, objects: list[MetaCognitiveObject],
    ) -> dict[str, Any]:
        """Track awareness level distribution and progression."""
        return self._awareness_tracker.track([])

    # ------------------------------------------------------------------
    # Phase 6: Transparency estimation
    # ------------------------------------------------------------------

    def _estimate_transparency(
        self,
        narratives: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
        identity: list[dict[str, Any]],
        reflections: list[dict[str, Any]],
    ) -> CognitiveTransparency:
        """Estimate cognitive transparency across domains."""
        narrative_vis = self._compute_domain_visibility(narratives, ('text', 'summary'))
        belief_vis = self._compute_domain_visibility(beliefs, ('belief_statement',))
        identity_vis = self._compute_domain_visibility(identity, ('identity_statement',))
        reflection_quality = min(1.0, len(reflections) * 0.15)

        behavioral_vis = min(1.0, (narrative_vis + belief_vis) * 0.3)
        decision_vis = min(1.0, (belief_vis + identity_vis) * 0.3)
        prediction_vis = min(1.0, reflection_quality * 0.5 + narrative_vis * 0.3)

        overall = (
            narrative_vis * 0.2
            + belief_vis * 0.2
            + identity_vis * 0.15
            + behavioral_vis * 0.1
            + decision_vis * 0.1
            + prediction_vis * 0.1
            + reflection_quality * 0.15
        )

        return CognitiveTransparency(
            narrative_visibility=narrative_vis,
            belief_visibility=belief_vis,
            identity_visibility=identity_vis,
            behavioral_visibility=behavioral_vis,
            decision_visibility=decision_vis,
            prediction_visibility=prediction_vis,
            reflection_quality=reflection_quality,
            overall_transparency=round(min(1.0, overall), 4),
        )

    # ------------------------------------------------------------------
    # Phase 7: De-identification tracking
    # ------------------------------------------------------------------

    def _track_de_identification(
        self, objects: list[MetaCognitiveObject],
    ) -> dict[str, Any]:
        """Track de-identification from cognitive content."""
        return self._de_id_tracker.track(objects)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_meta_cognitive(ev: dict[str, Any]) -> bool:
        """Check if evidence contains meta-cognitive content."""
        ev_type = ev.get('type', ev.get('category', '')).lower()
        meta_types = {'meta_cognitive_report', 'reflection'}
        if ev_type in meta_types:
            return True
        text = ev.get('text', ev.get('original_text', '')).lower()
        meta_keywords = [
            'i notice', 'i realise', 'i realize', 'i observe',
            'i am aware', 'i can see', 'i recognize', 'i understand',
            'thinking about', 'my mind', 'my thoughts', 'i catch myself',
        ]
        return any(kw in text for kw in meta_keywords)

    @staticmethod
    def _infer_awareness_level(item: dict[str, Any]) -> int:
        """Infer awareness level from evidence content."""
        explicit_level = item.get('awareness_level')
        if isinstance(explicit_level, int) and 0 <= explicit_level <= 5:
            return explicit_level

        text = item.get('text', item.get('reflection', item.get('original_text', ''))).lower()
        if any(kw in text for kw in ('i realise', 'i realize', 'i notice', 'i observe')):
            return 2
        if any(kw in text for kw in ('i am aware', 'i can see', 'i understand')):
            return 3
        if any(kw in text for kw in ('i used to', 'looking back', 'in retrospect')):
            return 1
        return 1

    @staticmethod
    def _find_related_narratives(
        event: AwarenessEvent,
        narratives: list[dict[str, Any]],
    ) -> list[str]:
        """Find narratives related to an awareness event."""
        event_words = set(event.recognized_process.lower().split())
        related: list[str] = []
        for narr in narratives:
            narr_text = narr.get('text', narr.get('summary', '')).lower()
            narr_words = set(narr_text.split())
            if event_words & narr_words:
                related.append(narr.get('identifier', ''))
        return related

    @staticmethod
    def _find_related_beliefs(
        event: AwarenessEvent,
        beliefs: list[dict[str, Any]],
    ) -> list[str]:
        """Find beliefs related to an awareness event."""
        event_words = set(event.recognized_process.lower().split())
        related: list[str] = []
        for belief in beliefs:
            belief_text = belief.get('belief_statement', '').lower()
            belief_words = set(belief_text.split())
            if event_words & belief_words:
                related.append(belief.get('identifier', ''))
        return related

    @staticmethod
    def _find_related_identity(
        event: AwarenessEvent,
        identity: list[dict[str, Any]],
    ) -> list[str]:
        """Find identity components related to an awareness event."""
        event_words = set(event.recognized_process.lower().split())
        related: list[str] = []
        for ic in identity:
            ic_text = ic.get('identity_statement', '').lower()
            ic_words = set(ic_text.split())
            if event_words & ic_words:
                related.append(ic.get('identifier', ''))
        return related

    @staticmethod
    def _extract_behavioral_effects(event: AwarenessEvent) -> list[str]:
        """Extract behavioral effects from an awareness event."""
        text = event.recognized_process.lower()
        effects: list[str] = []
        if any(kw in text for kw in ('changed', 'shift', 'different', 'adjust')):
            effects.append('behavioral_change_detected')
        if any(kw in text for kw in ('avoid', 'resist', 'suppress', 'control')):
            effects.append('avoidance_pattern_detected')
        if any(kw in text for kw in ('approach', 'engage', 'pursue', 'seek')):
            effects.append('approach_pattern_detected')
        return effects

    @staticmethod
    def _compute_domain_visibility(
        items: list[dict[str, Any]],
        text_keys: tuple[str, ...],
    ) -> float:
        """Compute visibility score for a cognitive domain."""
        if not items:
            return 0.0
        meta_count = 0
        for item in items:
            for key in text_keys:
                text = item.get(key, '').lower()
                meta_keywords = ('i notice', 'i realise', 'i realize', 'i observe', 'i am aware')
                if any(kw in text for kw in meta_keywords):
                    meta_count += 1
                    break
        return min(1.0, meta_count * 0.2)

    # ------------------------------------------------------------------
    # Phase 8: Self-monitoring
    # ------------------------------------------------------------------

    def _self_monitor(
        self,
        objects: list[MetaCognitiveObject],
        reflections: list[dict[str, Any]],
        narratives: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Monitor memory retrieval, inference quality, dialogue quality,
        prediction accuracy, reflection quality, reality calibration,
        and decision support.
        """
        memory_retrieval = min(1.0, len(objects) * 0.15) if objects else 0.0
        inference_quality = (
            sum(o.reasoning_quality for o in objects) / len(objects)
            if objects else 0.0
        )
        dialogue_quality = min(1.0, len(narratives) * 0.2) if narratives else 0.0
        prediction_accuracy = (
            self._prediction_accuracy_history[-1]
            if self._prediction_accuracy_history else 0.0
        )
        reflection_quality = min(1.0, len(reflections) * 0.2) if reflections else 0.0
        reality_calibration = (
            sum(o.confidence_calibration for o in objects) / len(objects)
            if objects else 0.0
        )
        decision_support = (inference_quality + reality_calibration) / 2

        return {
            'memory_retrieval_quality': round(memory_retrieval, 4),
            'inference_quality': round(inference_quality, 4),
            'dialogue_quality': round(dialogue_quality, 4),
            'prediction_accuracy': round(prediction_accuracy, 4),
            'reflection_quality': round(reflection_quality, 4),
            'reality_calibration': round(reality_calibration, 4),
            'decision_support': round(decision_support, 4),
        }

    # ------------------------------------------------------------------
    # Phase 9: Bias detection
    # ------------------------------------------------------------------

    def _detect_biases(
        self,
        objects: list[MetaCognitiveObject],
        evidence: list[dict[str, Any]],
    ) -> list[str]:
        """Detect cognitive biases: confirmation, availability, anchoring,
        narrative bias, overgeneralization, premature closure, overconfidence.
        """
        detected: list[str] = []

        evidence_count = len(evidence)
        object_count = len(objects)

        # Overconfidence: high confidence with low evidence
        if objects:
            avg_conf = sum(o.confidence for o in objects) / object_count
            if avg_conf > 0.7 and evidence_count < 3:
                detected.append(CognitiveBias.OVERCONFIDENCE.value)

        # Premature closure: high confidence, low uncertainty
        if objects:
            avg_uncert = sum(o.remaining_uncertainty for o in objects) / object_count
            avg_conf = sum(o.confidence for o in objects) / object_count
            if avg_conf > 0.6 and avg_uncert < 0.2:
                detected.append(CognitiveBias.PREMATURE_CLOSURE.value)

        # Overgeneralization: few objects, high confidence
        if object_count <= 2 and objects:
            avg_conf = sum(o.confidence for o in objects) / object_count
            if avg_conf > 0.5:
                detected.append(CognitiveBias.OVERGENERALIZATION.value)

        # Confirmation bias: low evidence diversity
        all_evidence: set[str] = set()
        for obj in objects:
            all_evidence.update(obj.supporting_evidence)
        if objects and len(all_evidence) < 2:
            detected.append(CognitiveBias.CONFIRMATION.value)

        # Narrative bias: strong narrative associations but weak evidence
        if objects:
            narr_count = sum(len(o.associated_narratives) for o in objects)
            ev_count = sum(len(o.supporting_evidence) for o in objects)
            if narr_count > ev_count and ev_count > 0:
                detected.append(CognitiveBias.NARRATIVE_BIAS.value)

        # Anchoring: all objects share similar awareness levels
        if len(objects) >= 2:
            levels = [o.awareness_level for o in objects]
            if len(set(levels)) == 1:
                detected.append(CognitiveBias.ANCHORING.value)

        # Availability: recent evidence dominates
        if objects:
            recent_count = sum(
                1 for obj in objects
                if (datetime.now(UTC) - obj.creation_timestamp).days < 1
            )
            if recent_count > len(objects) * 0.8 and len(objects) > 1:
                detected.append(CognitiveBias.AVAILABILITY.value)

        self._bias_history.append({'biases': detected, 'count': len(detected)})
        logger.info('cog.meta_cognition.biases_detected', biases=detected)
        return detected

    # ------------------------------------------------------------------
    # Phase 10: Confidence calibration
    # ------------------------------------------------------------------

    def _calibrate_confidence(
        self,
        objects: list[MetaCognitiveObject],
    ) -> dict[str, Any]:
        """Evaluate whether confidence matches evidence."""
        if not objects:
            return {
                'overall_calibration': 0.0,
                'status': 'no_objects',
                'too_high': 0,
                'too_low': 0,
                'well_calibrated': 0,
            }

        too_high = 0
        too_low = 0
        well_calibrated = 0

        for obj in objects:
            evidence_ratio = min(1.0, len(obj.supporting_evidence) * 0.25)
            gap = obj.confidence - evidence_ratio
            if gap > 0.2:
                too_high += 1
            elif gap < -0.2:
                too_low += 1
            else:
                well_calibrated += 1

        total = len(objects)
        overall = well_calibrated / total if total else 0.0

        return {
            'overall_calibration': round(overall, 4),
            'status': 'well_calibrated' if overall > 0.6 else 'needs_adjustment',
            'too_high': too_high,
            'too_low': too_low,
            'well_calibrated': well_calibrated,
        }

    # ------------------------------------------------------------------
    # Phase 11: Strategy selection
    # ------------------------------------------------------------------

    def _select_strategy(
        self,
        objects: list[MetaCognitiveObject],
        calibration: dict[str, Any],
    ) -> str:
        """When quality decreases, select a revision strategy."""
        if not objects:
            return RevisionStrategy.REQUEST_CLARIFICATION.value

        avg_quality = (
            sum(o.reasoning_quality for o in objects) / len(objects)
        )
        status = calibration.get('status', '')

        if status == 'needs_adjustment':
            return RevisionStrategy.GENERATE_COMPETING_HYPOTHESES.value

        if avg_quality < 0.3:
            return RevisionStrategy.RETRIEVE_MORE_MEMORIES.value

        too_high = calibration.get('too_high', 0)
        if too_high > len(objects) * 0.5:
            return RevisionStrategy.REDUCE_INFERENCE_DEPTH.value

        if avg_quality < 0.5:
            return RevisionStrategy.EXPAND_GRAPH_TRAVERSAL.value

        return RevisionStrategy.DELAY_CONCLUSION.value

    # ------------------------------------------------------------------
    # Phase 12: Cognitive resource management
    # ------------------------------------------------------------------

    def _manage_resources(
        self,
        objects: list[MetaCognitiveObject],
    ) -> dict[str, Any]:
        """Allocate working memory, inference depth, graph traversal budget,
        reflection scheduling, and prediction complexity.
        """
        if not objects:
            return dict(self._resource_budgets)

        complexity = min(1.0, len(objects) * 0.15)
        avg_quality = sum(o.reasoning_quality for o in objects) / len(objects)

        # Reduce inference depth when reasoning quality is low
        if avg_quality < 0.3:
            self._resource_budgets[CognitiveResource.INFERENCE_DEPTH.value] = max(
                0.3, self._resource_budgets[CognitiveResource.INFERENCE_DEPTH.value] - 0.2,
            )

        # Increase graph traversal when evidence is sparse
        total_evidence = sum(len(o.supporting_evidence) for o in objects)
        if total_evidence < len(objects):
            self._resource_budgets[CognitiveResource.GRAPH_TRAVERSAL.value] = min(
                1.0, self._resource_budgets[CognitiveResource.GRAPH_TRAVERSAL.value] + 0.1,
            )

        # Scale working memory with complexity
        self._resource_budgets[CognitiveResource.WORKING_MEMORY.value] = min(
            1.0, 0.5 + complexity * 0.5,
        )

        return dict(self._resource_budgets)

    # ------------------------------------------------------------------
    # Phase 13: Error tracking
    # ------------------------------------------------------------------

    def _track_errors(
        self,
        objects: list[MetaCognitiveObject],
        evidence: list[dict[str, Any]],
        reflections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Track possible sources of error: insufficient evidence,
        incomplete context, weak retrieval, prediction uncertainty,
        ambiguous language, hidden assumptions.
        """
        errors: list[str] = []

        if not evidence:
            errors.append('insufficient_evidence')

        if not reflections:
            errors.append('incomplete_context')

        if objects:
            avg_evidence = sum(len(o.supporting_evidence) for o in objects) / len(objects)
            if avg_evidence < 1.0:
                errors.append('weak_retrieval')

            avg_uncertainty = sum(o.remaining_uncertainty for o in objects) / len(objects)
            if avg_uncertainty > 0.5:
                errors.append('prediction_uncertainty')

            total_empty = sum(
                1 for o in objects
                if not o.awareness_description.strip()
            )
            if total_empty > len(objects) * 0.3:
                errors.append('ambiguous_language')

            # Hidden assumptions: high confidence, no supporting evidence
            for obj in objects:
                if obj.confidence > 0.5 and not obj.supporting_evidence:
                    errors.append('hidden_assumptions')
                    break

        errors = list(dict.fromkeys(errors))  # deduplicate preserving order
        self._error_history.append({'errors': errors, 'count': len(errors)})

        return {
            'detected_errors': errors,
            'error_count': len(errors),
            'has_critical': len(errors) >= 3,
        }

    # ------------------------------------------------------------------
    # Phase 14: Epistemic governance
    # ------------------------------------------------------------------

    def _enforce_epistemic_governance(
        self,
        objects: list[MetaCognitiveObject],
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Maintain evidence hierarchy, protect uncertainty,
        prevent premature certainty.
        """
        violations: list[str] = []

        # Evidence hierarchy
        for obj in objects:
            if obj.confidence > 0.8 and len(obj.supporting_evidence) == 0:
                violations.append(
                    f'evidence_hierarchy_violation:{obj.identifier}',
                )

        # Uncertainty protection
        for obj in objects:
            if obj.remaining_uncertainty == 0.0 and obj.confidence < 1.0:
                violations.append(
                    f'uncertainty_hidden:{obj.identifier}',
                )

        # Premature certainty prevention
        for obj in objects:
            if obj.confidence > 0.9 and obj.evidence_quality < 0.3:
                violations.append(
                    f'premature_certainty:{obj.identifier}',
                )

        return {
            'evidence_hierarchy_enforced': self._governance_policies['evidence_hierarchy_enforced'],
            'uncertainty_protection_active': self._governance_policies['uncertainty_protection_active'],
            'premature_certainty_prevention': self._governance_policies['premature_certainty_prevention'],
            'violations': violations,
            'violation_count': len(violations),
        }

    # ------------------------------------------------------------------
    # Phase 15: Architecture supervision
    # ------------------------------------------------------------------

    def _supervise_architecture(
        self,
        narratives: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
        identity: list[dict[str, Any]],
        reflections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Monitor Memory-Inference, Inference-Prediction,
        Prediction-Reality, Reflection-Dialogue, Identity-Narrative
        consistency.
        """
        memory_inference = min(1.0, (len(narratives) + len(beliefs)) * 0.15)
        inference_prediction = min(1.0, len(reflections) * 0.2) if reflections else 0.0
        prediction_reality = min(1.0, len(beliefs) * 0.2) if beliefs else 0.0
        reflection_dialogue = min(1.0, len(reflections) * 0.25) if reflections else 0.0

        # Identity-Narrative separation
        identity_words: set[str] = set()
        for ic in identity:
            identity_words.update(ic.get('identity_statement', '').lower().split())
        narrative_words: set[str] = set()
        for narr in narratives:
            narrative_words.update(narr.get('text', '').lower().split())
        overlap = len(identity_words & narrative_words)
        total = len(identity_words | narrative_words) if identity_words | narrative_words else 1
        identity_narrative = 1.0 - (overlap / total)

        overall = (
            memory_inference * 0.25
            + inference_prediction * 0.2
            + prediction_reality * 0.2
            + reflection_dialogue * 0.15
            + identity_narrative * 0.2
        )

        return {
            'memory_inference_consistency': round(memory_inference, 4),
            'inference_prediction_consistency': round(inference_prediction, 4),
            'prediction_reality_calibration': round(prediction_reality, 4),
            'reflection_dialogue_timing': round(reflection_dialogue, 4),
            'identity_narrative_separation': round(identity_narrative, 4),
            'overall_architecture_health': round(min(1.0, overall), 4),
        }

    # ------------------------------------------------------------------
    # Phase 16: Longitudinal self-evaluation
    # ------------------------------------------------------------------

    def _self_evaluate_longitudinally(self) -> dict[str, Any]:
        """Evaluate prediction accuracy trends, reflection usefulness,
        dialogue continuity over time.
        """
        prediction_trend = (
            sum(self._prediction_accuracy_history[-10:]) / len(self._prediction_accuracy_history[-10:])
            if self._prediction_accuracy_history else 0.0
        )
        reflection_trend = (
            sum(self._reflection_usefulness_history[-10:]) / len(self._reflection_usefulness_history[-10:])
            if self._reflection_usefulness_history else 0.0
        )
        dialogue_trend = (
            sum(self._dialogue_continuity_history[-10:]) / len(self._dialogue_continuity_history[-10:])
            if self._dialogue_continuity_history else 0.0
        )

        bias_trend = (
            self._bias_history[-1]['count'] / 7  # normalise by max bias types
            if self._bias_history else 0.0
        )
        error_trend = (
            self._error_history[-1]['count'] / 6  # normalise by max error types
            if self._error_history else 0.0
        )

        overall = (prediction_trend + reflection_trend + dialogue_trend) / 3

        return {
            'prediction_accuracy_trend': round(prediction_trend, 4),
            'reflection_usefulness_trend': round(reflection_trend, 4),
            'dialogue_continuity_trend': round(dialogue_trend, 4),
            'bias_trend': round(bias_trend, 4),
            'error_trend': round(error_trend, 4),
            'overall_longitudinal_health': round(min(1.0, overall), 4),
        }

    # ------------------------------------------------------------------
    # Phase 17: Adaptive governance
    # ------------------------------------------------------------------

    def _adapt_governance(
        self,
        longitudinal: dict[str, Any],
        governance: dict[str, Any],
    ) -> dict[str, Any]:
        """Governance policies evolve based on longitudinal evidence,
        observed failures, and reasoning quality.
        """
        health = longitudinal.get('overall_longitudinal_health', 0.0)
        violations = governance.get('violation_count', 0)

        adaptations: list[str] = []

        if health < 0.3:
            self._governance_policies['evidence_hierarchy_enforced'] = True
            self._governance_policies['uncertainty_protection_active'] = True
            self._governance_policies['premature_certainty_prevention'] = True
            adaptations.append('stricter_evidence_requirements')

        if violations > 2:
            self._governance_policies['premature_certainty_prevention'] = True
            adaptations.append('enhanced_certainty_prevention')

        if health > 0.7 and violations == 0:
            adaptations.append('relaxed_governance_possible')

        return {
            'policies': dict(self._governance_policies),
            'adaptations': adaptations,
            'adaptation_count': len(adaptations),
            'based_on_health': round(health, 4),
            'based_on_violations': violations,
        }
