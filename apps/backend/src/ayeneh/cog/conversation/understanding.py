"""Conversation Understanding Engine — COG-01.

Transforms raw conversation data into structured semantic representations.
The five-phase pipeline is: Segmentation → Linguistic Analysis → Reference
Resolution → Semantic Interpretation → Validation.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from ayeneh.cog.conversation.reference_resolution import ReferenceResolver
from ayeneh.cog.conversation.segmentation import SegmentationProcessor
from ayeneh.cog.conversation.types import (
    BELIEF_PRECURSORS,
    GOAL_PRECURSORS,
    IDENTITY_PRECURSORS,
    META_COGNITIVE_SIGNALS,
    NARRATIVE_PRECURSORS,
    VALUE_PRECURSORS,
    Claim,
    ConversationSegment,
    Entity,
    SemanticObject,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConversationUnderstandingResult:
    """Output of the COG-01 pipeline."""

    conversation_id: str
    segments: tuple[ConversationSegment, ...]
    semantic_objects: tuple[SemanticObject, ...]
    entities: tuple[Entity, ...]
    events: tuple[SemanticObject, ...]
    claims: tuple[Claim, ...]
    processing_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Linguistic analysis constants
# ---------------------------------------------------------------------------

_EPISTEMIC_MARKERS: dict[str, str] = {
    'i believe': 'belief',
    'i think': 'opinion',
    'i know': 'assertion',
    'i feel': 'emotional_report',
    'i remember': 'memory',
    'i noticed': 'observation',
    'maybe': 'uncertainty',
    'perhaps': 'uncertainty',
    'definitely': 'certainty',
    'always': 'generalization',
    'never': 'generalization',
}

_ACTION_VERBS: frozenset[str] = frozenset({
    'did', 'went', 'said', 'told', 'gave', 'made', 'saw',
    'heard', 'found', 'lost', 'start', 'started', 'finished',
    'asked', 'answered', 'wrote', 'read', 'ran', 'walked', 'took',
    'built', 'created', 'deleted', 'changed', 'broke', 'fixed',
})


# ---------------------------------------------------------------------------
# ConversationUnderstandingEngine
# ---------------------------------------------------------------------------


class ConversationUnderstandingEngine:
    """Transforms raw conversation into structured semantic representations.

    Pipeline phases:
        1. Segmentation — split messages into atomic segments
        2. Linguistic Analysis — extract semantic objects from text
        3. Reference Resolution — resolve pronouns and coreferences
        4. Semantic Interpretation — detect cognitive precursors
        5. Validation — prune low-confidence objects
    """

    def __init__(self) -> None:
        self._segmenter = SegmentationProcessor()
        self._resolver = ReferenceResolver()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        conversation_id: str,
        messages: list[dict],  # noqa: ANN401 – loosely-typed input
        language: str = 'en',
    ) -> ConversationUnderstandingResult:
        """Run the full COG-01 pipeline and return structured results."""
        logger.info(
            'cog.understanding.pipeline_started',
            conversation_id=conversation_id,
            message_count=len(messages),
            language=language,
        )

        # Phase 1 — Segmentation
        segments = self._segment(conversation_id, messages)

        # Phase 2 — Linguistic Analysis
        semantic_objects = self._analyze_linguistics(segments)

        # Phase 3 — Reference Resolution
        resolved = self._resolve_references(semantic_objects, segments)

        # Phase 4 — Semantic Interpretation
        interpreted = self._interpret(resolved, segments)

        # Phase 5 — Validation
        validated = self._validate(interpreted)

        result = ConversationUnderstandingResult(
            conversation_id=conversation_id,
            segments=tuple(segments),
            semantic_objects=tuple(validated),
            entities=tuple(self._extract_entities(validated)),
            events=tuple(self._extract_events(validated)),
            claims=tuple(self._extract_claims(validated)),
        )

        logger.info(
            'cog.understanding.pipeline_completed',
            conversation_id=conversation_id,
            segment_count=len(result.segments),
            object_count=len(result.semantic_objects),
            entity_count=len(result.entities),
            event_count=len(result.events),
            claim_count=len(result.claims),
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Segmentation
    # ------------------------------------------------------------------

    def _segment(
        self,
        conversation_id: str,
        messages: list[dict],
    ) -> list[ConversationSegment]:
        return self._segmenter.process(messages, conversation_id)

    # ------------------------------------------------------------------
    # Phase 2: Linguistic Analysis
    # ------------------------------------------------------------------

    def _analyze_linguistics(
        self,
        segments: list[ConversationSegment],
    ) -> list[SemanticObject]:
        """Extract semantic objects from every segment."""
        objects: list[SemanticObject] = []
        for seg in segments:
            objects.extend(self._extract_from_segment(seg))
        logger.info('cog.linguistics.analyzed', object_count=len(objects))
        return objects

    def _extract_from_segment(
        self,
        segment: ConversationSegment,
    ) -> list[SemanticObject]:
        """Produce semantic objects for a single segment."""
        text = segment.text
        results: list[SemanticObject] = []

        # Sentence-level split (simple regex — avoids heavy NLP deps)
        sentences = re.split(r'[.!?]+', text)
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            results.extend(self._extract_entities_from_text(sent, segment))
            results.extend(self._extract_events_from_text(sent, segment))
            results.extend(self._extract_claims_from_text(sent, segment))

        return results

    def _extract_entities_from_text(
        self,
        text: str,
        segment: ConversationSegment,
    ) -> list[SemanticObject]:
        """Detect named entities in *text*."""
        entities: list[SemanticObject] = []

        # Capitalised word sequences as crude NER (good enough for v1)
        proper_nouns = re.findall(
            r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b', text,
        )
        for noun in proper_nouns:
            offset = text.find(noun)
            entities.append(SemanticObject(
                object_id=f'{segment.segment_id}-ent-{uuid.uuid4().hex[:8]}',
                surface_form=noun,
                normalized_form=noun,
                object_type='entity',
                confidence=0.7,
                offsets=(offset, offset + len(noun)),
            ))

        # Pronouns as potential entity references
        pronouns = re.findall(
            r'\b(i|you|he|she|it|they|we|me|him|her|them|us|my|your|his|its|their|our)\b',
            text, re.IGNORECASE,
        )
        for pronoun in pronouns:
            offset = text.lower().find(pronoun.lower())
            entities.append(SemanticObject(
                object_id=f'{segment.segment_id}-pro-{uuid.uuid4().hex[:8]}',
                surface_form=pronoun,
                normalized_form=pronoun.lower(),
                object_type='entity',
                confidence=0.5,
                offsets=(offset, offset + len(pronoun)),
            ))

        return entities

    def _extract_events_from_text(
        self,
        text: str,
        segment: ConversationSegment,
    ) -> list[SemanticObject]:
        """Detect events and actions in *text*."""
        events: list[SemanticObject] = []
        lower = text.lower()
        for verb in _ACTION_VERBS:
            if verb in lower:
                offset = lower.find(verb)
                events.append(SemanticObject(
                    object_id=f'{segment.segment_id}-evt-{uuid.uuid4().hex[:8]}',
                    surface_form=verb,
                    normalized_form=verb,
                    object_type='event',
                    confidence=0.6,
                    offsets=(offset, offset + len(verb)),
                ))
        return events

    def _extract_claims_from_text(
        self,
        text: str,
        segment: ConversationSegment,
    ) -> list[SemanticObject]:
        """Detect claims in *text*."""
        claims: list[SemanticObject] = []
        lower = text.lower()
        for marker, _epistemic_type in _EPISTEMIC_MARKERS.items():
            if marker in lower:
                claims.append(SemanticObject(
                    object_id=f'{segment.segment_id}-clm-{uuid.uuid4().hex[:8]}',
                    surface_form=text,
                    normalized_form=text,
                    object_type='claim',
                    confidence=0.65,
                    offsets=(0, len(text)),
                ))
                break  # one claim per sentence is sufficient
        return claims

    # ------------------------------------------------------------------
    # Phase 3: Reference Resolution
    # ------------------------------------------------------------------

    def _resolve_references(
        self,
        semantic_objects: list[SemanticObject],
        segments: list[ConversationSegment],
    ) -> list[SemanticObject]:
        return self._resolver.resolve(semantic_objects, segments)

    # ------------------------------------------------------------------
    # Phase 4: Semantic Interpretation
    # ------------------------------------------------------------------

    def _interpret(
        self,
        objects: list[SemanticObject],
        segments: list[ConversationSegment],
    ) -> list[SemanticObject]:
        """Annotate objects with cognitive precursor tags."""
        interpreted: list[SemanticObject] = []
        for obj in objects:
            # Look up the segment text for precursor detection
            seg_text = self._text_for_object(obj, segments)
            tags = self._detect_precursors(seg_text)

            if tags:
                # Tag-aware confidence boost
                boosted_confidence = min(1.0, obj.confidence + 0.1 * len(tags))
                interpreted.append(SemanticObject(
                    object_id=obj.object_id,
                    surface_form=obj.surface_form,
                    normalized_form=obj.normalized_form,
                    object_type=obj.object_type,
                    confidence=boosted_confidence,
                    offsets=obj.offsets,
                ))
            else:
                interpreted.append(obj)

        logger.info('cog.interpretation.complete', object_count=len(interpreted))
        return interpreted

    def _detect_precursors(self, text: str) -> list[str]:
        """Return a list of precursor tags detected in *text*."""
        lower = text.lower()
        tags: list[str] = []
        for precursor in NARRATIVE_PRECURSORS:
            if precursor in lower:
                tags.append('narrative_precursor')
                break
        for precursor in IDENTITY_PRECURSORS:
            if precursor in lower:
                tags.append('identity_precursor')
                break
        for precursor in BELIEF_PRECURSORS:
            if precursor in lower:
                tags.append('belief_precursor')
                break
        for precursor in VALUE_PRECURSORS:
            if precursor in lower:
                tags.append('value_precursor')
                break
        for precursor in GOAL_PRECURSORS:
            if precursor in lower:
                tags.append('goal_precursor')
                break
        for signal in META_COGNITIVE_SIGNALS:
            if signal in lower:
                tags.append('metacognitive_signal')
                break
        return tags

    @staticmethod
    def _text_for_object(
        obj: SemanticObject,
        segments: list[ConversationSegment],
    ) -> str:
        """Return the segment text that contains *obj*."""
        # Heuristic: find the segment whose text contains the surface form
        for seg in segments:
            if obj.surface_form.lower() in seg.text.lower():
                return seg.text
        return ''

    # ------------------------------------------------------------------
    # Phase 5: Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(objects: list[SemanticObject]) -> list[SemanticObject]:
        """Remove semantic objects below the minimum confidence threshold."""
        MIN_CONFIDENCE = 0.25
        validated = [o for o in objects if o.confidence >= MIN_CONFIDENCE]
        dropped = len(objects) - len(validated)
        if dropped:
            logger.info('cog.validation.dropped', count=dropped)
        return validated

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_entities(objects: list[SemanticObject]) -> list[Entity]:
        """Collect unique entities from semantic objects."""
        seen: dict[str, Entity] = {}
        for obj in objects:
            if obj.object_type != 'entity':
                continue
            key = obj.normalized_form.lower()
            if key not in seen:
                seen[key] = Entity(
                    entity_id=obj.object_id,
                    name=obj.normalized_form,
                    entity_type='concept',
                    confidence=obj.confidence,
                )
        return list(seen.values())

    @staticmethod
    def _extract_events(objects: list[SemanticObject]) -> list[SemanticObject]:
        """Return all event-type semantic objects."""
        return [o for o in objects if o.object_type == 'event']

    @staticmethod
    def _extract_claims(objects: list[SemanticObject]) -> list[Claim]:
        """Convert claim-type semantic objects into Claim instances."""
        claims: list[Claim] = []
        for obj in objects:
            if obj.object_type != 'claim':
                continue
            epistemic = 'observation'
            lower = obj.normalized_form.lower()
            for marker, e_type in _EPISTEMIC_MARKERS.items():
                if marker in lower:
                    epistemic = e_type
                    break
            claims.append(Claim(
                claim_id=obj.object_id,
                text=obj.normalized_form,
                speaker='',
                timestamp=datetime.now(UTC),
                epistemic_marker=epistemic,
                confidence=obj.confidence,
            ))
        return claims
