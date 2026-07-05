"""Evidence Extraction Engine — COG-02.

Transforms validated semantic objects from COG-01 into fully validated,
provenanced EvidenceObjects ready for downstream cognitive processing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from ayeneh.cog.evidence.types import (
    EPISTEMIC_CLASSIFICATIONS,
    EVIDENCE_CATEGORIES,
    EvidenceContext,
    EvidenceObject,
    EvidenceProvenance,
    EvidenceStrength,
)
from ayeneh.cog.evidence.validation import EvidenceValidator

if TYPE_CHECKING:
    from ayeneh.cog.conversation.understanding import (
        ConversationUnderstandingResult,
    )

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceExtractionResult:
    """Output of the COG-02 pipeline."""

    evidence_objects: tuple[EvidenceObject, ...]
    total_extracted: int
    validation_summary: dict[str, int]
    processing_timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Epistemic classification heuristics
# ---------------------------------------------------------------------------

_CATEGORY_TO_EPISTEMIC: dict[str, str] = {
    'observed_event': 'direct_observation',
    'self_report': 'subjective_experience',
    'behavioral_report': 'reported_observation',
    'emotional_report': 'subjective_experience',
    'memory_report': 'remembered_event',
    'interpretation_report': 'interpretation',
    'prediction': 'prediction',
    'question': 'question',
    'hypothesis': 'hypothesis',
    'assumption': 'assumption',
    'intention': 'commitment',
    'commitment': 'commitment',
    'preference': 'preference',
    'decision_report': 'interpretation',
    'relationship_report': 'reported_observation',
    'meta_cognitive_report': 'interpretation',
    'narrative_report': 'narrative_report',
    'identity_statement': 'identity_statement',
    'value_statement': 'belief_report',
    'goal_statement': 'commitment',
}


# ---------------------------------------------------------------------------
# EvidenceExtractionEngine
# ---------------------------------------------------------------------------


class EvidenceExtractionEngine:
    """Transforms validated semantic objects into validated evidence.

    Pipeline phases:
        1. Candidate Extraction — convert semantic objects to EvidenceObject
        2. Epistemic Classification — assign epistemic category
        3. Validation — enforce mandatory attributes and consistency
        4. Confidence Assignment — compute multi-dimensional confidence
        5. Provenance Construction — build full provenance chain
        6. Publication — freeze and return validated evidence
    """

    def __init__(self) -> None:
        self._validator = EvidenceValidator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        understanding_result: ConversationUnderstandingResult,
    ) -> EvidenceExtractionResult:
        """Run the full COG-02 pipeline."""
        logger.info(
            'cog.evidence.pipeline_started',
            conversation_id=understanding_result.conversation_id,
            semantic_object_count=len(understanding_result.semantic_objects),
        )

        # Phase 1 — Candidate Extraction
        candidates = self._extract_candidates(understanding_result)

        # Phase 2 — Epistemic Classification
        classified = self._classify_epistemic(candidates)

        # Phase 3 — Validation
        validated = self._validate(classified)

        # Phase 4 — Confidence Assignment
        confident = self._assign_confidence(validated)

        # Phase 5 — Provenance Construction
        provenanced = self._construct_provenance(confident, understanding_result)

        # Phase 6 — Publication
        result = EvidenceExtractionResult(
            evidence_objects=tuple(provenanced),
            total_extracted=len(provenanced),
            validation_summary=self._summarize_validation(provenanced),
        )

        logger.info(
            'cog.evidence.pipeline_completed',
            conversation_id=understanding_result.conversation_id,
            evidence_count=result.total_extracted,
            validation_summary=result.validation_summary,
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Candidate Extraction
    # ------------------------------------------------------------------

    def _extract_candidates(
        self,
        understanding_result: ConversationUnderstandingResult,
    ) -> list[EvidenceObject]:
        """Convert semantic objects into raw EvidenceObject candidates."""
        candidates: list[EvidenceObject] = []

        # Build a segment lookup for provenance data
        seg_map = {
            seg.segment_id: seg for seg in understanding_result.segments
        }

        for obj in understanding_result.semantic_objects:
            category = self._infer_category(obj)
            seg = self._find_segment(obj, seg_map)

            candidate = EvidenceObject(
                identifier=str(uuid.uuid4()),
                category=category,
                epistemic_classification='',  # filled in Phase 2
                original_text=obj.surface_form,
                normalized_text=obj.normalized_form,
                speaker=seg.speaker if seg else '',
                confidence=obj.confidence,
                evidence_strength=EvidenceStrength(),
                provenance=EvidenceProvenance(
                    conversation_id=understanding_result.conversation_id,
                    segment_id=seg.segment_id if seg else '',
                    speaker=seg.speaker if seg else '',
                    timestamp=seg.timestamp if seg else datetime.now(UTC),
                    original_span=obj.offsets,
                    normalized_representation=obj.normalized_form,
                ),
                temporal_scope='momentary',
                context=EvidenceContext(),
                validation_status='pending',
            )
            candidates.append(candidate)

        logger.info('cog.evidence.candidates_extracted', count=len(candidates))
        return candidates

    # ------------------------------------------------------------------
    # Phase 2: Epistemic Classification
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_epistemic(
        candidates: list[EvidenceObject],
    ) -> list[EvidenceObject]:
        """Assign epistemic classification to each candidate."""
        classified: list[EvidenceObject] = []
        for c in candidates:
            epistemic = _CATEGORY_TO_EPISTEMIC.get(c.category, 'interpretation')
            classified.append(EvidenceObject(
                identifier=c.identifier,
                category=c.category,
                epistemic_classification=epistemic,
                original_text=c.original_text,
                normalized_text=c.normalized_text,
                speaker=c.speaker,
                confidence=c.confidence,
                evidence_strength=c.evidence_strength,
                provenance=c.provenance,
                temporal_scope=c.temporal_scope,
                context=c.context,
                validation_status=c.validation_status,
            ))
        logger.info('cog.evidence.epistemic_classified', count=len(classified))
        return classified

    # ------------------------------------------------------------------
    # Phase 3: Validation
    # ------------------------------------------------------------------

    def _validate(
        self,
        classified: list[EvidenceObject],
    ) -> list[EvidenceObject]:
        """Validate each candidate via EvidenceValidator."""
        validated: list[EvidenceObject] = []
        for c in classified:
            status, warnings = self._validator.validate(c)
            if status == 'fail':
                logger.warning(
                    'cog.evidence.validation_failed',
                    evidence_id=c.identifier,
                    warnings=warnings,
                )
                continue
            if status == 'requires_review':
                logger.info(
                    'cog.evidence.requires_review',
                    evidence_id=c.identifier,
                    warnings=warnings,
                )
            validated.append(EvidenceObject(
                identifier=c.identifier,
                category=c.category,
                epistemic_classification=c.epistemic_classification,
                original_text=c.original_text,
                normalized_text=c.normalized_text,
                speaker=c.speaker,
                confidence=c.confidence,
                evidence_strength=c.evidence_strength,
                provenance=c.provenance,
                temporal_scope=c.temporal_scope,
                context=c.context,
                validation_status=status,
            ))
        return validated

    # ------------------------------------------------------------------
    # Phase 4: Confidence Assignment
    # ------------------------------------------------------------------

    @staticmethod
    def _assign_confidence(
        validated: list[EvidenceObject],
    ) -> list[EvidenceObject]:
        """Compute multi-dimensional confidence for each evidence object."""
        result: list[EvidenceObject] = []
        for ev in validated:
            strength = _compute_strength(ev)
            overall = strength.overall()
            result.append(EvidenceObject(
                identifier=ev.identifier,
                category=ev.category,
                epistemic_classification=ev.epistemic_classification,
                original_text=ev.original_text,
                normalized_text=ev.normalized_text,
                speaker=ev.speaker,
                confidence=overall,
                evidence_strength=strength,
                provenance=ev.provenance,
                temporal_scope=ev.temporal_scope,
                context=ev.context,
                validation_status=ev.validation_status,
            ))
        return result

    # ------------------------------------------------------------------
    # Phase 5: Provenance Construction
    # ------------------------------------------------------------------

    @staticmethod
    def _construct_provenance(
        confident: list[EvidenceObject],
        understanding_result: ConversationUnderstandingResult,
    ) -> list[EvidenceObject]:
        """Finalise the provenance chain on every evidence object."""
        result: list[EvidenceObject] = []
        for ev in confident:
            provenance = EvidenceProvenance(
                conversation_id=understanding_result.conversation_id,
                segment_id=ev.provenance.segment_id,
                speaker=ev.provenance.speaker,
                timestamp=ev.provenance.timestamp,
                engine_version='1.0.0',
                language='en',
                original_span=ev.provenance.original_span,
                normalized_representation=ev.provenance.normalized_representation,
                validation_history=(ev.validation_status,),
            )
            result.append(EvidenceObject(
                identifier=ev.identifier,
                category=ev.category,
                epistemic_classification=ev.epistemic_classification,
                original_text=ev.original_text,
                normalized_text=ev.normalized_text,
                speaker=ev.speaker,
                confidence=ev.confidence,
                evidence_strength=ev.evidence_strength,
                provenance=provenance,
                temporal_scope=ev.temporal_scope,
                context=ev.context,
                validation_status=ev.validation_status,
            ))
        return result

    # ------------------------------------------------------------------
    # Phase 6: Publication helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _summarize_validation(
        evidence: list[EvidenceObject],
    ) -> dict[str, int]:
        """Count evidence objects by validation status."""
        summary: dict[str, int] = {}
        for ev in evidence:
            summary[ev.validation_status] = summary.get(ev.validation_status, 0) + 1
        return summary

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_category(obj: Any) -> str:
        """Infer an evidence category from a semantic object's type."""
        type_map: dict[str, str] = {
            'entity': 'observed_event',
            'event': 'behavioral_report',
            'claim': 'self_report',
            'action': 'behavioral_report',
            'temporal_ref': 'observed_event',
            'location': 'observed_event',
            'person': 'observed_event',
        }
        return type_map.get(obj.object_type, 'interpretation_report')

    @staticmethod
    def _find_segment(
        obj: Any,
        seg_map: dict[str, Any],
    ) -> Any | None:
        """Locate the segment that owns a semantic object."""
        for seg in seg_map.values():
            if obj.surface_form in seg.text:
                return seg
        return None


