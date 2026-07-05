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
    CognitiveTransparency,
    MetaCognitiveObject,
    ObserverEpisode,
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

        result = MetaCognitionResult(
            objects=tuple(validated),
            awareness_levels=levels,
            transparency=transparency,
            de_identification=de_id,
            total_extracted=len(validated),
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
