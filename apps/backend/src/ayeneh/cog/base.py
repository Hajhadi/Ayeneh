"""Core types shared by all cognitive objects in the Ayeneh COG architecture.

This module defines the foundational dataclasses that every COG module depends on:
CognitiveObject (COG-03), EvidenceRef, TemporalMetadata, Revision, and the
lifecycle state machine.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Lifecycle state machine
# ---------------------------------------------------------------------------

LIFECYCLE_TRANSITIONS: dict[str, list[str]] = {
    'evidence_candidate': ['candidate'],
    'candidate': ['provisional', 'evidence_candidate'],
    'provisional': ['validation', 'candidate'],
    'validation': ['canonical', 'provisional'],
    'canonical': ['evidence_expansion', 'revision', 'historical'],
    'evidence_expansion': ['canonical', 'revision'],
    'revision': ['canonical', 'historical'],
    'historical': [],
}


def can_transition(current: str, target: str) -> bool:
    """Return True if *target* is a legal next state from *current*."""
    allowed = LIFECYCLE_TRANSITIONS.get(current, [])
    return target in allowed


# ---------------------------------------------------------------------------
# EvidenceRef — lightweight reference to an EvidenceObject
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvidenceRef:
    """Immutable reference to an EvidenceObject stored elsewhere."""

    evidence_id: str
    evidence_type: str
    confidence: float
    timestamp: datetime


# ---------------------------------------------------------------------------
# TemporalMetadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TemporalMetadata:
    """Tracks when an object was observed and its temporal scope."""

    first_observed: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_observed: datetime = field(default_factory=lambda: datetime.now(UTC))
    observation_count: int = 1
    temporal_scope: str = 'momentary'  # momentary|short_term|long_term|historical|recurring


# ---------------------------------------------------------------------------
# Revision — immutable change record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Revision:
    """Immutable snapshot of a state change for audit purposes."""

    revision_id: str
    timestamp: datetime
    previous_state: dict[str, Any]
    change_reason: str
    evidence_ref: EvidenceRef | None = None


# ---------------------------------------------------------------------------
# CognitiveObject — base for all 16 cognitive object types (COG-03)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CognitiveObject:
    """Base dataclass for every cognitive object in the COG architecture.

    Subclasses and downstream modules specialise via *object_type* and
    additional fields; the core fields live here so that the graph layer,
    confidence engine, and lifecycle manager can operate generically.
    """

    identifier: str = field(default_factory=lambda: str(uuid.uuid4()))
    object_type: str = ''
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    evidence_references: tuple[EvidenceRef, ...] = ()
    contradictory_evidence: tuple[EvidenceRef, ...] = ()
    meta_evidence: tuple[EvidenceRef, ...] = ()
    confidence: float = 0.0
    temporal_metadata: TemporalMetadata = field(default_factory=TemporalMetadata)
    lifecycle_state: str = 'evidence_candidate'
    revision_history: tuple[Revision, ...] = ()
    validation_status: str = 'pending'
    specification_version: str = '1.0.0'

    # -- convenience helpers -------------------------------------------------

    def is_canonical(self) -> bool:
        """Return True when the object has reached canonical status."""
        return self.lifecycle_state == 'canonical'

    def with_transition(self, target: str) -> CognitiveObject:
        """Return a new instance with the lifecycle advanced to *target*.

        Raises ``ValueError`` if the transition is not permitted.
        """
        if not can_transition(self.lifecycle_state, target):
            raise ValueError(
                f"Invalid lifecycle transition: {self.lifecycle_state} -> {target}"
            )
        rev = Revision(
            revision_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC),
            previous_state={'lifecycle_state': self.lifecycle_state},
            change_reason=f'lifecycle {self.lifecycle_state} -> {target}',
        )
        # dataclass(frozen=True) → use object.__setattr__ for the new copy
        new = object.__new__(CognitiveObject)
        object.__setattr__(new, 'identifier', self.identifier)
        object.__setattr__(new, 'object_type', self.object_type)
        object.__setattr__(new, 'creation_timestamp', self.creation_timestamp)
        object.__setattr__(new, 'evidence_references', self.evidence_references)
        object.__setattr__(new, 'contradictory_evidence', self.contradictory_evidence)
        object.__setattr__(new, 'meta_evidence', self.meta_evidence)
        object.__setattr__(new, 'confidence', self.confidence)
        object.__setattr__(new, 'temporal_metadata', self.temporal_metadata)
        object.__setattr__(new, 'lifecycle_state', target)
        object.__setattr__(new, 'revision_history', self.revision_history + (rev,))
        object.__setattr__(new, 'validation_status', self.validation_status)
        object.__setattr__(new, 'specification_version', self.specification_version)
        return new
