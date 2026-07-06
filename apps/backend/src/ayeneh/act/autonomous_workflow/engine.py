"""ACT-05 Autonomous Workflow Engine.

7-phase pipeline:
    1. GoalGraph — build and validate goal graph
    2. StrategySelection — select appropriate strategies
    3. Planning — create execution plan
    4. Execution — execute planned steps
    5. Monitoring — monitor execution progress
    6. Feedback — collect execution feedback
    7. Adaptation — adapt workflow based on feedback
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from ayeneh.act.autonomous_workflow.types import (
    PHASE_VALID_TRANSITIONS,
    WORKFLOW_PHASES,
    WORKFLOW_STATUSES,
    AdaptationRecord,
    ExecutionRecord,
    GoalNode,
    MonitoringCheckpoint,
    PlanningStep,
    StrategySelection,
    WorkflowObject,
    WorkflowResult,
)

logger = structlog.get_logger(__name__)


class AutonomousWorkflowEngine:
    """Autonomous workflow engine (ACT-05).

    Pipeline:
        1. GoalGraph — build and validate goal graph
        2. StrategySelection — select appropriate strategies
        3. Planning — create execution plan
        4. Execution — execute planned steps
        5. Monitoring — monitor execution progress
        6. Feedback — collect execution feedback
        7. Adaptation — adapt workflow based on feedback
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._workflows: dict[str, WorkflowObject] = {}

    def process(
        self,
        workflow_request: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Run the full ACT-05 pipeline.

        Parameters
        ----------
        workflow_request:
            List of goal/plan dicts defining the workflow.
        context:
            Optional context dict with additional configuration.
        """
        ctx = context or {}

        logger.info(
            'act.autonomous_workflow.pipeline_started',
            goals_count=len(workflow_request),
        )

        # Phase 1: GoalGraph
        goal_graph = self._phase_goal_graph(workflow_request, ctx)

        # Phase 2: StrategySelection
        strategies = self._phase_strategy_selection(goal_graph, ctx)

        # Phase 3: Planning
        planning_steps = self._phase_planning(goal_graph, strategies, ctx)

        # Phase 4: Execution
        execution_records = self._phase_execution(planning_steps, ctx)

        # Phase 5: Monitoring
        checkpoints = self._phase_monitoring(execution_records, ctx)

        # Phase 6: Feedback — implicit from monitoring
        # Feedback is gathered during monitoring; no separate objects needed.

        # Phase 7: Adaptation
        adaptations = self._phase_adaptation(checkpoints, ctx)

        # Build workflow object
        workflow = self._build_workflow_object(
            goal_graph, planning_steps, execution_records, adaptations, ctx,
        )

        phases = (
            'GoalGraph',
            'StrategySelection',
            'Planning',
            'Execution',
            'Monitoring',
            'Feedback',
            'Adaptation',
        )

        result = WorkflowResult(
            workflow=workflow,
            goal_graph=goal_graph,
            strategy_selections=strategies,
            planning_steps=planning_steps,
            execution_records=execution_records,
            monitoring_checkpoints=checkpoints,
            adaptations=adaptations,
            pipeline_phases_completed=phases,
        )

        logger.info(
            'act.autonomous_workflow.pipeline_completed',
            workflow_id=workflow.workflow_id,
            phase=workflow.current_phase,
            progress=workflow.progress,
        )

        return result

    # -------------------------------------------------------------------
    # Phase 1: GoalGraph
    # -------------------------------------------------------------------

    def _phase_goal_graph(
        self,
        request: list[dict[str, Any]],
        ctx: dict[str, Any],
    ) -> tuple[GoalNode, ...]:
        """Build and validate the goal graph."""
        nodes: list[GoalNode] = []

        for item in request:
            node = GoalNode(
                node_id=item.get('node_id', str(uuid.uuid4())),
                goal_description=item.get('description', item.get('title', '')),
                priority=item.get('priority', 0.5),
                status=item.get('status', 'pending'),
                dependencies=tuple(item.get('dependencies', ())),
                metadata=dict(item.get('metadata', {})),
            )
            nodes.append(node)

        if not nodes and ctx.get('default_goal'):
            nodes.append(
                GoalNode(
                    node_id=str(uuid.uuid4()),
                    goal_description=ctx['default_goal'],
                    priority=0.5,
                ),
            )

        logger.debug(
            'act.autonomous_workflow.phase_goal_graph',
            nodes_count=len(nodes),
        )
        return tuple(nodes)

    # -------------------------------------------------------------------
    # Phase 2: StrategySelection
    # -------------------------------------------------------------------

    def _phase_strategy_selection(
        self,
        goal_graph: tuple[GoalNode, ...],
        ctx: dict[str, Any],
    ) -> tuple[StrategySelection, ...]:
        """Select appropriate strategies for each goal."""
        selections: list[StrategySelection] = []

        for node in goal_graph:
            strategy_name = self._select_strategy_for_goal(node, ctx)
            selection = StrategySelection(
                selection_id=str(uuid.uuid4()),
                strategy_name=strategy_name,
                strategy_type=node.metadata.get('strategy_type', 'adaptive'),
                confidence=node.priority,
                rationale=f'Selected for goal: {node.goal_description[:50]}',
                alternatives=tuple(
                    ctx.get('alternative_strategies', ['conservative', 'aggressive']),
                ),
            )
            selections.append(selection)

        # Include any raw strategy selections from context
        for raw in ctx.get('strategy_selections', []):
            selections.append(
                StrategySelection(
                    selection_id=raw.get('selection_id', str(uuid.uuid4())),
                    strategy_name=raw.get('strategy_name', ''),
                    strategy_type=raw.get('strategy_type', 'default'),
                    confidence=raw.get('confidence', 0.5),
                    rationale=raw.get('rationale', ''),
                    alternatives=tuple(raw.get('alternatives', ())),
                ),
            )

        logger.debug(
            'act.autonomous_workflow.phase_strategy_selection',
            selections_count=len(selections),
        )
        return tuple(selections)

    def _select_strategy_for_goal(
        self, node: GoalNode, ctx: dict[str, Any],
    ) -> str:
        """Select a strategy based on goal characteristics."""
        if node.priority >= 0.8:
            return 'aggressive'
        if node.priority >= 0.5:
            return 'balanced'
        return 'conservative'

    # -------------------------------------------------------------------
    # Phase 3: Planning
    # -------------------------------------------------------------------

    def _phase_planning(
        self,
        goal_graph: tuple[GoalNode, ...],
        strategies: tuple[StrategySelection, ...],
        ctx: dict[str, Any],
    ) -> tuple[PlanningStep, ...]:
        """Create execution plan from goals and strategies."""
        steps: list[PlanningStep] = []
        order = 0

        for i, node in enumerate(goal_graph):
            strategy = strategies[i] if i < len(strategies) else None
            step = PlanningStep(
                step_id=str(uuid.uuid4()),
                description=(
                    f'Execute: {node.goal_description}'
                    f' (strategy: {strategy.strategy_name if strategy else "default"})'
                ),
                order=order,
                status='pending',
                estimated_duration_ms=node.metadata.get('estimated_duration_ms', 0.0),
                dependencies=node.dependencies,
            )
            steps.append(step)
            order += 1

        # Include any raw planning steps from context
        for raw in ctx.get('planning_steps', []):
            steps.append(
                PlanningStep(
                    step_id=raw.get('step_id', str(uuid.uuid4())),
                    description=raw.get('description', ''),
                    order=raw.get('order', order),
                    status=raw.get('status', 'pending'),
                    estimated_duration_ms=raw.get('estimated_duration_ms', 0.0),
                    dependencies=tuple(raw.get('dependencies', ())),
                ),
            )
            order += 1

        logger.debug(
            'act.autonomous_workflow.phase_planning',
            steps_count=len(steps),
        )
        return tuple(steps)

    # -------------------------------------------------------------------
    # Phase 4: Execution
    # -------------------------------------------------------------------

    def _phase_execution(
        self,
        planning_steps: tuple[PlanningStep, ...],
        ctx: dict[str, Any],
    ) -> tuple[ExecutionRecord, ...]:
        """Execute planned steps."""
        records: list[ExecutionRecord] = []

        for step in planning_steps:
            status = 'completed' if not step.dependencies else 'pending'
            now = datetime.now(UTC)

            record = ExecutionRecord(
                record_id=str(uuid.uuid4()),
                step_id=step.step_id,
                started_at=now,
                completed_at=now,
                status=status,
                output=f'Step {step.order}: {step.description[:50]}',
                confidence=0.7 if status == 'completed' else 0.0,
            )
            records.append(record)

        # Include any raw execution records from context
        for raw in ctx.get('execution_records', []):
            started = datetime.fromisoformat(raw['started_at']) if raw.get('started_at') else datetime.now(UTC)
            completed = datetime.fromisoformat(raw['completed_at']) if raw.get('completed_at') else datetime.now(UTC)
            records.append(
                ExecutionRecord(
                    record_id=raw.get('record_id', str(uuid.uuid4())),
                    step_id=raw.get('step_id', ''),
                    started_at=started,
                    completed_at=completed,
                    status=raw.get('status', 'completed'),
                    output=raw.get('output', ''),
                    error=raw.get('error', ''),
                    confidence=raw.get('confidence', 0.5),
                ),
            )

        logger.debug(
            'act.autonomous_workflow.phase_execution',
            records_count=len(records),
        )
        return tuple(records)

    # -------------------------------------------------------------------
    # Phase 5: Monitoring
    # -------------------------------------------------------------------

    def _phase_monitoring(
        self,
        execution_records: tuple[ExecutionRecord, ...],
        ctx: dict[str, Any],
    ) -> tuple[MonitoringCheckpoint, ...]:
        """Monitor execution progress."""
        checkpoints: list[MonitoringCheckpoint] = []

        total = len(execution_records)
        completed = sum(1 for r in execution_records if r.status == 'completed')
        failed = sum(1 for r in execution_records if r.status == 'failed')
        progress = completed / total if total > 0 else 0.0

        health = 'healthy'
        alerts: list[str] = []
        if failed > 0:
            health = 'degraded'
            alerts.append(f'{failed} step(s) failed')
        if progress < 0.5 and total > 0:
            alerts.append('Progress below 50%')

        checkpoint = MonitoringCheckpoint(
            checkpoint_id=str(uuid.uuid4()),
            phase='execution',
            progress=progress,
            health_status=health,
            alerts=tuple(alerts),
            metrics={
                'total_steps': float(total),
                'completed_steps': float(completed),
                'failed_steps': float(failed),
                'success_rate': completed / total if total > 0 else 0.0,
            },
        )
        checkpoints.append(checkpoint)

        # Include any raw checkpoints from context
        for raw in ctx.get('monitoring_checkpoints', []):
            checkpoints.append(
                MonitoringCheckpoint(
                    checkpoint_id=raw.get('checkpoint_id', str(uuid.uuid4())),
                    phase=raw.get('phase', ''),
                    progress=raw.get('progress', 0.0),
                    health_status=raw.get('health_status', 'healthy'),
                    alerts=tuple(raw.get('alerts', ())),
                    metrics=dict(raw.get('metrics', {})),
                ),
            )

        logger.debug(
            'act.autonomous_workflow.phase_monitoring',
            checkpoints_count=len(checkpoints),
            progress=progress,
        )
        return tuple(checkpoints)

    # -------------------------------------------------------------------
    # Phase 7: Adaptation
    # -------------------------------------------------------------------

    def _phase_adaptation(
        self,
        checkpoints: tuple[MonitoringCheckpoint, ...],
        ctx: dict[str, Any],
    ) -> tuple[AdaptationRecord, ...]:
        """Adapt workflow based on monitoring feedback."""
        adaptations: list[AdaptationRecord] = []

        for checkpoint in checkpoints:
            if checkpoint.health_status == 'degraded':
                adaptations.append(
                    AdaptationRecord(
                        adaptation_id=str(uuid.uuid4()),
                        trigger='degraded_health',
                        previous_state='executing',
                        new_state='recovery_planning',
                        rationale=f'Health degraded: {", ".join(checkpoint.alerts)}',
                        confidence=0.7,
                    ),
                )
            elif checkpoint.progress >= 1.0:
                adaptations.append(
                    AdaptationRecord(
                        adaptation_id=str(uuid.uuid4()),
                        trigger='completion',
                        previous_state='executing',
                        new_state='completed',
                        rationale='All steps completed successfully',
                        confidence=0.95,
                    ),
                )
            elif checkpoint.progress < 0.3:
                adaptations.append(
                    AdaptationRecord(
                        adaptation_id=str(uuid.uuid4()),
                        trigger='slow_progress',
                        previous_state='executing',
                        new_state='reassessing',
                        rationale=f'Progress at {checkpoint.progress:.0%} — may need replanning',
                        confidence=0.5,
                    ),
                )

        # Include any raw adaptations from context
        for raw in ctx.get('adaptations', []):
            adaptations.append(
                AdaptationRecord(
                    adaptation_id=raw.get('adaptation_id', str(uuid.uuid4())),
                    trigger=raw.get('trigger', ''),
                    previous_state=raw.get('previous_state', ''),
                    new_state=raw.get('new_state', ''),
                    rationale=raw.get('rationale', ''),
                    confidence=raw.get('confidence', 0.5),
                ),
            )

        logger.debug(
            'act.autonomous_workflow.phase_adaptation',
            adaptations_count=len(adaptations),
        )
        return tuple(adaptations)

    # -------------------------------------------------------------------
    # Helper: build WorkflowObject
    # -------------------------------------------------------------------

    def _build_workflow_object(
        self,
        goal_graph: tuple[GoalNode, ...],
        planning_steps: tuple[PlanningStep, ...],
        execution_records: tuple[ExecutionRecord, ...],
        adaptations: tuple[AdaptationRecord, ...],
        ctx: dict[str, Any],
    ) -> WorkflowObject:
        """Build the core WorkflowObject."""
        workflow_id = ctx.get('workflow_id', str(uuid.uuid4()))

        current_phase = 'execution'
        if adaptations:
            last = adaptations[-1]
            if last.new_state == 'completed':
                current_phase = 'completion'
            elif last.new_state == 'recovery_planning':
                current_phase = 'adaptation'

        total = len(execution_records)
        completed = sum(1 for r in execution_records if r.status == 'completed')
        progress = completed / total if total > 0 else 0.0

        exec_history = tuple(
            {
                'record_id': r.record_id,
                'step_id': r.step_id,
                'status': r.status,
                'confidence': r.confidence,
            }
            for r in execution_records
        )

        goals = tuple(n.node_id for n in goal_graph)
        plans = tuple(s.step_id for s in planning_steps)

        avg_confidence = 0.0
        if execution_records:
            avg_confidence = sum(r.confidence for r in execution_records) / len(execution_records)

        return WorkflowObject(
            workflow_id=workflow_id,
            associated_goals=goals,
            associated_plans=plans,
            current_phase=current_phase,
            execution_history=exec_history,
            dependencies=tuple(ctx.get('dependencies', ())),
            responsible_modules=tuple(ctx.get('responsible_modules', ())),
            current_status='active' if current_phase != 'completion' else 'completed',
            priority=ctx.get('priority', 0.5),
            progress=progress,
            confidence=avg_confidence,
            explainability_metadata={
                'goal_count': len(goal_graph),
                'steps_count': len(planning_steps),
                'execution_count': len(execution_records),
                'adaptations_count': len(adaptations),
            },
        )

    # -------------------------------------------------------------------
    # Public helpers
    # -------------------------------------------------------------------

    def get_workflow(self, workflow_id: str) -> WorkflowObject | None:
        """Retrieve a tracked workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[WorkflowObject]:
        """Return all tracked workflows."""
        return list(self._workflows.values())
