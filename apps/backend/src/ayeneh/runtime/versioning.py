"""Version tracking per SPEC-01A RP-06.

Every execution shall record:
- graph version
- knowledge version
- reasoning version
- policy version
- provider version
- interpretation version
- router version

Every result shall therefore be reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Engine Versions (single source of truth)
# ---------------------------------------------------------------------------

ENGINE_VERSIONS: dict[str, str] = {
    "pipeline": "1.0.0",
    "dialogue": "1.0.0",
    "graph_reasoning": "1.0.0",
    "interpretation": "1.0.0",
    "epistemic_safety": "1.0.0",
    "knowledge_concepts": "1.0.0",
    "cross_book_linking": "1.0.0",
    "knowledge_curation": "1.0.0",
    "profile_generator": "1.0.0",
    "hierarchical_profile": "1.0.0",
    "ai_router": "1.0.0",
    "query_concept_resolver": "1.0.0",
}


# ---------------------------------------------------------------------------
# Runtime Versions (per SPEC-01A §31)
# ---------------------------------------------------------------------------


@dataclass
class RuntimeVersions:
    """Tracks all versions for a runtime execution.

    Per SPEC-01A §31, these values shall remain constant
    throughout a Runtime Session.
    """

    graph_version: str = "0.0.0"
    knowledge_version: str = "0.0.0"
    policy_version: str = "0.0.0"
    provider_version: str = "0.0.0"
    interpretation_version: str = "0.0.0"
    reasoning_version: str = "1.0.0"
    router_version: str = "0.0.0"

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for serialization."""
        return {
            "graph_version": self.graph_version,
            "knowledge_version": self.knowledge_version,
            "policy_version": self.policy_version,
            "provider_version": self.provider_version,
            "interpretation_version": self.interpretation_version,
            "reasoning_version": self.reasoning_version,
            "router_version": self.router_version,
        }


# ---------------------------------------------------------------------------
# Version Tracker
# ---------------------------------------------------------------------------


class VersionTracker:
    """Tracks and records versions for runtime executions.

    Per SPEC-01A RP-06: every execution shall record versions.
    Per SPEC-01A §31: versions remain constant throughout a session.
    """

    def __init__(self) -> None:
        self._versions = RuntimeVersions()

    def get_versions(self) -> RuntimeVersions:
        """Get current version snapshot."""
        return self._versions

    def update_graph_version(self, version: str) -> None:
        """Update graph version (e.g. after graph mutation)."""
        self._versions.graph_version = version

    def update_knowledge_version(self, version: str) -> None:
        """Update knowledge version (e.g. after book import)."""
        self._versions.knowledge_version = version

    def update_policy_version(self, version: str) -> None:
        """Update policy version."""
        self._versions.policy_version = version

    def update_provider_version(self, version: str) -> None:
        """Update provider version."""
        self._versions.provider_version = version

    def update_interpretation_version(self, version: str) -> None:
        """Update interpretation version."""
        self._versions.interpretation_version = version

    def update_reasoning_version(self, version: str) -> None:
        """Update reasoning version."""
        self._versions.reasoning_version = version

    def update_router_version(self, version: str) -> None:
        """Update router version."""
        self._versions.router_version = version

    def get_engine_version(self, engine_name: str) -> str:
        """Get version for a specific engine."""
        return ENGINE_VERSIONS.get(engine_name, "0.0.0")

    def record_execution(self, execution_id: str, versions: RuntimeVersions) -> dict[str, Any]:
        """Record versions for an execution (for audit trail)."""
        return {
            "execution_id": execution_id,
            "versions": versions.to_dict(),
            "engine_versions": dict(ENGINE_VERSIONS),
        }
