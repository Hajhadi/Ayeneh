"""MEM-10 Version lineage tracking.

Tracks the ancestry, descendants, and lineage of memory versions,
enabling traversal of the version tree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from ayeneh.memo.versioning.types import VersionObject


@dataclass(frozen=True)
class LineageNode:
    """A node in the version lineage tree."""

    version: VersionObject
    children: tuple[str, ...] = ()  # version_identifiers of children


@dataclass
class LineageTree:
    """Full lineage tree for a single memory."""

    memory_id: str = ''
    nodes: dict[str, LineageNode] = field(default_factory=dict)
    root: str = ''  # version_identifier of root

    def add_version(self, version: VersionObject) -> None:
        """Add a version to the lineage tree."""
        node = LineageNode(version=version)
        self.nodes[version.version_identifier] = node

        if version.parent_version and version.parent_version in self.nodes:
            parent = self.nodes[version.parent_version]
            self.nodes[version.parent_version] = LineageNode(
                version=parent.version,
                children=parent.children + (version.version_identifier,),
            )
        elif not self.root:
            self.root = version.version_identifier

    def get_ancestors(self, version_id: str) -> list[VersionObject]:
        """Get all ancestors of a version (root → version)."""
        ancestors: list[VersionObject] = []
        current = version_id
        visited: set[str] = set()
        while current and current in self.nodes and current not in visited:
            visited.add(current)
            node = self.nodes[current]
            ancestors.append(node.version)
            parent_id = node.version.parent_version
            current = parent_id
        ancestors.reverse()
        return ancestors

    def get_descendants(self, version_id: str) -> list[VersionObject]:
        """Get all descendants of a version (version → leaves)."""
        descendants: list[VersionObject] = []
        queue = [version_id]
        visited: set[str] = set()
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            node = self.nodes.get(current)
            if node:
                descendants.append(node.version)
                queue.extend(node.children)
        return descendants

    def get_latest(self) -> VersionObject | None:
        """Get the latest version (leaf with highest version number)."""
        if not self.nodes:
            return None
        return max(
            (n.version for n in self.nodes.values()),
            key=lambda v: v.version_number,
        )

    def depth(self) -> int:
        """Get the depth of the lineage tree."""
        if not self.root:
            return 0
        max_d = 0
        queue: list[tuple[str, int]] = [(self.root, 0)]
        visited: set[str] = set()
        while queue:
            current, d = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            max_d = max(max_d, d)
            node = self.nodes.get(current)
            if node:
                for child in node.children:
                    queue.append((child, d + 1))
        return max_d
