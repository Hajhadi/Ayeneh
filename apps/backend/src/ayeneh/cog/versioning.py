"""Temporal versioning for COG cognitive objects.

Every revision creates a new immutable version. Previous versions are
preserved, enabling time-travel queries and change-rate analytics.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CognitiveVersionManager:
    """Manages versioned cognitive objects with immutable history."""

    def __init__(self) -> None:
        self._versions: dict[str, list[dict]] = {}  # object_id -> [version_dicts]

    def create_version(
        self,
        obj: Any,
        change_reason: str = "",
        evidence_ref: str = "",
    ) -> dict:
        """Create a new version of a cognitive object.

        1. Snapshot current state as a version entry.
        2. Append to the version history.
        3. Return the version record.
        """
        obj_id = getattr(obj, "identifier", None) or str(uuid.uuid4())

        snapshot: dict[str, Any] = {
            "version_id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "change_reason": change_reason,
            "evidence_ref": evidence_ref,
            "state": self._snapshot_state(obj),
        }

        if obj_id not in self._versions:
            self._versions[obj_id] = []
        self._versions[obj_id].append(snapshot)

        logger.info(
            "cog.version_created",
            object_id=obj_id,
            version=len(self._versions[obj_id]),
        )
        return snapshot

    def get_versions(self, obj_id: str) -> list[dict]:
        """Get all versions of a cognitive object."""
        return list(self._versions.get(obj_id, []))

    def get_latest_version(self, obj_id: str) -> dict | None:
        """Get the most recent version."""
        versions = self._versions.get(obj_id, [])
        return versions[-1] if versions else None

    def get_version_at(self, obj_id: str, timestamp: datetime) -> dict | None:
        """Get the version that was active at a given timestamp.

        Walks backward through the version list and returns the first
        version whose timestamp is <= the given timestamp.
        """
        versions = self._versions.get(obj_id, [])
        for v in reversed(versions):
            v_ts = datetime.fromisoformat(v["timestamp"])
            if v_ts <= timestamp:
                return v
        return versions[0] if versions else None

    def compute_change_rate(self, obj_id: str) -> float:
        """Compute rate of change (revisions per day).

        Returns 0.0 when there are fewer than 2 versions or the span
        is zero.
        """
        versions = self._versions.get(obj_id, [])
        if len(versions) < 2:
            return 0.0
        first = datetime.fromisoformat(versions[0]["timestamp"])
        last = datetime.fromisoformat(versions[-1]["timestamp"])
        days = max((last - first).total_seconds() / 86400, 1.0)
        return len(versions) / days

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _snapshot_state(obj: Any) -> dict:
        """Create a serializable snapshot of an object's state.

        Frozen dataclasses expose their fields via ``__dict__``; plain
        objects do as well.  Private/dunder attributes are excluded.
        """
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return {"value": str(obj)}
