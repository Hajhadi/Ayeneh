"""Evidence Repository for the Ayeneh COG architecture (COG-02).

In-memory evidence store with query capabilities.  Provides storage,
retrieval, and filtered queries over validated EvidenceObjects.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from ayeneh.cog.evidence.types import EvidenceObject

logger = structlog.get_logger(__name__)


class EvidenceRepository:
    """In-memory evidence store with indexed query capabilities.

    Indices are maintained on ``speaker`` and ``category`` for fast lookups.
    All stored evidence objects are frozen and immutable.
    """

    def __init__(self) -> None:
        self._evidence: dict[str, EvidenceObject] = {}
        self._by_speaker: dict[str, list[str]] = {}
        self._by_category: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def store(self, evidence: EvidenceObject) -> None:
        """Store an evidence object and update indices."""
        self._evidence[evidence.identifier] = evidence

        # Speaker index
        speaker = evidence.speaker
        if speaker:
            self._by_speaker.setdefault(speaker, []).append(evidence.identifier)

        # Category index
        category = evidence.category
        if category:
            self._by_category.setdefault(category, []).append(evidence.identifier)

        logger.info(
            'cog.evidence.repository.stored',
            evidence_id=evidence.identifier,
            speaker=speaker,
            category=category,
        )

    def store_batch(self, evidence_list: list[EvidenceObject]) -> None:
        """Store multiple evidence objects."""
        for ev in evidence_list:
            self.store(ev)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, evidence_id: str) -> EvidenceObject | None:
        """Return the evidence object with *evidence_id*, or ``None``."""
        return self._evidence.get(evidence_id)

    def count(self) -> int:
        """Return the total number of stored evidence objects."""
        return len(self._evidence)

    def all(self) -> list[EvidenceObject]:
        """Return all stored evidence objects."""
        return list(self._evidence.values())

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def query_by_speaker(self, speaker: str) -> list[EvidenceObject]:
        """Return all evidence objects for *speaker*."""
        ids = self._by_speaker.get(speaker, [])
        return [self._evidence[eid] for eid in ids if eid in self._evidence]

    def query_by_category(self, category: str) -> list[EvidenceObject]:
        """Return all evidence objects in *category*."""
        ids = self._by_category.get(category, [])
        return [self._evidence[eid] for eid in ids if eid in self._evidence]

    def query_by_time_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[EvidenceObject]:
        """Return evidence objects whose creation timestamp falls in the range."""
        results: list[EvidenceObject] = []
        for ev in self._evidence.values():
            ts = ev.provenance.timestamp
            if start <= ts <= end:
                results.append(ev)
        return results

    def query_by_status(self, status: str) -> list[EvidenceObject]:
        """Return evidence objects with the given validation status."""
        return [
            ev for ev in self._evidence.values()
            if ev.validation_status == status
        ]

    def query_by_min_confidence(self, min_confidence: float) -> list[EvidenceObject]:
        """Return evidence objects with confidence >= *min_confidence*."""
        return [
            ev for ev in self._evidence.values()
            if ev.confidence >= min_confidence
        ]

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def remove(self, evidence_id: str) -> bool:
        """Remove an evidence object by id.  Returns True if found."""
        ev = self._evidence.pop(evidence_id, None)
        if ev is None:
            return False

        # Update speaker index
        if ev.speaker in self._by_speaker:
            self._by_speaker[ev.speaker] = [
                eid for eid in self._by_speaker[ev.speaker] if eid != evidence_id
            ]

        # Update category index
        if ev.category in self._by_category:
            self._by_category[ev.category] = [
                eid for eid in self._by_category[ev.category] if eid != evidence_id
            ]

        return True

    def clear(self) -> None:
        """Remove all stored evidence objects."""
        self._evidence.clear()
        self._by_speaker.clear()
        self._by_category.clear()
