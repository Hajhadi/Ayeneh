"""Tests for MEM-10 Versioning module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ayeneh.memo.base import MemoryObject
from ayeneh.memo.versioning.engine import (
    VersioningEngine,
    analyse_revision,
    build_version_record,
    create_version,
    detect_differences,
    update_relationships,
)
from ayeneh.memo.versioning.lineage import LineageNode, LineageTree
from ayeneh.memo.versioning.snapshot import SnapshotDiff, SnapshotStore
from ayeneh.memo.versioning.types import (
    CognitiveSnapshot,
    DifferenceRecord,
    RevisionAnalysis,
    RevisionCategory,
    VersionChain,
    VersionComparison,
    VersionObject,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_memory(
    identifier: str = 'mem_1',
    importance: float = 0.5,
    confidence: float = 0.7,
    evidence: tuple[str, ...] = ('ev1',),
    lifecycle: str = 'validated_memory',
    memory_type: str = 'episodic',
) -> MemoryObject:
    return MemoryObject(
        identifier=identifier,
        memory_type=memory_type,
        creation_time=datetime.now(UTC) - timedelta(hours=2),
        last_updated=datetime.now(UTC),
        supporting_evidence=evidence,
        confidence=confidence,
        importance_score=importance,
        temporal_scope='short_term',
        lifecycle_status=lifecycle,
    )


def _version(num: int = 1, memory_id: str = 'mem_1', parent: str = '') -> VersionObject:
    return VersionObject(
        version_identifier=f'ver_{memory_id}_v{num}',
        parent_version=parent,
        target_memory=memory_id,
        version_number=num,
        confidence_before=0.5,
        confidence_after=0.7,
        revision_type=RevisionCategory.EXPANSION,
        reason_for_revision='test',
    )


# ---------------------------------------------------------------------------
# Difference detection
# ---------------------------------------------------------------------------

class TestDifferenceDetection:
    def test_no_differences(self) -> None:
        mem = _make_memory()
        diffs = detect_differences(mem, mem)
        assert len(diffs) == 0

    def test_confidence_change(self) -> None:
        old = _make_memory(confidence=0.5)
        new = _make_memory(confidence=0.8)
        diffs = detect_differences(old, new)
        assert any(d.field_name == 'confidence' for d in diffs)

    def test_multiple_changes(self) -> None:
        old = _make_memory(confidence=0.5, importance=0.3)
        new = _make_memory(confidence=0.9, importance=0.8)
        diffs = detect_differences(old, new)
        field_names = {d.field_name for d in diffs}
        assert 'confidence' in field_names
        assert 'importance_score' in field_names

    def test_evidence_change(self) -> None:
        old = _make_memory(evidence=('ev1',))
        new = _make_memory(evidence=('ev1', 'ev2'))
        diffs = detect_differences(old, new)
        assert any(d.field_name == 'supporting_evidence' for d in diffs)

    def test_numeric_significance(self) -> None:
        old = _make_memory(confidence=0.1)
        new = _make_memory(confidence=0.9)
        diffs = detect_differences(old, new)
        conf_diff = next(d for d in diffs if d.field_name == 'confidence')
        assert conf_diff.significance > 0.5


# ---------------------------------------------------------------------------
# Revision analysis
# ---------------------------------------------------------------------------

class TestRevisionAnalysis:
    def test_no_differences_no_version(self) -> None:
        analysis = analyse_revision('mem_1', [])
        assert analysis.should_create_version is False

    def test_confidence_update_category(self) -> None:
        diffs = [DifferenceRecord(field_name='confidence', old_value=0.5, new_value=0.8)]
        analysis = analyse_revision('mem_1', diffs)
        assert analysis.recommended_revision == RevisionCategory.CONFIDENCE_UPDATE

    def test_evidence_update_category(self) -> None:
        diffs = [DifferenceRecord(field_name='supporting_evidence', old_value=('ev1',), new_value=('ev1', 'ev2'))]
        analysis = analyse_revision('mem_1', diffs)
        assert analysis.recommended_revision == RevisionCategory.EVIDENCE_UPDATE

    def test_multiple_fields_generalization(self) -> None:
        diffs = [
            DifferenceRecord(field_name='confidence', old_value=0.5, new_value=0.8),
            DifferenceRecord(field_name='importance_score', old_value=0.3, new_value=0.9),
            DifferenceRecord(field_name='temporal_scope', old_value='short_term', new_value='long_term'),
            DifferenceRecord(field_name='lifecycle_status', old_value='candidate_memory', new_value='consolidated_memory'),
        ]
        analysis = analyse_revision('mem_1', diffs)
        assert analysis.recommended_revision == RevisionCategory.GENERALIZATION

    def test_confidence_delta_computed(self) -> None:
        diffs = [DifferenceRecord(field_name='confidence', old_value=0.3, new_value=0.8, significance=0.5)]
        analysis = analyse_revision('mem_1', diffs)
        assert abs(analysis.confidence_delta - 0.5) < 0.01


# ---------------------------------------------------------------------------
# Version creation
# ---------------------------------------------------------------------------

class TestVersionCreation:
    def test_create_first_version(self) -> None:
        mem = _make_memory(confidence=0.8)
        analysis = RevisionAnalysis(
            memory_id='mem_1',
            recommended_revision=RevisionCategory.EXPANSION,
            confidence_delta=0.3,
            rationale='test',
            should_create_version=True,
        )
        ver = create_version(None, 'mem_1', analysis, mem)
        assert ver.version_number == 1
        assert ver.parent_version == ''

    def test_create_subsequent_version(self) -> None:
        parent = _version(1)
        mem = _make_memory(confidence=0.8)
        analysis = RevisionAnalysis(
            memory_id='mem_1',
            recommended_revision=RevisionCategory.REFINEMENT,
            confidence_delta=0.1,
            rationale='test',
            should_create_version=True,
        )
        ver = create_version(parent, 'mem_1', analysis, mem)
        assert ver.version_number == 2
        assert ver.parent_version == parent.version_identifier


# ---------------------------------------------------------------------------
# Relationship update
# ---------------------------------------------------------------------------

class TestRelationshipUpdate:
    def test_update_relationships(self) -> None:
        ver = _version()
        updated = update_relationships(ver, affected_relationships=('rel1', 'rel2'))
        assert updated.affected_relationships == ('rel1', 'rel2')


# ---------------------------------------------------------------------------
# Version record building
# ---------------------------------------------------------------------------

class TestVersionRecord:
    def test_build_version_record(self) -> None:
        ver = _version()
        record = build_version_record(ver)
        assert isinstance(record, dict)
        assert record['version_number'] == 1
        assert 'change_reason' in record


# ---------------------------------------------------------------------------
# Version chain
# ---------------------------------------------------------------------------

class TestVersionChain:
    def test_empty_chain(self) -> None:
        chain = VersionChain(memory_id='mem_1')
        assert chain.latest is None
        assert chain.current_version_number == 0

    def test_chain_with_versions(self) -> None:
        v1 = _version(1)
        v2 = _version(2, parent=v1.version_identifier)
        chain = VersionChain(memory_id='mem_1', versions=(v1, v2), current_version_number=2)
        assert chain.latest is v2


# ---------------------------------------------------------------------------
# Versioning engine
# ---------------------------------------------------------------------------

class TestVersioningEngine:
    def test_process_update_creates_version(self) -> None:
        engine = VersioningEngine()
        old = _make_memory(confidence=0.5)
        new = _make_memory(confidence=0.8)
        ver = engine.process_update(old, new)
        assert ver is not None
        assert ver.version_number == 1

    def test_process_no_change_returns_none(self) -> None:
        engine = VersioningEngine()
        mem = _make_memory()
        ver = engine.process_update(mem, mem)
        assert ver is None

    def test_chain_grows(self) -> None:
        engine = VersioningEngine()
        old = _make_memory(confidence=0.3)
        new1 = _make_memory(confidence=0.6)
        engine.process_update(old, new1)

        new2 = _make_memory(confidence=0.9)
        ver2 = engine.process_update(new1, new2)
        assert ver2 is not None
        assert ver2.version_number == 2

    def test_compare_versions(self) -> None:
        engine = VersioningEngine()
        old = _make_memory(confidence=0.3)
        new = _make_memory(confidence=0.8)
        engine.process_update(old, new)
        comparison = engine.compare_versions('mem_1', 0, 1)
        assert isinstance(comparison, VersionComparison)

    def test_create_snapshot(self) -> None:
        engine = VersioningEngine()
        old = _make_memory(confidence=0.3)
        new = _make_memory(confidence=0.8)
        engine.process_update(old, new)
        snapshot = engine.create_snapshot(active_goals=('g1',))
        assert isinstance(snapshot, CognitiveSnapshot)
        assert 'mem_1' in snapshot.memory_versions


# ---------------------------------------------------------------------------
# Lineage tree
# ---------------------------------------------------------------------------

class TestLineageTree:
    def test_add_version(self) -> None:
        tree = LineageTree(memory_id='mem_1')
        v1 = _version(1)
        tree.add_version(v1)
        assert tree.root == v1.version_identifier

    def test_ancestors(self) -> None:
        tree = LineageTree(memory_id='mem_1')
        v1 = _version(1)
        v2 = _version(2, parent=v1.version_identifier)
        tree.add_version(v1)
        tree.add_version(v2)
        ancestors = tree.get_ancestors(v2.version_identifier)
        assert len(ancestors) == 2
        assert ancestors[0].version_number == 1

    def test_descendants(self) -> None:
        tree = LineageTree(memory_id='mem_1')
        v1 = _version(1)
        v2 = _version(2, parent=v1.version_identifier)
        v3 = _version(3, parent=v2.version_identifier)
        tree.add_version(v1)
        tree.add_version(v2)
        tree.add_version(v3)
        descendants = tree.get_descendants(v1.version_identifier)
        assert len(descendants) == 3

    def test_get_latest(self) -> None:
        tree = LineageTree(memory_id='mem_1')
        v1 = _version(1)
        v2 = _version(2)
        tree.add_version(v1)
        tree.add_version(v2)
        latest = tree.get_latest()
        assert latest is not None
        assert latest.version_number == 2

    def test_depth(self) -> None:
        tree = LineageTree(memory_id='mem_1')
        v1 = _version(1)
        v2 = _version(2, parent=v1.version_identifier)
        tree.add_version(v1)
        tree.add_version(v2)
        assert tree.depth() == 1


# ---------------------------------------------------------------------------
# Snapshot store
# ---------------------------------------------------------------------------

class TestSnapshotStore:
    def test_save_and_get(self) -> None:
        store = SnapshotStore()
        snap = CognitiveSnapshot(snapshot_id='s1')
        store.save(snap)
        assert store.get('s1') is snap

    def test_list_snapshots_order(self) -> None:
        store = SnapshotStore()
        store.save(CognitiveSnapshot(snapshot_id='s1'))
        store.save(CognitiveSnapshot(snapshot_id='s2'))
        snaps = store.list_snapshots()
        assert len(snaps) == 2
        assert snaps[0].snapshot_id == 's1'

    def test_latest(self) -> None:
        store = SnapshotStore()
        store.save(CognitiveSnapshot(snapshot_id='s1'))
        store.save(CognitiveSnapshot(snapshot_id='s2'))
        assert store.latest().snapshot_id == 's2'

    def test_diff(self) -> None:
        store = SnapshotStore()
        store.save(CognitiveSnapshot(snapshot_id='s1', memory_versions={'m1': 1}))
        store.save(CognitiveSnapshot(snapshot_id='s2', memory_versions={'m1': 2, 'm2': 1}))
        diff = store.diff('s1', 's2')
        assert isinstance(diff, SnapshotDiff)
        assert 'm2' in diff.added_memories
        assert 'm1' in diff.changed_memories

    def test_restore(self) -> None:
        store = SnapshotStore()
        store.save(CognitiveSnapshot(snapshot_id='s1', memory_versions={'m1': 1}))
        restored = store.restore('s1')
        assert restored is not None
        assert restored.snapshot_id == 'restored_s1'
        assert restored.memory_versions == {'m1': 1}

    def test_between(self) -> None:
        store = SnapshotStore()
        now = datetime.now(UTC)
        store.save(CognitiveSnapshot(snapshot_id='s1', timestamp=now - timedelta(hours=2)))
        store.save(CognitiveSnapshot(snapshot_id='s2', timestamp=now))
        between = store.between(now - timedelta(hours=1), now + timedelta(hours=1))
        assert len(between) == 1
