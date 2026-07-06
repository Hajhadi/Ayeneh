"""ACT-01 Execution Monitoring Engine.

7-phase pipeline:
    1. ExecutionPlan — load and validate execution plan
    2. ActionInitialization — initialize execution tracking
    3. ProgressObservation — observe and record progress
    4. DeviationDetection — detect deviations from plan
    5. ResourceMonitoring — monitor resource consumption
    6. ExecutionStateUpdate — update execution state
    7. BehavioralFeedback — generate behavioral feedback
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.act.execution_monitoring.types import (
    DEVIATION_SEVERITY_LEVELS,
    EXECUTION_STATES,
    RESOURCE_CATEGORIES,
    VALID_STATE_TRANSITIONS,
    BehavioralFeedback,
    DeviationRecord,
    ExecutionObject,
    ExecutionProgress,
    ExecutionResult,
    ExecutionSnapshot,
    ResourceConsumption,
)

logger = structlog.get_logger(__name__)


class ExecutionMonitoringEngine:
    """Execution monitoring engine (ACT-01).

    Pipeline:
        1. ExecutionPlan — load and validate execution plan
        2. ActionInitialization — initialize execution tracking
        3. ProgressObservation — observe and record progress
        4. DeviationDetection — detect deviations from plan
        5. ResourceMonitoring — monitor resource consumption
        6. ExecutionStateUpdate — update execution state
        7. BehavioralFeedback — generate behavioral feedback
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._executions: dict[str, ExecutionObject] = {}

    def process(
        self,
        execution_request: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Run the full ACT-01 pipeline.

        Parameters
        ----------
        execution_request:
            Dict with ``'execution_id'``, ``'associated_plan'``,
            ``'associated_goal'``, and optional fields.
        context:
            Optional context dict with progress, resources, deviations.
        """
        ctx = context or {}

        logger.info(
            'act.execution_monitoring.pipeline_started',
            execution_id=execution_request.get('execution_id', ''),
        )

        # Phase 1: ExecutionPlan
        plan_validation = self._phase_execution_plan(execution_request, ctx)

        # Phase 2: ActionInitialization
        exec_obj = self._phase_action_initialization(execution_request, ctx)

        # Phase 3: ProgressObservation
        progress = self._phase_progress_observation(exec_obj, ctx)

        # Phase 4: DeviationDetection
        deviations = self._phase_deviation_detection(exec_obj, ctx)

        # Phase 5: ResourceMonitoring
        resources = self._phase_resource_monitoring(exec_obj, ctx)

        # Phase 6: ExecutionStateUpdate
        state_update = self._phase_execution_state_update(
            exec_obj, progress, deviations, ctx,
        )

        # Re-read the updated execution object
        exec_obj = self._executions[exec_obj.execution_id]

        # Phase 7: BehavioralFeedback
        feedback = self._phase_behavioral_feedback(
            exec_obj, deviations, resources, ctx,
        )

        phases = (
            'ExecutionPlan',
            'ActionInitialization',
            'ProgressObservation',
            'DeviationDetection',
            'ResourceMonitoring',
            'ExecutionStateUpdate',
            'BehavioralFeedback',
        )

        result = ExecutionResult(
            execution=exec_obj,
            state_transition=state_update,
            deviations_detected=deviations,
            resource_report=resources,
            progress_snapshots=(progress,),
            feedback=feedback,
            pipeline_phases_completed=phases,
        )

        logger.info(
            'act.execution_monitoring.pipeline_completed',
            execution_id=exec_obj.execution_id,
            state=exec_obj.current_state,
            progress=exec_obj.observed_progress,
            deviations=len(deviations),
        )

        return result

    # -------------------------------------------------------------------
    # Phase 1: ExecutionPlan
    # -------------------------------------------------------------------

    def _phase_execution_plan(
        self,
        request: dict[str, Any],
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Load and validate the execution plan."""
        plan_id = request.get('associated_plan', '')
        goal_id = request.get('associated_goal', '')
        execution_id = request.get('execution_id', '')

        validation = {
            'plan_id': plan_id,
            'goal_id': goal_id,
            'execution_id': execution_id,
            'valid': bool(execution_id),
            'plan_loaded': bool(plan_id),
            'goal_linked': bool(goal_id),
        }

        logger.debug(
            'act.execution_monitoring.phase_execution_plan',
            execution_id=execution_id,
            valid=validation['valid'],
        )
        return validation

    # -------------------------------------------------------------------
    # Phase 2: ActionInitialization
    # -------------------------------------------------------------------

    def _phase_action_initialization(
        self,
        request: dict[str, Any],
        ctx: dict[str, Any],
    ) -> ExecutionObject:
        """Initialize execution tracking object."""
        execution_id = request.get(
            'execution_id', str(uuid.uuid4()),
        )

        start_str = request.get('start_time', '')
        if start_str:
            start_time = datetime.fromisoformat(start_str)
        else:
            start_time = ctx.get('start_time', datetime.now(UTC))

        completion_str = request.get('expected_completion', '')
        if completion_str:
            expected_completion = datetime.fromisoformat(completion_str)
        else:
            expected_completion = ctx.get(
                'expected_completion', datetime.now(UTC),
            )

        state = request.get('current_state', 'prepared')
        if state not in EXECUTION_STATES:
            state = 'prepared'

        exec_obj = ExecutionObject(
            execution_id=execution_id,
            associated_plan=request.get('associated_plan', ''),
            associated_goal=request.get('associated_goal', ''),
            current_state=state,
            start_time=start_time,
            expected_completion=expected_completion,
            observed_progress=ctx.get('observed_progress', 0.0),
            consumed_resources=dict(ctx.get('consumed_resources', {})),
            detected_deviations=tuple(
                ctx.get('detected_deviations', ()),
            ),
            execution_confidence=ctx.get('execution_confidence', 0.0),
            risk_level=ctx.get('risk_level', 0.0),
            explainability_metadata=dict(
                ctx.get('explainability_metadata', {}),
            ),
        )

        self._executions[execution_id] = exec_obj

        logger.debug(
            'act.execution_monitoring.phase_action_initialization',
            execution_id=execution_id,
            state=state,
        )
        return exec_obj

    # -------------------------------------------------------------------
    # Phase 3: ProgressObservation
    # -------------------------------------------------------------------

    def _phase_progress_observation(
        self,
        exec_obj: ExecutionObject,
        ctx: dict[str, Any],
    ) -> ExecutionProgress:
        """Observe and record current progress."""
        progress_ratio = ctx.get('progress_ratio', exec_obj.observed_progress)
        milestones_achieved = tuple(
            ctx.get('milestones_achieved', ()),
        )
        milestones_pending = tuple(
            ctx.get('milestones_pending', ()),
        )
        quality_score = ctx.get('quality_score', 0.0)
        velocity = ctx.get('velocity', 0.0)

        progress = ExecutionProgress(
            progress_id=str(uuid.uuid4()),
            completion_ratio=progress_ratio,
            milestones_achieved=milestones_achieved,
            milestones_pending=milestones_pending,
            quality_score=quality_score,
            velocity=velocity,
        )

        logger.debug(
            'act.execution_monitoring.phase_progress_observation',
            execution_id=exec_obj.execution_id,
            completion_ratio=progress_ratio,
        )
        return progress

    # -------------------------------------------------------------------
    # Phase 4: DeviationDetection
    # -------------------------------------------------------------------

    def _phase_deviation_detection(
        self,
        exec_obj: ExecutionObject,
        ctx: dict[str, Any],
    ) -> tuple[DeviationRecord, ...]:
        """Detect deviations from the expected execution path."""
        raw_deviations = ctx.get('new_deviations', [])
        deviations: list[DeviationRecord] = []

        for raw in raw_deviations:
            severity = raw.get('severity', 'minor')
            if severity not in DEVIATION_SEVERITY_LEVELS:
                severity = 'minor'

            deviation = DeviationRecord(
                deviation_id=raw.get(
                    'deviation_id', str(uuid.uuid4()),
                ),
                deviation_type=raw.get('deviation_type', ''),
                severity=severity,
                description=raw.get('description', ''),
                expected_value=raw.get('expected_value'),
                observed_value=raw.get('observed_value'),
                metadata=dict(raw.get('metadata', {})),
            )
            deviations.append(deviation)

        for existing in exec_obj.detected_deviations:
            deviation = DeviationRecord(
                deviation_id=existing.get('deviation_id', ''),
                deviation_type=existing.get('deviation_type', ''),
                severity=existing.get('severity', 'minor'),
                description=existing.get('description', ''),
                expected_value=existing.get('expected_value'),
                observed_value=existing.get('observed_value'),
                metadata=dict(existing.get('metadata', {})),
            )
            deviations.append(deviation)

        result = tuple(deviations)

        logger.debug(
            'act.execution_monitoring.phase_deviation_detection',
            execution_id=exec_obj.execution_id,
            deviations_found=len(result),
        )
        return result

    # -------------------------------------------------------------------
    # Phase 5: ResourceMonitoring
    # -------------------------------------------------------------------

    def _phase_resource_monitoring(
        self,
        exec_obj: ExecutionObject,
        ctx: dict[str, Any],
    ) -> tuple[ResourceConsumption, ...]:
        """Monitor resource consumption."""
        resources: list[ResourceConsumption] = []
        consumed = ctx.get('consumed_resources', exec_obj.consumed_resources)
        allocations = ctx.get('resource_allocations', {})

        for category in RESOURCE_CATEGORIES:
            consumed_val = consumed.get(category, 0.0)
            allocated_val = allocations.get(category, 0.0)
            remaining = max(0.0, allocated_val - consumed_val)
            efficiency = (
                consumed_val / allocated_val
                if allocated_val > 0
                else 0.0
            )

            resources.append(
                ResourceConsumption(
                    resource_type=category,
                    allocated=allocated_val,
                    consumed=consumed_val,
                    remaining=remaining,
                    efficiency=min(efficiency, 1.0),
                ),
            )

        logger.debug(
            'act.execution_monitoring.phase_resource_monitoring',
            execution_id=exec_obj.execution_id,
            categories=len(resources),
        )
        return tuple(resources)

    # -------------------------------------------------------------------
    # Phase 6: ExecutionStateUpdate
    # -------------------------------------------------------------------

    def _phase_execution_state_update(
        self,
        exec_obj: ExecutionObject,
        progress: ExecutionProgress,
        deviations: tuple[DeviationRecord, ...],
        ctx: dict[str, Any],
    ) -> str:
        """Update execution state based on observations."""
        current_state = exec_obj.current_state
        requested_state = ctx.get('target_state', '')

        if requested_state and requested_state in EXECUTION_STATES:
            allowed = VALID_STATE_TRANSITIONS.get(current_state, [])
            if requested_state in allowed:
                old_state = current_state
                current_state = requested_state
                logger.info(
                    'act.execution_monitoring.state_transition',
                    execution_id=exec_obj.execution_id,
                    from_state=old_state,
                    to_state=current_state,
                )

        critical_deviations = sum(
            1 for d in deviations if d.severity in ('significant', 'critical')
        )
        if critical_deviations > 0 and current_state == 'running':
            old_state = current_state
            current_state = 'blocked'
            logger.warning(
                'act.execution_monitoring.auto_blocked_deviations',
                execution_id=exec_obj.execution_id,
                critical_count=critical_deviations,
            )

        snapshot = ExecutionSnapshot(
            snapshot_id=str(uuid.uuid4()),
            state=current_state,
            progress=progress.completion_ratio,
            confidence=exec_obj.execution_confidence,
            risk_level=exec_obj.risk_level,
        )

        new_history = list(exec_obj.version_history)
        new_history.append({
            'snapshot_id': snapshot.snapshot_id,
            'state': snapshot.state,
            'progress': snapshot.progress,
            'timestamp': snapshot.timestamp.isoformat(),
        })

        transition_str = f'{exec_obj.current_state}->{current_state}'

        self._executions[exec_obj.execution_id] = ExecutionObject(
            execution_id=exec_obj.execution_id,
            associated_plan=exec_obj.associated_plan,
            associated_goal=exec_obj.associated_goal,
            current_state=current_state,
            start_time=exec_obj.start_time,
            expected_completion=exec_obj.expected_completion,
            observed_progress=progress.completion_ratio,
            consumed_resources=dict(exec_obj.consumed_resources),
            detected_deviations=exec_obj.detected_deviations,
            execution_confidence=exec_obj.execution_confidence,
            risk_level=exec_obj.risk_level,
            version_history=tuple(new_history),
            creation_timestamp=exec_obj.creation_timestamp,
            explainability_metadata=dict(exec_obj.explainability_metadata),
        )

        logger.debug(
            'act.execution_monitoring.phase_execution_state_update',
            execution_id=exec_obj.execution_id,
            transition=transition_str,
        )
        return transition_str

    # -------------------------------------------------------------------
    # Phase 7: BehavioralFeedback
    # -------------------------------------------------------------------

    def _phase_behavioral_feedback(
        self,
        exec_obj: ExecutionObject,
        deviations: tuple[DeviationRecord, ...],
        resources: tuple[ResourceConsumption, ...],
        ctx: dict[str, Any],
    ) -> tuple[BehavioralFeedback, ...]:
        """Generate behavioral feedback based on observations."""
        feedbacks: list[BehavioralFeedback] = []

        critical_count = sum(
            1 for d in deviations if d.severity in ('significant', 'critical')
        )
        if critical_count > 0:
            feedbacks.append(
                BehavioralFeedback(
                    feedback_id=str(uuid.uuid4()),
                    feedback_type='warning',
                    message=(
                        f'{critical_count} critical deviation(s) detected. '
                        'Consider reviewing the execution plan.'
                    ),
                    severity='warning',
                    actionable=True,
                    suggested_action='review_plan',
                    confidence=0.8,
                ),
            )

        over_consumed: list[str] = []
        for r in resources:
            if r.allocated > 0 and r.consumed > r.allocated:
                over_consumed.append(r.resource_type)

        if over_consumed:
            feedbacks.append(
                BehavioralFeedback(
                    feedback_id=str(uuid.uuid4()),
                    feedback_type='resource_alert',
                    message=(
                        f'Resource over-consumption in: '
                        f'{", ".join(over_consumed)}.'
                    ),
                    severity='warning',
                    actionable=True,
                    suggested_action='reallocate_resources',
                    confidence=0.7,
                ),
            )

        progress = ctx.get('progress_ratio', exec_obj.observed_progress)
        if progress >= 1.0:
            feedbacks.append(
                BehavioralFeedback(
                    feedback_id=str(uuid.uuid4()),
                    feedback_type='celebration',
                    message='Execution has reached 100% completion.',
                    severity='info',
                    actionable=True,
                    suggested_action='archive_execution',
                    confidence=0.95,
                ),
            )

        if exec_obj.current_state == 'blocked':
            feedbacks.append(
                BehavioralFeedback(
                    feedback_id=str(uuid.uuid4()),
                    feedback_type='suggestion',
                    message=(
                        'Execution is blocked. Consider recovery '
                        'strategies or plan revision.'
                    ),
                    severity='info',
                    actionable=True,
                    suggested_action='suggest_recovery',
                    confidence=0.6,
                ),
            )

        if not feedbacks:
            feedbacks.append(
                BehavioralFeedback(
                    feedback_id=str(uuid.uuid4()),
                    feedback_type='status',
                    message='Execution proceeding normally.',
                    severity='info',
                    actionable=False,
                    confidence=0.5,
                ),
            )

        result = tuple(feedbacks)

        logger.debug(
            'act.execution_monitoring.phase_behavioral_feedback',
            execution_id=exec_obj.execution_id,
            feedback_count=len(result),
        )
        return result

    # -------------------------------------------------------------------
    # Public helpers
    # -------------------------------------------------------------------

    def get_execution(
        self, execution_id: str,
    ) -> ExecutionObject | None:
        """Retrieve a tracked execution by ID."""
        return self._executions.get(execution_id)

    def list_executions(self) -> list[ExecutionObject]:
        """Return all tracked executions."""
        return list(self._executions.values())

    def validate_state_transition(
        self, from_state: str, to_state: str,
    ) -> bool:
        """Check whether a state transition is valid."""
        allowed = VALID_STATE_TRANSITIONS.get(from_state, [])
        return to_state in allowed
