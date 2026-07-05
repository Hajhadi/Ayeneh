"""MEM-10 Cognitive snapshot management.

Manages creation, storage, and retrieval of cognitive snapshots —
complete captures of cognitive state at a point in time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.versioning.types import CognitiveSnapshot, VersionChain


@dataclass
class SnapshotStore:
    """Persistent store for cognitive snapshots."""

    _snapshots: dict[str, CognitiveSnapshot] = field(default_factory=dict)
    _index: list[str] = field(default_factory=list)  # ordered by creation time

    def save(self, snapshot: CognitiveSnapshot) -> None:
        """Save a snapshot to the store."""
        self._snapshots[snapshot.snapshot_id] = snapshot
        self._index.append(snapshot.snapshot_id)

    def get(self, snapshot_id: str) -> CognitiveSnapshot | None:
        return self._snapshots.get(snapshot_id)

    def list_snapshots(self) -> list[CognitiveSnapshot]:
        """Return all snapshots in chronological order."""
        return [self._snapshots[sid] for sid in self._index if sid in self._snapshots]

    def latest(self) -> CognitiveSnapshot | None:
        """Return the most recent snapshot."""
        if not self._index:
            return None
        return self._snapshots.get(self._index[-1])

    def between(
        self,
        start: datetime,
        end: datetime,
    ) -> list[CognitiveSnapshot]:
        """Return snapshots created between start and end."""
        result: list[CognitiveSnapshot] = []
        for sid in self._index:
            snap = self._snapshots.get(sid)
            if snap and start <= snap.timestamp <= end:
                result.append(snap)
        return result

    def diff(self, snap_a_id: str, snap_b_id: str) -> SnapshotDiff:
        """Compute the difference between two snapshots."""
        snap_a = self._snapshots.get(snap_a_id)
        snap_b = self._snapshots.get(snap_b_id)
        if snap_a is None or snap_b is None:
            return SnapshotDiff(
                summary='One or both snapshots not found',
            )

        added_memories = set(snap_b.memory_versions.keys()) - set(snap_a.memory_versions.keys())
        removed_memories = set(snap_a.memory_versions.keys()) - set(snap_b.memory_versions.keys())
        changed_memories: dict[str, tuple[int, int]] = {}
        for mid in set(snap_a.memory_versions) & set(snap_b.memory_versions):
            va = snap_a.memory_versions[mid]
            vb = snap_b.memory_versions[mid]
            if va != vb:
                changed_memories[mid] = (va, vb)

        return SnapshotDiff(
            snapshot_a=snap_a_id,
            snapshot_b=snap_b_id,
            added_memories=tuple(added_memories),
            removed_memories=tuple(removed_memories),
            changed_memories=changed_memories,
            summary=f'{len(added_memories)} added, {len(removed_memories)} removed, {len(changed_memories)} changed',
        )

    def restore(self, snapshot_id: str) -> CognitiveSnapshot | None:
        """Retrieve a snapshot for restoration purposes."""
        snap = self._snapshots.get(snapshot_id)
        if snap is None:
            return None
        # Return a copy with a new snapshot_id to indicate restoration
        return CognitiveSnapshot(
            snapshot_id=f'restored_{snapshot_id}',
            timestamp=datetime.now(UTC),
            memory_versions=dict(snap.memory_versions),
            knowledge_graph_version=snap.knowledge_graph_version,
            active_goals=snap.active_goals,
            active_projects=snap.active_projects,
            identity_state=dict(snap.identity_state),
            belief_state=dict(snap.belief_state),
            metadata={**snap.metadata, 'restored_from': snapshot_id},
        )

    def capture_snapshot(
        self,
        user_id: str,
        memories: list[Any],
        beliefs: list[Any] | None = None,
        narratives: list[Any] | None = None,
        identity: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Capture a complete cognitive state summary.

        Analyses the provided memory objects and returns a dict describing
        the state at this point in time, including counts broken down by
        lifecycle status.
        """
        active_count = 0
        dormant_count = 0
        for m in memories:
            state = getattr(m, 'lifecycle_state', '') or getattr(m, 'lifecycle_status', '') or ''
            if state in ('consolidated_memory', 'longitudinal_memory', 'consolidated', 'longitudinal'):
                active_count += 1
            elif state in ('dormant', 'archived'):
                dormant_count += 1

        snapshot: dict[str, Any] = {
            'user_id': user_id,
            'timestamp': datetime.now(UTC).isoformat(),
            'memories': len(memories),
            'beliefs': len(beliefs or []),
            'narratives': len(narratives or []),
            'identity_components': len(identity or []),
            'active_memories': active_count,
            'dormant_memories': dormant_count,
        }

        # Persist as a CognitiveSnapshot
        versions: dict[str, int] = {}
        for i, m in enumerate(memories):
            mid = getattr(m, 'identifier', f'mem_{i}')
            versions[mid] = 1

        cognitive_snap = CognitiveSnapshot(
            snapshot_id=f'capture_{int(datetime.now(UTC).timestamp())}_{user_id}',
            memory_versions=versions,
            knowledge_graph_version=1,
            active_goals=tuple(),
            active_projects=tuple(),
            identity_state={},
            belief_state={},
            metadata={'capture_summary': snapshot},
        )
        self.save(cognitive_snap)

        return snapshot


@dataclass(frozen=True)
class SnapshotDiff:
    """Difference between two cognitive snapshots."""

    snapshot_a: str = ''
    snapshot_b: str = ''
    added_memories: tuple[str, ...] = ()
    removed_memories: tuple[str, ...] = ()
    changed_memories: dict[str, tuple[int, int]] = field(default_factory=dict)
    summary: str = ''
