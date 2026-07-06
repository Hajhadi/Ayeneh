"""INT-04 Unified Cognitive State — 7-phase pipeline engine."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog

from ayeneh.int.cognitive_state.types import (
    ArchitectureSyncRecord,
    ConflictRecord,
    CognitiveStateObject,
    CognitiveStateResult,
    DimensionStatus,
    ExplainabilityMetadata,
    STATE_DIMENSIONS,
    STATE_TRANSITIONS,
    StateTransition,
)

logger = structlog.get_logger(__name__)


class CognitiveStateEngine:
    """Maintains unified cognitive state through a 7-phase pipeline.

    Phases:
        1. StateCollection          — gather dimension data from all modules
        2. ConsistencyValidation    — validate cross-dimension consistency
        3. ConflictDetection        — detect conflicts between dimensions
        4. StateIntegration         — merge dimension states into unified view
        5. GlobalCognitiveState     — produce the global state object
        6. ArchitectureSynchronization — sync state across architecture layers
        7. StateDistribution        — distribute state to subscribed modules
    """

    def __init__(self) -> None:
        self._subscribers: list[str] = []
        self._state_history: list[CognitiveStateObject] = []

    def register_subscriber(self, module_id: str) -> None:
        if module_id not in self._subscribers:
            self._subscribers.append(module_id)

    def process(
        self,
        context: dict[str, Any] | None = None,
        session_id: str = '',
    ) -> CognitiveStateResult:
        start = time.monotonic()
        ctx = context or {}
        errors: list[str] = []
        phases: list[str] = []

        logger.info(
            "cognitive_state_pipeline_started",
            session_id=session_id,
        )

        # Phase 1: StateCollection
        dimensions = self._phase_state_collection(ctx, errors)
        phases.append('StateCollection')

        # Phase 2: ConsistencyValidation
        validated, valid_errors = self._phase_consistency_validation(dimensions, errors)
        errors.extend(valid_errors)
        phases.append('ConsistencyValidation')

        # Phase 3: ConflictDetection
        conflicts = self._phase_conflict_detection(validated, errors)
        phases.append('ConflictDetection')

        # Phase 4: StateIntegration
        integrated = self._phase_state_integration(validated, conflicts, errors)
        phases.append('StateIntegration')

        # Phase 5: GlobalCognitiveState
        state_id = str(uuid.uuid4())
        state_obj = self._phase_global_cognitive_state(
            state_id, ctx, integrated, conflicts, errors,
        )
        phases.append('GlobalCognitiveState')

        # Phase 6: ArchitectureSynchronization
        sync_records = self._phase_architecture_synchronization(
            state_obj, validated, errors,
        )
        phases.append('ArchitectureSynchronization')

        # Phase 7: StateDistribution
        self._phase_state_distribution(state_obj, errors)
        phases.append('StateDistribution')

        duration_ms = (time.monotonic() - start) * 1000

        # Compute global confidence
        if integrated:
            global_confidence = sum(d.confidence for d in integrated) / len(integrated)
        else:
            global_confidence = 0.0

        logger.info(
            "cognitive_state_pipeline_completed",
            state_id=state_id,
            dimensions=len(dimensions),
            conflicts=len(conflicts),
            confidence=global_confidence,
            duration_ms=duration_ms,
        )

        return CognitiveStateResult(
            state_id=state_id,
            state_object=state_obj,
            dimension_statuses=tuple(validated),
            transitions=(),
            conflicts=tuple(conflicts),
            sync_records=tuple(sync_records),
            global_confidence=global_confidence,
            duration_ms=duration_ms,
            errors=tuple(errors),
            pipeline_phases_completed=tuple(phases),
        )

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _phase_state_collection(
        self,
        ctx: dict[str, Any],
        errors: list[str],
    ) -> list[DimensionStatus]:
        """Phase 1: Gather dimension data from all modules."""
        try:
            dimensions: list[DimensionStatus] = []
            module_data = ctx.get('module_data', {})

            for dim in STATE_DIMENSIONS:
                data = module_data.get(dim, {})
                dimensions.append(DimensionStatus(
                    dimension=dim,
                    active=data.get('active', True),
                    confidence=data.get('confidence', 0.5),
                    contributing_modules=tuple(data.get('modules', [])),
                    metadata=data.get('metadata', {}),
                ))

            logger.debug("phase_state_collection_completed", count=len(dimensions))
            return dimensions
        except Exception as exc:
            errors.append(f"Phase 1 (StateCollection) error: {exc}")
            return [DimensionStatus(dimension=d) for d in STATE_DIMENSIONS]

    def _phase_consistency_validation(
        self,
        dimensions: list[DimensionStatus],
        errors: list[str],
    ) -> tuple[list[DimensionStatus], list[str]]:
        """Phase 2: Validate cross-dimension consistency."""
        validation_errors: list[str] = []
        try:
            validated: list[DimensionStatus] = []
            for dim in dimensions:
                # Check confidence bounds
                if dim.confidence < 0.0 or dim.confidence > 1.0:
                    validation_errors.append(
                        f"Dimension {dim.dimension}: confidence {dim.confidence} out of bounds"
                    )
                    continue
                validated.append(dim)

            if not validated:
                validated = dimensions  # fallback to original

            logger.debug("phase_consistency_validation_completed", validated=len(validated))
            return validated, validation_errors
        except Exception as exc:
            errors.append(f"Phase 2 (ConsistencyValidation) error: {exc}")
            return dimensions, validation_errors

    def _phase_conflict_detection(
        self,
        dimensions: list[DimensionStatus],
        errors: list[str],
    ) -> list[ConflictRecord]:
        """Phase 3: Detect conflicts between dimensions."""
        try:
            conflicts: list[ConflictRecord] = []

            # Check for low-confidence dimensions
            for dim in dimensions:
                if dim.confidence < 0.3 and dim.active:
                    conflicts.append(ConflictRecord(
                        conflict_id=str(uuid.uuid4()),
                        source_dimension=dim.dimension,
                        target_dimension='global',
                        conflict_type='inconsistency',
                        severity='medium',
                        description=f"Low confidence ({dim.confidence:.2f}) in active dimension {dim.dimension}",
                        resolution_strategy='recollect',
                    ))

            # Check for completely inactive dimensions
            inactive = [d for d in dimensions if not d.active]
            if len(inactive) > len(dimensions) * 0.5:
                conflicts.append(ConflictRecord(
                    conflict_id=str(uuid.uuid4()),
                    source_dimension='global',
                    target_dimension='global',
                    conflict_type='contradictory',
                    severity='high',
                    description=f"{len(inactive)}/{len(dimensions)} dimensions inactive",
                    resolution_strategy='reactivation',
                ))

            logger.debug("phase_conflict_detection_completed", conflicts=len(conflicts))
            return conflicts
        except Exception as exc:
            errors.append(f"Phase 3 (ConflictDetection) error: {exc}")
            return []

    def _phase_state_integration(
        self,
        dimensions: list[DimensionStatus],
        conflicts: list[ConflictRecord],
        errors: list[str],
    ) -> list[DimensionStatus]:
        """Phase 4: Merge dimension states into unified view."""
        try:
            # Adjust confidence based on conflicts
            conflict_dims = {c.source_dimension for c in conflicts}
            integrated: list[DimensionStatus] = []
            for dim in dimensions:
                if dim.dimension in conflict_dims:
                    adjusted_confidence = dim.confidence * 0.8
                else:
                    adjusted_confidence = dim.confidence
                integrated.append(DimensionStatus(
                    dimension=dim.dimension,
                    active=dim.active,
                    confidence=adjusted_confidence,
                    last_updated=dim.last_updated,
                    contributing_modules=dim.contributing_modules,
                    metadata=dim.metadata,
                ))

            logger.debug("phase_state_integration_completed", count=len(integrated))
            return integrated
        except Exception as exc:
            errors.append(f"Phase 4 (StateIntegration) error: {exc}")
            return dimensions

    def _phase_global_cognitive_state(
        self,
        state_id: str,
        ctx: dict[str, Any],
        dimensions: list[DimensionStatus],
        conflicts: list[ConflictRecord],
        errors: list[str],
    ) -> CognitiveStateObject:
        """Phase 5: Produce the global state object."""
        try:
            active_modules = ctx.get('active_modules', ())
            if isinstance(active_modules, list):
                active_modules = tuple(active_modules)

            active_goals = ctx.get('active_goals', ())
            if isinstance(active_goals, list):
                active_goals = tuple(active_goals)

            running_workflows = ctx.get('running_workflows', ())
            if isinstance(running_workflows, list):
                running_workflows = tuple(running_workflows)

            confidence_map = {d.dimension: d.confidence for d in dimensions}
            avg_confidence = (
                sum(d.confidence for d in dimensions) / len(dimensions)
                if dimensions else 0.0
            )

            consistency_status = 'consistent'
            if any(c.severity == 'critical' for c in conflicts):
                consistency_status = 'critical'
            elif any(c.severity == 'high' for c in conflicts):
                consistency_status = 'inconsistent'
            elif conflicts:
                consistency_status = 'minor_conflicts'

            explainability = ExplainabilityMetadata(
                reasoning_chain=(
                    f"Collected {len(dimensions)} dimension states",
                    f"Detected {len(conflicts)} conflicts",
                    f"Global confidence: {avg_confidence:.2f}",
                ),
                contributing_factors=tuple(
                    {'dimension': d.dimension, 'confidence': d.confidence}
                    for d in dimensions
                ),
                confidence_decomposition=confidence_map,
            )

            state_obj = CognitiveStateObject(
                state_id=state_id,
                active_modules=active_modules,
                active_goals=active_goals,
                running_workflows=running_workflows,
                resource_status={d.dimension: {'active': d.active, 'confidence': d.confidence} for d in dimensions},
                confidence_map=confidence_map,
                consistency_status=consistency_status,
                architecture_health=avg_confidence,
                revision_history=(),
                explainability_metadata={
                    'reasoning_chain': explainability.reasoning_chain,
                    'contributing_factors': explainability.contributing_factors,
                    'confidence_decomposition': explainability.confidence_decomposition,
                },
            )

            self._state_history.append(state_obj)
            logger.debug("phase_global_cognitive_state_completed", state_id=state_id)
            return state_obj
        except Exception as exc:
            errors.append(f"Phase 5 (GlobalCognitiveState) error: {exc}")
            return CognitiveStateObject(state_id=state_id, consistency_status='error')

    def _phase_architecture_synchronization(
        self,
        state_obj: CognitiveStateObject,
        dimensions: list[DimensionStatus],
        errors: list[str],
    ) -> list[ArchitectureSyncRecord]:
        """Phase 6: Sync state across architecture layers."""
        try:
            records: list[ArchitectureSyncRecord] = []
            active_dims = tuple(d.dimension for d in dimensions if d.active)

            records.append(ArchitectureSyncRecord(
                sync_id=str(uuid.uuid4()),
                synced_dimensions=active_dims,
                conflicts_resolved=0,
                health_before=state_obj.architecture_health,
                health_after=state_obj.architecture_health,
                details={'subscriber_count': len(self._subscribers)},
            ))

            logger.debug("phase_architecture_synchronization_completed", records=len(records))
            return records
        except Exception as exc:
            errors.append(f"Phase 6 (ArchitectureSynchronization) error: {exc}")
            return []

    def _phase_state_distribution(
        self,
        state_obj: CognitiveStateObject,
        errors: list[str],
    ) -> None:
        """Phase 7: Distribute state to subscribed modules."""
        try:
            for subscriber in self._subscribers:
                logger.debug(
                    "state_distributed",
                    subscriber=subscriber,
                    state_id=state_obj.state_id,
                )
            logger.debug(
                "phase_state_distribution_completed",
                subscribers=len(self._subscribers),
            )
        except Exception as exc:
            errors.append(f"Phase 7 (StateDistribution) error: {exc}")
