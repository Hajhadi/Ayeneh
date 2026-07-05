"""Evidence types for the Ayeneh COG architecture (COG-02, COG-03).

Defines EvidenceObject — the fundamental unit of evidence — along with its
supporting value objects (EvidenceStrength, EvidenceProvenance, EvidenceContext)
and the authoritative catalogue enumerations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

EVIDENCE_CATEGORIES: list[str] = [
    'observed_event', 'self_report', 'behavioral_report', 'emotional_report',
    'memory_report', 'interpretation_report', 'prediction', 'question',
    'hypothesis', 'assumption', 'intention', 'commitment', 'preference',
    'decision_report', 'relationship_report', 'meta_cognitive_report',
    'narrative_report', 'identity_statement', 'value_statement', 'goal_statement',
]

EPISTEMIC_CLASSIFICATIONS: list[str] = [
    'direct_observation', 'reported_observation', 'subjective_experience',
    'remembered_event', 'interpretation', 'hypothesis', 'prediction',
    'assumption', 'belief_report', 'narrative_report', 'identity_statement',
    'question', 'commitment', 'preference', 'wish', 'fear', 'possibility',
    'counterfactual', 'quotation',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvidenceStrength:
    """Multi-dimensional strength assessment of an evidence object."""

    directness: float = 0.5
    specificity: float = 0.5
    temporal_proximity: float = 0.5
    consistency: float = 0.5

    def overall(self) -> float:
        """Weighted average across all dimensions."""
        return (
            self.directness * 0.35
            + self.specificity * 0.25
            + self.temporal_proximity * 0.20
            + self.consistency * 0.20
        )


@dataclass(frozen=True)
class EvidenceProvenance:
    """Full provenance chain for an evidence object."""

    conversation_id: str = ''
    segment_id: str = ''
    sentence_id: str = ''
    speaker: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    engine_version: str = '1.0.0'
    language: str = 'en'
    original_span: tuple[int, int] = (0, 0)
    normalized_representation: str = ''
    validation_history: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceContext:
    """Contextual dimensions surrounding the evidence."""

    physical: str = ''
    social: str = ''
    project: str = ''
    emotional: str = ''


# ---------------------------------------------------------------------------
# EvidenceObject — the fundamental unit (COG-02)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvidenceObject:
    """Atomic unit of evidence extracted from a conversation.

    Every downstream cognitive object (beliefs, narratives, identity components,
    …) references one or more EvidenceObjects to ground its claims.
    """

    identifier: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ''            # one of EVIDENCE_CATEGORIES
    epistemic_classification: str = ''  # one of EPISTEMIC_CLASSIFICATIONS
    original_text: str = ''
    normalized_text: str = ''
    speaker: str = ''
    confidence: float = 0.0
    evidence_strength: EvidenceStrength = field(default_factory=EvidenceStrength)
    provenance: EvidenceProvenance = field(default_factory=EvidenceProvenance)
    temporal_scope: str = 'momentary'
    context: EvidenceContext = field(default_factory=EvidenceContext)
    validation_status: str = 'pending'
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
