"""MEM-10 Versioning engine.

Implements the pipeline: ExistingMemory → NewEvidence → DifferenceDetection
→ RevisionAnalysis → VersionCreation → RelationshipUpdate
→ KnowledgeGraphUpdate → HistoricalPreservation.
"""

from __future__ import annotations

import structlog
from datetime import UTC, datetime
from typing import Any

from ayeneh.memo.base import MemoryObject, make_version_record
from ayeneh.memo.versioning.types import (
    CognitiveSnapshot,
    DifferenceRecord,
    RevisionAnalysis,
    RevisionCategory,
    VersionChain,
    VersionComparison,
    VersioningPipelineStage,
    VersionObject,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Stage 1: Difference detection
# ---------------------------------------------------------------------------

def detect_differences(
    old_memory: MemoryObject,
    new_memory: MemoryObject,
) -> list[DifferenceRecord]:
    """Detect field-level differences between two memory versions."""
    diffs: list[DifferenceRecord] = []

    field_checks = [
        ('memory_type', old_memory.memory_type, new_memory.memory_type),
        ('confidence', old_memory.confidence, new_memory.confidence),
        ('importance_score', old_memory.importance_score, new_memory.importance_score),
        ('temporal_scope', old_memory.temporal_scope, new_memory.temporal_scope),
        ('lifecycle_status', old_memory.lifecycle_status, new_memory.lifecycle_status),
        ('supporting_evidence', old_memory.supporting_evidence, new_memory.supporting_evidence),
        ('associated_episodes', old_memory.associated_episodes, new_memory.associated_episodes),
        ('associated_projects', old_memory.associated_projects, new_memory.associated_projects),
        ('associated_people', old_memory.associated_people, new_memory.associated_people),
        ('associated_places', old_memory.associated_places, new_memory.associated_places),
        ('associated_conversations', old_memory.associated_conversations, new_memory.associated_conversations),
        ('associated_cognitive_objects', old_memory.associated_cognitive_objects, new_memory.associated_cognitive_objects),
    ]

    for field_name, old_val, new_val in field_checks:
        if old_val != new_val:
            # Compute significance for numeric fields
            significance = 0.5
            if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                significance = min(1.0, abs(new_val - old_val))
            diffs.append(
                DifferenceRecord(
                    field_name=field_name,
                    old_value=old_val,
                    new_value=new_val,
                    significance=significance,
                )
            )
    return diffs


# ---------------------------------------------------------------------------
# Stage 2: Revision analysis
# ---------------------------------------------------------------------------

def analyse_revision(
    memory_id: str,
    differences: list[DifferenceRecord],
) -> RevisionAnalysis:
    """Analyse detected differences and recommend a revision category."""
    if not differences:
        return RevisionAnalysis(
            memory_id=memory_id,
            should_create_version=False,
            rationale='No differences detected',
        )

    max_significance = max(d.significance for d in differences)
    confidence_delta = 0.0
    for d in differences:
        if d.field_name == 'confidence':
            old_c = d.old_value if isinstance(d.old_value, (int, float)) else 0.0
            new_c = d.new_value if isinstance(d.new_value, (int, float)) else 0.0
            confidence_delta = new_c - old_c

    # Determine revision category from field changes
    changed_fields = {d.field_name for d in differences}

    if 'confidence' in changed_fields and len(changed_fields) == 1:
        category = RevisionCategory.CONFIDENCE_UPDATE
    elif len(changed_fields) > 3:
        category = RevisionCategory.GENERALIZATION
    elif 'supporting_evidence' in changed_fields:
        category = RevisionCategory.EVIDENCE_UPDATE
    elif 'lifecycle_status' in changed_fields:
        category = RevisionCategory.REFINEMENT
    elif 'importance_score' in changed_fields:
        if confidence_delta > 0:
            category = RevisionCategory.EXPANSION
        else:
            category = RevisionCategory.REFINEMENT
    else:
        category = RevisionCategory.EXPANSION

    return RevisionAnalysis(
        memory_id=memory_id,
        differences=tuple(differences),
        recommended_revision=category,
        confidence_delta=confidence_delta,
        rationale=f'{len(differences)} differences in {changed_fields}',
        should_create_version=max_significance > 0.0,
    )


# ---------------------------------------------------------------------------
# Stage 3: Version creation
# ---------------------------------------------------------------------------

def create_version(
    parent_version: VersionObject | None,
    target_memory: str,
    analysis: RevisionAnalysis,
    current_memory: MemoryObject,
) -> VersionObject:
    """Create a new version record from a revision analysis."""
    parent_num = parent_version.version_number if parent_version else 0
    parent_id = parent_version.version_identifier if parent_version else ''

    conf_before = current_memory.confidence - analysis.confidence_delta
    conf_after = current_memory.confidence

    return VersionObject(
        version_identifier=f'ver_{target_memory}_v{parent_num + 1}',
        parent_version=parent_id,
        target_memory=target_memory,
        version_number=parent_num + 1,
        creation_time=datetime.now(UTC),
        revision_time=datetime.now(UTC),
        supporting_evidence=current_memory.supporting_evidence,
        revision_type=analysis.recommended_revision,
        reason_for_revision=analysis.rationale,
        confidence_before=max(0.0, min(1.0, conf_before)),
        confidence_after=conf_after,
        associated_episodes=current_memory.associated_episodes,
        associated_conversations=current_memory.associated_conversations,
    )


# ---------------------------------------------------------------------------
# Stage 4-5: Relationship & knowledge graph update (stub delegates)
# ---------------------------------------------------------------------------

def update_relationships(
    version: VersionObject,
    affected_relationships: tuple[str, ...] = (),
) -> VersionObject:
    """Update the version's affected relationships."""
    return VersionObject(
        version_identifier=version.version_identifier,
        parent_version=version.parent_version,
        target_memory=version.target_memory,
        version_number=version.version_number,
        creation_time=version.creation_time,
        revision_time=version.revision_time,
        supporting_evidence=version.supporting_evidence,
        revision_type=version.revision_type,
        reason_for_revision=version.reason_for_revision,
        confidence_before=version.confidence_before,
        confidence_after=version.confidence_after,
        affected_relationships=affected_relationships,
        associated_episodes=version.associated_episodes,
        associated_conversations=version.associated_conversations,
        explainability_metadata=version.explainability_metadata,
    )


# ---------------------------------------------------------------------------
# Stage 6: Historical preservation
# ---------------------------------------------------------------------------

def build_version_record(version: VersionObject) -> dict[str, Any]:
    """Convert a VersionObject into a version_history record dict."""
    return make_version_record(
        version_number=version.version_number,
        changed_fields={
            'revision_type': version.revision_type.value,
            'confidence_before': version.confidence_before,
            'confidence_after': version.confidence_after,
            'reason': version.reason_for_revision,
        },
        change_reason=version.reason_for_revision,
        timestamp=version.revision_time,
    )


# ---------------------------------------------------------------------------
# Full pipeline orchestrator
# ---------------------------------------------------------------------------

class VersioningEngine:
    """Orchestrates the full MEM-10 versioning pipeline."""

    def __init__(self) -> None:
        self._chains: dict[str, VersionChain] = {}

    def get_chain(self, memory_id: str) -> VersionChain:
        return self._chains.get(memory_id, VersionChain(memory_id=memory_id))

    def process_update(
        self,
        old_memory: MemoryObject,
        new_memory: MemoryObject,
    ) -> VersionObject | None:
        """Process a memory update through the full versioning pipeline."""
        logger.info('versioning_pipeline.start', memory_id=new_memory.identifier)

        # 1. Difference detection
        diffs = detect_differences(old_memory, new_memory)
        if not diffs:
            logger.info('versioning_pipeline.no_diff', memory_id=new_memory.identifier)
            return None

        # 2. Revision analysis
        analysis = analyse_revision(new_memory.identifier, diffs)
        if not analysis.should_create_version:
            return None

        # 3. Version creation
        chain = self._chains.get(new_memory.identifier)
        parent = chain.latest if chain else None
        version = create_version(parent, new_memory.identifier, analysis, new_memory)

        # 4-5. Relationship update (placeholder)
        version = update_relationships(version)

        # 6. Historical preservation
        record = build_version_record(version)

        # Update chain
        versions = list(chain.versions) if chain else []
        versions.append(version)
        self._chains[new_memory.identifier] = VersionChain(
            memory_id=new_memory.identifier,
            versions=tuple(versions),
            current_version_number=version.version_number,
        )

        logger.info(
            'versioning_pipeline.complete',
            memory_id=new_memory.identifier,
            new_version=version.version_number,
            revision_type=version.revision_type.value,
        )
        return version

    def compare_versions(
        self,
        memory_id: str,
        version_a_num: int,
        version_b_num: int,
    ) -> VersionComparison:
        """Compare two versions of a memory."""
        chain = self._chains.get(memory_id)
        if chain is None:
            return VersionComparison(summary='No version history found')

        va: VersionObject | None = None
        vb: VersionObject | None = None
        for v in chain.versions:
            if v.version_number == version_a_num:
                va = v
            if v.version_number == version_b_num:
                vb = v

        diffs: list[DifferenceRecord] = []
        if va and vb:
            if va.confidence_before != vb.confidence_before:
                diffs.append(
                    DifferenceRecord(
                        field_name='confidence_before',
                        old_value=va.confidence_before,
                        new_value=vb.confidence_before,
                    )
                )
            if va.revision_type != vb.revision_type:
                diffs.append(
                    DifferenceRecord(
                        field_name='revision_type',
                        old_value=va.revision_type.value,
                        new_value=vb.revision_type.value,
                    )
                )

        return VersionComparison(
            version_a=va,
            version_b=vb,
            differences=tuple(diffs),
            summary=f'Compared v{version_a_num} and v{version_b_num}',
        )

    def create_snapshot(
        self,
        active_goals: tuple[str, ...] = (),
        active_projects: tuple[str, ...] = (),
        identity_state: dict[str, Any] | None = None,
        belief_state: dict[str, Any] | None = None,
    ) -> CognitiveSnapshot:
        """Create a cognitive snapshot of all current version states."""
        memory_versions: dict[str, int] = {}
        for mid, chain in self._chains.items():
            memory_versions[mid] = chain.current_version_number

        max_graph_ver = max((chain.current_version_number for chain in self._chains.values()), default=0)

        return CognitiveSnapshot(
            snapshot_id=f'snap_{int(datetime.now(UTC).timestamp())}',
            memory_versions=memory_versions,
            knowledge_graph_version=max_graph_ver,
            active_goals=active_goals,
            active_projects=active_projects,
            identity_state=identity_state or {},
            belief_state=belief_state or {},
        )
