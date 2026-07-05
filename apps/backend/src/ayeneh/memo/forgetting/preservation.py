"""MEM-08 Evidence preservation utilities.

Ensures essential knowledge survives compression by tracking what must
be retained and producing preservation records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.base import MemoryObject


@dataclass(frozen=True)
class PreservationRecord:
    """Record of preserved evidence from a compressed memory."""

    memory_id: str
    preserved_evidence_ids: tuple[str, ...] = ()
    preserved_confidence: float = 0.0
    preserved_importance: float = 0.0
    key_facts: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


def must_preserve(memory: MemoryObject) -> bool:
    """Determine if a memory's evidence must be preserved regardless of compression."""
    # Core memories are never fully discarded
    if memory.lifecycle_status == 'longitudinal_memory':
        return True
    # High-confidence memories with evidence should be preserved
    if memory.confidence > 0.8 and memory.supporting_evidence:
        return True
    # Memories with core importance
    if memory.importance_score > 0.9:
        return True
    return False


def create_preservation_record(memory: MemoryObject) -> PreservationRecord:
    """Create a preservation record for a memory being compressed."""
    key_facts: list[str] = []
    if memory.confidence > 0.5:
        key_facts.append(f'confidence={memory.confidence:.2f}')
    if memory.importance_score > 0.5:
        key_facts.append(f'importance={memory.importance_score:.2f}')
    key_facts.append(f'type={memory.memory_type}')
    key_facts.append(f'lifecycle={memory.lifecycle_status}')

    return PreservationRecord(
        memory_id=memory.identifier,
        preserved_evidence_ids=memory.supporting_evidence,
        preserved_confidence=memory.confidence,
        preserved_importance=memory.importance_score,
        key_facts=tuple(key_facts),
    )


def validate_preservation(
    original: MemoryObject,
    record: PreservationRecord,
) -> bool:
    """Validate that a preservation record adequately covers the original memory."""
    # Check all evidence is preserved
    original_evidence = set(original.supporting_evidence)
    preserved_evidence = set(record.preserved_evidence_ids)
    if not original_evidence.issubset(preserved_evidence):
        return False
    # Check confidence is not lost
    if record.preserved_confidence < original.confidence * 0.9:
        return False
    return True
