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
    MentalStoryObject,
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

    def __init__(self) -> None:
        self._calibrations: dict[str, CalibrationObject] = {}
        self._mental_stories: dict[str, MentalStoryObject] = {}
        self._fusion_detector = CognitiveFusionDetector()
        self._narrative_fusion_detector = NarrativeFusionDetector()

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
    # Phase 1: Calibrate evidence
    # ------------------------------------------------------------------

    def _calibrate(
        self,
        evidence: list[dict[str, Any]],
        narratives: list[dict[str, Any]],
        beliefs: list[dict[str, Any]],
        identity: list[dict[str, Any]],
    ) -> list[CalibrationObject]:
        """Calibrate each evidence item against available context."""
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