# ---------------------------------------------------------------------------
# Strength computation
# ---------------------------------------------------------------------------


def _compute_strength(ev: EvidenceObject) -> EvidenceStrength:
    """Compute multi-dimensional strength for an evidence object."""
    # Directness: how directly was the evidence observed?
    directness_map: dict[str, float] = {
        'direct_observation': 0.9,
        'reported_observation': 0.7,
        'subjective_experience': 0.6,
        'remembered_event': 0.5,
        'interpretation': 0.4,
        'hypothesis': 0.3,
        'prediction': 0.3,
        'assumption': 0.2,
        'belief_report': 0.5,
        'narrative_report': 0.45,
        'identity_statement': 0.5,
        'question': 0.1,
        'commitment': 0.6,
        'preference': 0.5,
        'wish': 0.3,
        'fear': 0.4,
        'possibility': 0.2,
        'counterfactual': 0.15,
        'quotation': 0.8,
    }
    directness = directness_map.get(ev.epistemic_classification, 0.5)

    # Specificity: how specific is the evidence text?
    text_len = len(ev.original_text)
    if text_len > 80:
        specificity = 0.85
    elif text_len > 30:
        specificity = 0.65
    elif text_len > 10:
        specificity = 0.45
    else:
        specificity = 0.25

    # Temporal proximity: always moderate for real-time extraction
    temporal_proximity = 0.7

    # Consistency: validation status as proxy
    consistency_map: dict[str, float] = {
        'pass': 0.9,
        'pass_with_warning': 0.7,
        'requires_review': 0.4,
        'pending': 0.5,
    }
    consistency = consistency_map.get(ev.validation_status, 0.5)

    return EvidenceStrength(
        directness=directness,
        specificity=specificity,
        temporal_proximity=temporal_proximity,
        consistency=consistency,
    )
