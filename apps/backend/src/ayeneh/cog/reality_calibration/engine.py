"""Reality Calibration Engine — COG-15.

Continuously distinguishes reality from interpretation, narrative, belief,
and identity. The pipeline calibrates observed events against available
evidence and tracks how far mental stories drift from verifiable reality.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.cog.reality_calibration.fusion import (
    CognitiveFusionDetector,
    FusionResult,
    NarrativeFusionDetector,
)
from ayeneh.cog.reality_calibration.types import (
    CALIBRATION_STATES,
    EVIDENCE_HIERARCHY,
    CalibrationObject,
    EpistemicIntegrity,
    MentalStoryObject,
    PredictionErrorObject,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalibrationResult:
    """Output of the COG-15 Reality Calibration pipeline."""

    calibrations: tuple[CalibrationObject, ...]
    mental_stories: tuple[MentalStoryObject, ...]
    distances: dict[str, float]
    fusion_levels: list[FusionResult]
    narrative_gravities: dict[str, float]
    awakening_index: float
    processing_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# RealityCalibrationEngine
# ---------------------------------------------------------------------------


class RealityCalibrationEngine:
    """Continuously distinguishes reality from interpretation, narrative, belief (COG-15).

    Pipeline phases:
        1. Event → Observation → Calibration
        2. Extract mental stories from narratives and beliefs
        3. Compute story–reality distance
        4. Detect cognitive fusion
        5. Compute narrative gravity
        6. Compute awakening index
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._calibrations: dict[str, CalibrationObject] = {}
        self._mental_stories: dict[str, MentalStoryObject] = {}
        self._fusion_detector = CognitiveFusionDetector()
        self._narrative_fusion_detector = NarrativeFusionDetector()
        self._ai_router = ai_router

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        evidence: list[dict[str, Any]],
        narratives: list[dict[str, Any]] | None = None,
        beliefs: list[dict[str, Any]] | None = None,
        identity: list[dict[str, Any]] | None = None,
        predictions: list[dict[str, Any]] | None = None,
    ) -> CalibrationResult:
        """Run the full COG-15 pipeline.

        Stages:
            Evidence → Observation → Interpretation → Narrative →
            Belief → Identity → Calibration
        """
        logger.info(
            'cog.reality_calibration.pipeline_started',
            evidence_count=len(evidence),
            narrative_count=len(narratives) if narratives else 0,
        )

        narratives = narratives or []
        beliefs = beliefs or []
        identity = identity or []
        predictions = predictions or []

        calibrations = self._calibrate(evidence, narratives, beliefs, identity)
        stories = self._extract_mental_stories(narratives, beliefs, identity)
        distances = self._compute_story_reality_distance(stories, evidence)
        fusion = self._detect_fusion(identity, narratives, beliefs)
        gravity = self._compute_narrative_gravity(narratives, evidence)
        awakening = self._compute_awakening_index(evidence, beliefs, identity)

        result = CalibrationResult(
            calibrations=tuple(calibrations),
            mental_stories=tuple(stories),
            distances=distances,
            fusion_levels=fusion,
            narrative_gravities=gravity,
            awakening_index=awakening,
        )

        logger.info(
            'cog.reality_calibration.pipeline_completed',
            calibration_count=len(calibrations),
            story_count=len(stories),
            awakening_index=awakening,
        )
        return result

    # ------------------------------------------------------------------
    # LLM integration
    # ------------------------------------------------------------------

    def _try_llm_calibration(
        self,
        evidence: list[dict[str, Any]],
        narratives: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]] | None:
        """Attempt LLM-based calibration assessment. Returns None on failure."""
        if not self._ai_router:
            return None
        try:
            import asyncio
            from ayeneh.ai_router.types import AITask, AITaskType

            evidence_texts = [
                f"- [{ev.get('identifier', '')}] ({ev.get('type', 'unknown')}) {ev.get('text', '')}"
                for ev in evidence[:10]
                if ev.get('text')
            ]
            narr_texts = [
                f"- [{n.get('identifier', '')}] {n.get('text', n.get('summary', ''))}"
                for n in narratives[:5]
                if n.get('text') or n.get('summary')
            ]
            belief_texts = [
                f"- [{b.get('identifier', '')}] {b.get('belief_statement', '')}"
                for b in beliefs[:5]
                if b.get('belief_statement')
            ]

            prompt = (
                "Calibrate the following evidence against available narratives and beliefs. "
                "For each evidence item, provide:\n"
                "- confidence: 0.0-1.0\n"
                "- evidence_quality: 0.0-1.0\n"
                "- calibration_status: one of well_anchored, moderately_anchored, "
                "weakly_anchored, highly_speculative, contradicted\n"
                "- identity_involvement: 0.0-1.0\n\n"
                "Evidence:\n"
                + ("\n".join(evidence_texts) if evidence_texts else "(none)")
                + "\n\nNarratives:\n"
                + ("\n".join(narr_texts) if narr_texts else "(none)")
                + "\n\nBeliefs:\n"
                + ("\n".join(belief_texts) if belief_texts else "(none)")
                + "\n\nRespond as a JSON object mapping evidence IDs to assessment objects."
            )
            messages = [
                {"role": "system", "content": "You are a cognitive reality calibration assistant."},
                {"role": "user", "content": prompt},
            ]
            task = AITask(
                task_type=AITaskType.CONVERSATION_GENERATION,
                content=prompt,
                max_tokens=1024,
                temperature=0.3,
            )

            loop = asyncio.get_event_loop()
            if loop.is_running():
                return None
            result = loop.run_until_complete(self._ai_router.chat(task, messages))
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                return None

            import json
            start = content.find('{')
            end = content.rfind('}') + 1
            if start == -1 or end <= 0:
                return None
            assessments = json.loads(content[start:end])
            if not isinstance(assessments, dict):
                return None
            return assessments
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Phase 1: Calibrate evidence
    # ------------------------------------------------------------------

    def _calibrate(
        self,
        evidence: list[dict[str, Any]],
        narratives: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
        identity: list[dict[str, Any]],
    ) -> list[CalibrationObject]:
        """Calibrate each evidence item against available context.

        If an AI router is available, attempts LLM-based calibration first,
        falling back to rule-based on failure.
        """
        llm_assessments = self._try_llm_calibration(evidence, narratives, beliefs)

        calibrations: list[CalibrationObject] = []

        for ev in evidence:
            eid = ev.get('identifier', str(uuid.uuid4()))
            event_text = ev.get('text', ev.get('original_text', ev.get('normalized_text', '')))
            if not event_text:
                continue

            evidence_level = self._determine_evidence_level(ev)
            available = self._find_related_evidence(ev, evidence)
            interp = self._find_related_items(ev, narratives, key='text')
            narr_refs = self._find_related_items(ev, narratives, key='title')
            belief_refs = self._find_related_items(ev, beliefs, key='belief_statement')

            identity_score = self._compute_identity_involvement(ev, identity)

            if llm_assessments and eid in llm_assessments:
                a = llm_assessments[eid]
                confidence = min(1.0, max(0.0, float(a.get('confidence', 0.0))))
                evidence_quality = min(1.0, max(0.0, float(a.get('evidence_quality', 0.0))))
                status = a.get('calibration_status', 'weakly_anchored')
                if status not in CALIBRATION_STATES:
                    status = 'weakly_anchored'
                identity_score = min(1.0, max(0.0, float(a.get('identity_involvement', identity_score))))
            else:
                confidence = self._compute_calibration_confidence(
                    evidence_level, len(available), identity_score,
                )
                evidence_quality = self._compute_evidence_quality(evidence_level, len(available))
                status = self._determine_calibration_status(confidence, evidence_level)

            obj = CalibrationObject(
                identifier=eid,
                observed_event=event_text,
                available_evidence=tuple(available),
                interpretations=tuple(interp),
                narratives=tuple(narr_refs),
                associated_beliefs=tuple(belief_refs),
                identity_involvement=identity_score,
                confidence=confidence,
                evidence_quality=evidence_quality,
                calibration_status=status,
                evidence_level=evidence_level,
            )
            calibrations.append(obj)
            self._calibrations[eid] = obj

        return calibrations

    # ------------------------------------------------------------------
    # Phase 2: Extract mental stories
    # ------------------------------------------------------------------

    def _extract_mental_stories(
        self,
        narratives: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
        identity: list[dict[str, Any]],
    ) -> list[MentalStoryObject]:
        """Extract coherent mental stories from narratives, beliefs, and identity."""
        stories: list[MentalStoryObject] = []

        for narr in narratives:
            sid = narr.get('identifier', str(uuid.uuid4()))
            description = narr.get('summary', narr.get('text', narr.get('title', '')))
            if not description:
                continue

            actors = self._extract_actors(narr)
            roles = tuple(narr.get('roles', ()))
            rules = tuple(narr.get('core_assumptions', narr.get('implicit_rules', ())))
            expected = tuple(narr.get('expected_outcomes', ()))
            threats = tuple(narr.get('threats', ()))
            resolutions = tuple(narr.get('desired_resolutions', ()))

            underlying = tuple(b.get('identifier', '') for b in beliefs
                               if self._narrative_belief_overlap(narr, b))
            identity_refs = tuple(ic.get('identifier', '') for ic in identity
                                  if self._narrative_identity_overlap(narr, ic))

            identity_involvement = self._compute_narrative_identity_involvement(narr, identity)
            story_reality_distance = self._compute_story_reality_distance_single(narr)

            story = MentalStoryObject(
                story_id=sid,
                description=description,
                actors=actors,
                roles=roles,
                rules=rules,
                expected_outcomes=expected,
                threats=threats,
                desired_resolutions=resolutions,
                supporting_narratives=(narr.get('identifier', ''),),
                underlying_beliefs=underlying,
                associated_emotions=tuple(narr.get('emotional_associations', ())),
                identity_involvement=identity_involvement,
                story_reality_distance=story_reality_distance,
                narrative_gravity=narr.get('influence_score', 0.0),
                cognitive_fusion_level=0.0,
            )
            stories.append(story)
            self._mental_stories[sid] = story

        return stories

    # ------------------------------------------------------------------
    # Phase 3: Story–reality distance
    # ------------------------------------------------------------------

    def _compute_story_reality_distance(
        self,
        stories: list[MentalStoryObject],
        evidence: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Compute distance from reality for each mental story."""
        distances: dict[str, float] = {}
        evidence_texts = {
            e.get('text', e.get('original_text', '')).lower()
            for e in evidence
            if e.get('text') or e.get('original_text')
        }

        for story in stories:
            base_distance = story.story_reality_distance
            evidence_gap = self._compute_evidence_gap(story, evidence_texts)
            distances[story.story_id] = min(1.0, base_distance + evidence_gap)

        return distances

    # ------------------------------------------------------------------
    # Phase 4: Fusion detection
    # ------------------------------------------------------------------

    def _detect_fusion(
        self,
        identity: list[dict[str, Any]],
        narratives: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
    ) -> list[FusionResult]:
        """Detect cognitive fusion across identity, narratives, and beliefs."""
        return self._fusion_detector.detect(identity, narratives, beliefs)

    # ------------------------------------------------------------------
    # Phase 5: Narrative gravity
    # ------------------------------------------------------------------

    def _compute_narrative_gravity(
        self,
        narratives: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Compute narrative gravity — how strongly narratives pull cognition."""
        gravities: dict[str, float] = {}
        evidence_ids = {e.get('identifier', '') for e in evidence}

        for narr in narratives:
            nid = narr.get('identifier', '')
            influence = narr.get('influence_score', 0.0)
            confidence = narr.get('confidence', 0.0)
            supporting = narr.get('supporting_evidence', ())
            grounded = sum(1 for e in supporting if e in evidence_ids)
            grounding_factor = min(1.0, grounded * 0.2)
            gravities[nid] = min(1.0, influence * 0.5 + confidence * 0.3 + grounding_factor * 0.2)

        return gravities

    # ------------------------------------------------------------------
    # Phase 6: Awakening index
    # ------------------------------------------------------------------

    def _compute_awakening_index(
        self,
        evidence: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
        identity: list[dict[str, Any]],
    ) -> float:
        """Compute awakening index — capacity to observe own cognition.

        Higher values indicate greater ability to distinguish internal
        processes from external reality.
        """
        if not evidence and not beliefs and not identity:
            return 0.0

        evidence_diversity = min(1.0, len(evidence) * 0.1)
        belief_count = min(1.0, len(beliefs) * 0.15)
        identity_components = min(1.0, len(identity) * 0.12)

        meta_evidence_count = sum(
            1 for e in evidence
            if e.get('type', '') in ('meta_cognitive_report', 'observation')
        )
        meta_factor = min(1.0, meta_evidence_count * 0.2)

        score = (
            evidence_diversity * 0.3
            + belief_count * 0.2
            + identity_components * 0.2
            + meta_factor * 0.3
        )
        return round(min(1.0, score), 4)

    # ------------------------------------------------------------------
    # Phase 7: Model Revision
    # ------------------------------------------------------------------

    @staticmethod
    def _revise_model(
        calibration: CalibrationObject,
        prediction_errors: list[PredictionErrorObject],
    ) -> dict[str, Any]:
        """Evaluate whether to strengthen, weaken, revise, split, merge, or archive a model.

        Every revision preserves historical lineage.
        """
        action = 'strengthen'
        reason = 'evidence supports current model'

        if calibration.calibration_status == 'contradicted':
            action = 'revise'
            reason = 'calibration contradicted by evidence'
        elif calibration.calibration_status == 'weakly_anchored':
            action = 'weaken'
            reason = 'weak evidence grounding'
        elif calibration.evidence_level <= 2 and calibration.confidence >= 0.7:
            action = 'strengthen'
            reason = 'strong evidence and high confidence'
        elif calibration.evidence_level >= 6:
            action = 'archive'
            reason = 'highly speculative or narrative-level evidence'

        if len(prediction_errors) >= 3:
            action = 'split'
            reason = (
                f"{len(prediction_errors)} prediction errors suggest "
                f"multiple underlying models"
            )

        return {
            'calibration_id': calibration.identifier,
            'action': action,
            'reason': reason,
            'current_status': calibration.calibration_status,
            'evidence_level': calibration.evidence_level,
            'prediction_errors_count': len(prediction_errors),
        }

    # ------------------------------------------------------------------
    # Phase 8: Epistemic Integrity Enforcement
    # ------------------------------------------------------------------

    @staticmethod
    def _enforce_epistemic_integrity(
        calibration: CalibrationObject,
    ) -> dict[str, Any]:
        """Never present a higher epistemic layer as a lower one.

        For example, a narrative must never be presented as an observed fact.
        """
        violations: list[str] = []

        if calibration.evidence_level >= 6 and calibration.confidence >= 0.8:
            violations.append(
                f"High confidence ({calibration.confidence:.2f}) on "
                f"weak evidence level ({calibration.evidence_level})"
            )

        if calibration.identity_involvement > 0.7 and calibration.evidence_level > 3:
            violations.append(
                f"Strong identity involvement ({calibration.identity_involvement:.2f}) "
                f"with insufficient evidence level ({calibration.evidence_level})"
            )

        if calibration.prediction_involvement > 0.5 and calibration.evidence_level > 4:
            violations.append(
                f"Prediction-driven calibration ({calibration.prediction_involvement:.2f}) "
                f"lacks direct evidence"
            )

        layer = EpistemicIntegrity.DIRECT_OBSERVATION
        if calibration.evidence_level >= 7:
            layer = EpistemicIntegrity.SPECULATIVE_POSSIBILITY
        elif calibration.evidence_level >= 5:
            layer = EpistemicIntegrity.PROBABLE_INFERENCE
        elif calibration.evidence_level >= 3:
            layer = EpistemicIntegrity.RELIABLE_EVIDENCE

        return {
            'calibration_id': calibration.identifier,
            'determined_layer': layer.value,
            'violations': violations,
            'is_epistemically_honest': len(violations) == 0,
        }

    # ------------------------------------------------------------------
    # Phase 9: Continuous Calibration
    # ------------------------------------------------------------------

    def _continuous_calibration(
        self,
        calibration_requests: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Subscription model for continuous calibration requests.

        Processes calibration requests from memory, inference, prediction,
        reflection, dialogue, and meta-cognition subsystems.
        """
        results: list[dict[str, Any]] = []

        for request in calibration_requests:
            source = request.get('source', 'unknown')
            subject = request.get('subject', '')
            evidence = request.get('evidence', ())

            if not subject:
                continue

            matched_calibrations = [
                cal for cal in self._calibrations.values()
                if subject.lower() in cal.observed_event.lower()
            ]

            status = 'pending'
            if matched_calibrations:
                best = max(matched_calibrations, key=lambda c: c.confidence)
                status = best.calibration_status

            results.append({
                'source': source,
                'subject': subject,
                'evidence_count': len(evidence) if isinstance(evidence, (list, tuple)) else 0,
                'calibration_status': status,
                'matched_calibrations': len(matched_calibrations),
            })

        logger.info(
            'cog.reality_calibration.continuous_calibration',
            request_count=len(calibration_requests),
            results_count=len(results),
        )
        return results

    # ------------------------------------------------------------------
    # Phase 10: Calibration Explainability
    # ------------------------------------------------------------------

    @staticmethod
    def _explain_calibration(
        calibration: CalibrationObject,
        prediction_errors: list[PredictionErrorObject] | None = None,
    ) -> dict[str, Any]:
        """Generate mandatory explainability for a calibration result.

        Answers: which observations initiated calibration, which predictions
        failed, which evidence supported revision, competing interpretations,
        confidence changes, and remaining uncertainty.
        """
        prediction_errors = prediction_errors or []

        failed_predictions = [
            pe.predicted_outcome for pe in prediction_errors
            if pe.observed_outcome != pe.predicted_outcome
        ]

        competing = list(calibration.interpretations) if calibration.interpretations else []

        return {
            'calibration_id': calibration.identifier,
            'initiating_observation': calibration.observed_event,
            'failed_predictions': failed_predictions,
            'supporting_evidence': list(calibration.available_evidence),
            'competing_interpretations': competing,
            'confidence': calibration.confidence,
            'evidence_quality': calibration.evidence_quality,
            'remaining_uncertainty': calibration.remaining_uncertainty,
            'calibration_status': calibration.calibration_status,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_evidence_level(ev: dict[str, Any]) -> int:
        """Map evidence type to evidence hierarchy level (1=strongest)."""
        ev_type = ev.get('type', ev.get('category', '')).lower()
        mapping = {
            'observation': 1,
            'behavioral_report': 2,
            'independent_corroboration': 3,
            'self_report': 4,
            'interpretation': 5,
            'narrative': 6,
            'prediction': 7,
            'speculation': 8,
        }
        return mapping.get(ev_type, 8)

    @staticmethod
    def _find_related_evidence(
        target: dict[str, Any],
        all_evidence: list[dict[str, Any]],
    ) -> list[str]:
        """Find evidence items with overlapping keywords."""
        target_text = target.get('text', '').lower()
        target_words = set(target_text.split())
        related: list[str] = []
        for ev in all_evidence:
            if ev.get('identifier') == target.get('identifier'):
                continue
            ev_text = ev.get('text', ev.get('original_text', '')).lower()
            ev_words = set(ev_text.split())
            if target_words & ev_words:
                related.append(ev.get('identifier', ''))
        return related

    @staticmethod
    def _find_related_items(
        target: dict[str, Any],
        items: list[dict[str, Any]],
        key: str = 'text',
    ) -> list[str]:
        """Find items with overlapping text content."""
        target_text = target.get('text', '').lower()
        target_words = set(target_text.split())
        related: list[str] = []
        for item in items:
            item_text = item.get(key, '').lower()
            item_words = set(item_text.split())
            if target_words & item_words:
                related.append(item.get('identifier', ''))
        return related

    @staticmethod
    def _compute_identity_involvement(
        ev: dict[str, Any],
        identity: list[dict[str, Any]],
    ) -> float:
        """Compute how much an evidence item involves identity components."""
        if not identity:
            return 0.0
        ev_text = ev.get('text', '').lower()
        ev_words = set(ev_text.split())
        matches = 0
        for ic in identity:
            ic_text = ic.get('identity_statement', '').lower()
            ic_words = set(ic_text.split())
            if ev_words & ic_words:
                matches += 1
        return min(1.0, matches * 0.25)

    @staticmethod
    def _compute_calibration_confidence(
        evidence_level: int,
        related_count: int,
        identity_involvement: float,
    ) -> float:
        """Compute calibration confidence from evidence quality and corroboration."""
        level_score = max(0.0, 1.0 - (evidence_level - 1) * 0.125)
        corroboration = min(1.0, related_count * 0.2)
        identity_factor = 1.0 - identity_involvement * 0.3
        return round(min(1.0, level_score * 0.5 + corroboration * 0.3 + identity_factor * 0.2), 4)

    @staticmethod
    def _compute_evidence_quality(evidence_level: int, related_count: int) -> float:
        """Compute evidence quality score."""
        level_score = max(0.0, 1.0 - (evidence_level - 1) * 0.125)
        corroboration = min(1.0, related_count * 0.2)
        return round(min(1.0, level_score * 0.6 + corroboration * 0.4), 4)

    @staticmethod
    def _determine_calibration_status(confidence: float, evidence_level: int) -> str:
        """Determine calibration status from confidence and evidence level."""
        if evidence_level <= 2 and confidence >= 0.7:
            return 'well_anchored'
        if evidence_level <= 3 and confidence >= 0.5:
            return 'moderately_anchored'
        if evidence_level <= 4 and confidence >= 0.3:
            return 'weakly_anchored'
        if evidence_level >= 7:
            return 'highly_speculative'
        return 'weakly_anchored'

    @staticmethod
    def _extract_actors(narr: dict[str, Any]) -> tuple[str, ...]:
        """Extract actors from a narrative."""
        actors: list[str] = []
        actors.extend(narr.get('actors', ()))
        text = narr.get('text', narr.get('summary', '')).lower()
        for keyword in ('i ', 'my ', 'me ', 'we ', 'our '):
            if keyword in text and 'self' not in actors:
                actors.append('self')
        return tuple(actors)

    @staticmethod
    def _narrative_belief_overlap(narr: dict[str, Any], belief: dict[str, Any]) -> bool:
        """Check if a narrative and belief share textual content."""
        narr_text = set(narr.get('text', narr.get('summary', '')).lower().split())
        belief_text = set(belief.get('belief_statement', '').lower().split())
        return bool(narr_text & belief_text)

    @staticmethod
    def _narrative_identity_overlap(narr: dict[str, Any], ic: dict[str, Any]) -> bool:
        """Check if a narrative and identity component share textual content."""
        narr_text = set(narr.get('text', narr.get('summary', '')).lower().split())
        ic_text = set(ic.get('identity_statement', '').lower().split())
        return bool(narr_text & ic_text)

    @staticmethod
    def _compute_narrative_identity_involvement(
        narr: dict[str, Any],
        identity: list[dict[str, Any]],
    ) -> float:
        """Compute identity involvement for a narrative."""
        if not identity:
            return 0.0
        narr_text = set(narr.get('text', narr.get('summary', '')).lower().split())
        matches = 0
        for ic in identity:
            ic_text = set(ic.get('identity_statement', '').lower().split())
            if narr_text & ic_text:
                matches += 1
        return min(1.0, matches * 0.25)

    @staticmethod
    def _compute_story_reality_distance_single(narr: dict[str, Any]) -> float:
        """Estimate how far a single narrative is from observable reality."""
        influence = narr.get('influence_score', 0.0)
        confidence = narr.get('confidence', 0.0)
        core_assumptions = len(narr.get('core_assumptions', ()))
        assumption_factor = min(1.0, core_assumptions * 0.2)
        return round(min(1.0, influence * 0.3 + confidence * 0.3 + assumption_factor * 0.4), 4)

    @staticmethod
    def _compute_evidence_gap(
        story: MentalStoryObject,
        evidence_texts: set[str],
    ) -> float:
        """Compute evidence gap between a story and available evidence."""
        if not evidence_texts:
            return 0.5
        story_words = set(story.description.lower().split())
        overlap_count = sum(1 for t in evidence_texts if story_words & set(t.split()))
        if overlap_count == 0:
            return 0.3
        return max(0.0, 0.3 - overlap_count * 0.1)
