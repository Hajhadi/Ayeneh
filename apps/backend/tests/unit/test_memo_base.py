"""Tests for MEM-01 foundation types: MemoryObject, lifecycle, consolidation."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.memo.base import (
    CONSOLIDATION_LEVELS,
    CONSOLIDATION_LEVEL_VALUES,
    MEMORY_LIFECYCLE,
    MEMORY_LIFECYCLE_TRANSITIONS,
    MEMORY_TYPES,
    RELATIONSHIP_TYPES,
    TEMPORAL_SCOPES,
    EvidenceRef,
    MemoryObject,
    can_memory_transition,
    make_version_record,
)


# ===================================================================
# Constants
# ===================================================================

class TestConstants:
    def test_lifecycle_has_six_stages(self) -> None:
        assert len(MEMORY_LIFECYCLE) == 6

    def test_lifecycle_starts_with_conversation(self) -> None:
        assert MEMORY_LIFECYCLE[0] == 'conversation'

    def test_lifecycle_ends_with_historical(self) -> None:
        assert MEMORY_LIFECYCLE[-1] == 'historical_memory'

    def test_consolidation_has_five_levels(self) -> None:
        assert len(CONSOLIDATION_LEVELS) == 5

    def test_consolidation_level_values_are_sequential(self) -> None:
        for i, level in enumerate(CONSOLIDATION_LEVELS):
            assert CONSOLIDATION_LEVEL_VALUES[level] == i

    def test_memory_types_cover_all_modules(self) -> None:
        assert 'episodic' in MEMORY_TYPES
        assert 'semantic_personal' in MEMORY_TYPES
        assert 'working' in MEMORY_TYPES
        assert 'consolidation' in MEMORY_TYPES
        assert 'evidence' in MEMORY_TYPES
        assert 'relationship' in MEMORY_TYPES
        assert 'meta_cognitive' in MEMORY_TYPES

    def test_relationship_types_has_ten(self) -> None:
        assert len(RELATIONSHIP_TYPES) == 10

    def test_temporal_scopes(self) -> None:
        assert 'momentary' in TEMPORAL_SCOPES
        assert 'long_term' in TEMPORAL_SCOPES
        assert 'recurring' in TEMPORAL_SCOPES


# ===================================================================
# Lifecycle transitions
# ===================================================================

class TestLifecycleTransitions:
    def test_conversation_to_candidate(self) -> None:
        assert can_memory_transition('conversation', 'candidate_memory')

    def test_candidate_to_validated(self) -> None:
        assert can_memory_transition('candidate_memory', 'validated_memory')

    def test_validated_to_consolidated(self) -> None:
        assert can_memory_transition('validated_memory', 'consolidated_memory')

    def test_consolidated_to_longitudinal(self) -> None:
        assert can_memory_transition('consolidated_memory', 'longitudinal_memory')

    def test_longitudinal_to_historical(self) -> None:
        assert can_memory_transition('longitudinal_memory', 'historical_memory')

    def test_historical_has_no_transitions(self) -> None:
        assert can_memory_transition('historical_memory', 'anything') is False

    def test_invalid_transition(self) -> None:
        assert can_memory_transition('conversation', 'historical_memory') is False

    def test_reverse_transitions_exist(self) -> None:
        assert can_memory_transition('candidate_memory', 'conversation')
        assert can_memory_transition('validated_memory', 'candidate_memory')
        assert can_memory_transition('consolidated_memory', 'validated_memory')
        assert can_memory_transition('longitudinal_memory', 'consolidated_memory')


# ===================================================================
# EvidenceRef
# ===================================================================

class TestEvidenceRef:
    def test_creation(self) -> None:
        ref = EvidenceRef(
            evidence_id='ev-1',
            evidence_type='self_report',
            confidence=0.8,
            timestamp=datetime.now(UTC),
        )
        assert ref.evidence_id == 'ev-1'
        assert ref.confidence == 0.8

    def test_frozen(self) -> None:
        ref = EvidenceRef(
            evidence_id='ev-1',
            evidence_type='self_report',
            confidence=0.8,
            timestamp=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            ref.evidence_id = 'ev-2'  # type: ignore[misc]


# ===================================================================
# MemoryObject
# ===================================================================

class TestMemoryObject:
    def test_creation_with_required_fields(self) -> None:
        now = datetime.now(UTC)
        obj = MemoryObject(
            identifier='mem-1',
            memory_type='episodic',
            creation_time=now,
        )
        assert obj.identifier == 'mem-1'
        assert obj.memory_type == 'episodic'
        assert obj.creation_time == now

    def test_defaults(self) -> None:
        obj = MemoryObject(
            identifier='mem-2',
            memory_type='semantic_personal',
            creation_time=datetime.now(UTC),
        )
        assert obj.confidence == 0.0
        assert obj.importance_score == 0.0
        assert obj.temporal_scope == 'momentary'
        assert obj.lifecycle_status == 'candidate_memory'
        assert obj.supporting_evidence == ()
        assert obj.associated_cognitive_objects == ()
        assert obj.associated_episodes == ()
        assert obj.associated_projects == ()
        assert obj.associated_people == ()
        assert obj.associated_places == ()
        assert obj.associated_conversations == ()
        assert obj.version_history == ()
        assert obj.explainability_metadata == {}

    def test_frozen(self) -> None:
        obj = MemoryObject(
            identifier='mem-3',
            memory_type='working',
            creation_time=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            obj.identifier = 'mem-4'  # type: ignore[misc]

    def test_is_canonical_false_by_default(self) -> None:
        obj = MemoryObject(
            identifier='mem-5',
            memory_type='episodic',
            creation_time=datetime.now(UTC),
        )
        assert obj.is_canonical() is False

    def test_is_canonical_when_longitudinal(self) -> None:
        obj = MemoryObject(
            identifier='mem-6',
            memory_type='episodic',
            creation_time=datetime.now(UTC),
            lifecycle_status='longitudinal_memory',
        )
        assert obj.is_canonical() is True

    def test_can_transition_to_valid(self) -> None:
        obj = MemoryObject(
            identifier='mem-7',
            memory_type='episodic',
            creation_time=datetime.now(UTC),
            lifecycle_status='conversation',
        )
        assert obj.can_transition_to('candidate_memory') is True

    def test_can_transition_to_invalid(self) -> None:
        obj = MemoryObject(
            identifier='mem-8',
            memory_type='episodic',
            creation_time=datetime.now(UTC),
            lifecycle_status='conversation',
        )
        assert obj.can_transition_to('historical_memory') is False

    def test_with_all_fields(self) -> None:
        now = datetime.now(UTC)
        obj = MemoryObject(
            identifier='mem-9',
            memory_type='consolidation',
            creation_time=now,
            last_updated=now,
            supporting_evidence=('ev-1', 'ev-2'),
            confidence=0.9,
            importance_score=0.8,
            temporal_scope='long_term',
            associated_cognitive_objects=('cog-1',),
            associated_episodes=('ep-1',),
            associated_projects=('proj-1',),
            associated_people=('person-1',),
            associated_places=('place-1',),
            associated_conversations=('conv-1',),
            version_history=(make_version_record(version_number=1, changed_fields={}, change_reason='init'),),
            lifecycle_status='consolidated_memory',
            explainability_metadata={'reason': 'test'},
        )
        assert obj.supporting_evidence == ('ev-1', 'ev-2')
        assert obj.confidence == 0.9
        assert len(obj.version_history) == 1


# ===================================================================
# make_version_record
# ===================================================================

class TestMakeVersionRecord:
    def test_basic(self) -> None:
        record = make_version_record(
            version_number=1,
            changed_fields={'confidence': 0.5},
            change_reason='initial',
        )
        assert record['version_number'] == 1
        assert record['changed_fields'] == {'confidence': 0.5}
        assert record['change_reason'] == 'initial'
        assert 'timestamp' in record

    def test_custom_timestamp(self) -> None:
        ts = datetime(2025, 1, 1, tzinfo=UTC)
        record = make_version_record(
            version_number=2,
            changed_fields={},
            change_reason='update',
            timestamp=ts,
        )
        assert record['timestamp'] == ts.isoformat()
