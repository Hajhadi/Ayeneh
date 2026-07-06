"""DEC-03 Planning Engine.

Planning engine implementing an 8-phase pipeline:
1. GoalGraph — load goal graph for context
2. ConstraintAnalysis — analyze planning constraints
3. DependencyResolution — resolve task dependencies
4. MilestoneConstruction — construct milestones
5. TaskDecomposition — decompose into tasks
6. ScheduleGeneration — generate schedule
7. RiskReview — review plan risks
8. ExecutionPlan — produce execution plan
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.dec.planning.types import (
    DEPENDENCY_TYPES,
    PLANNING_HORIZONS,
    TASK_STATUSES,
    PlanObject,
    PlanResult,
    PlanRiskAssessment,
    ScheduleSlot,
)

logger = structlog.get_logger(__name__)


class PlanningEngine:
    """Planning engine (DEC-03).

    Pipeline:
        1. GoalGraph — load goal graph for context
        2. ConstraintAnalysis — analyze planning constraints
        3. DependencyResolution — resolve task dependencies
        4. MilestoneConstruction — construct milestones
        5. TaskDecomposition — decompose into tasks
        6. ScheduleGeneration — generate schedule
        7. RiskReview — review plan risks
        8. ExecutionPlan — produce execution plan
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._plans: dict[str, PlanObject] = {}

    def process(
        self,
        goal: dict[str, Any],
        context: dict[str, Any] | None = None,
        existing_tasks: list[dict[str, Any]] | None = None,
    ) -> PlanResult:
        """Run the full DEC-03 pipeline.

        Parameters
        ----------
        goal:
            Goal dict with ``'goal_id'``, ``'description'``, ``'priority'``.
        context:
            Optional context dict with constraints, resources, horizon.
        existing_tasks:
            Optional list of task dicts to incorporate.
        """
        ctx = context or {}
        tasks_raw = existing_tasks or []

        logger.info(
            'dec.planning.pipeline_started',
            goal_id=goal.get('goal_id', ''),
            horizon=ctx.get('planning_horizon', 'daily'),
        )

        # Phase 1: GoalGraph
        goal_graph = self._phase_goal_graph(goal, ctx)

        # Phase 2: ConstraintAnalysis
        constraints = self._phase_constraint_analysis(ctx)

        # Phase 3: DependencyResolution
        dependencies = self._phase_dependency_resolution(tasks_raw)

        # Phase 4: MilestoneConstruction
        milestones = self._phase_milestone_construction(goal_graph, dependencies)

        # Phase 5: TaskDecomposition
        tasks = self._phase_task_decomposition(goal_graph, milestones, tasks_raw)

        # Phase 6: ScheduleGeneration
        schedule = self._phase_schedule_generation(tasks, dependencies, ctx)

        # Phase 7: RiskReview
        risks, critical_path = self._phase_risk_review(tasks, dependencies, constraints)

        # Phase 8: ExecutionPlan
        result = self._phase_execution_plan(
            goal, goal_graph, milestones, tasks, dependencies,
            constraints, schedule, risks, critical_path, ctx,
        )

        logger.info(
            'dec.planning.pipeline_completed',
            plan_id=result.plan.plan_id,
            task_count=len(tasks),
            milestone_count=len(milestones),
        )

        return result

    # ------------------------------------------------------------------
    # Phase 1: GoalGraph
    # ------------------------------------------------------------------

    def _phase_goal_graph(
        self,
        goal: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Load and structure the goal graph."""
        logger.debug('dec.planning.phase1_goal_graph')

        return {
            'goal_id': goal.get('goal_id', ''),
            'description': goal.get('description', ''),
            'priority': goal.get('priority', 0.5),
            'associated_values': goal.get('associated_values', []),
            'child_goals': goal.get('child_goals', []),
            'time_horizon': context.get('planning_horizon', 'daily'),
        }

    # ------------------------------------------------------------------
    # Phase 2: ConstraintAnalysis
    # ------------------------------------------------------------------

    def _phase_constraint_analysis(
        self,
        context: dict[str, Any],
    ) -> tuple[dict[str, Any], ...]:
        """Analyze planning constraints."""
        logger.debug('dec.planning.phase2_constraint_analysis')

        constraints: list[dict[str, Any]] = []

        for tc in context.get('time_constraints', []):
            constraints.append({
                'type': 'temporal',
                'description': tc,
                'severity': 0.6,
            })

        for rc in context.get('resource_constraints', []):
            constraints.append({
                'type': 'resource',
                'description': rc,
                'severity': 0.5,
            })

        for ec in context.get('external_constraints', []):
            constraints.append({
                'type': 'external',
                'description': ec,
                'severity': 0.7,
            })

        return tuple(constraints)

    # ------------------------------------------------------------------
    # Phase 3: DependencyResolution
    # ------------------------------------------------------------------

    def _phase_dependency_resolution(
        self,
        tasks_raw: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], ...]:
        """Resolve task dependencies."""
        logger.debug('dec.planning.phase3_dependency_resolution')

        dependencies: list[dict[str, Any]] = []
        for task in tasks_raw:
            for dep in task.get('dependencies', []):
                dependencies.append({
                    'dependency_id': str(uuid.uuid4()),
                    'source_task': dep if isinstance(dep, str) else dep.get('task_id', ''),
                    'target_task': task.get('task_id', ''),
                    'dependency_type': 'sequential',
                })

        # Add implicit sequential dependencies between tasks without deps
        task_ids = [t.get('task_id', '') for t in tasks_raw]
        for i in range(len(task_ids) - 1):
            has_dep = any(
                d.get('target_task') == task_ids[i + 1]
                for d in dependencies
            )
            if not has_dep and task_ids[i] and task_ids[i + 1]:
                dependencies.append({
                    'dependency_id': str(uuid.uuid4()),
                    'source_task': task_ids[i],
                    'target_task': task_ids[i + 1],
                    'dependency_type': 'sequential',
                })

        return tuple(dependencies)

    # ------------------------------------------------------------------
    # Phase 4: MilestoneConstruction
    # ------------------------------------------------------------------

    def _phase_milestone_construction(
        self,
        goal_graph: dict[str, Any],
        dependencies: tuple[dict[str, Any], ...],
    ) -> tuple[dict[str, Any], ...]:
        """Construct milestones from the goal graph."""
        logger.debug('dec.planning.phase4_milestone_construction')

        milestones: list[dict[str, Any]] = [
            {
                'milestone_id': str(uuid.uuid4()),
                'name': 'Initial assessment and planning',
                'description': 'Gather requirements and create initial plan',
                'target_progress': 0.1,
            },
            {
                'milestone_id': str(uuid.uuid4()),
                'name': 'Core implementation',
                'description': 'Execute the main tasks',
                'target_progress': 0.5,
            },
            {
                'milestone_id': str(uuid.uuid4()),
                'name': 'Review and adjustment',
                'description': 'Review progress and adjust plan',
                'target_progress': 0.8,
            },
            {
                'milestone_id': str(uuid.uuid4()),
                'name': 'Completion',
                'description': 'Finalize and complete the goal',
                'target_progress': 1.0,
            },
        ]

        return tuple(milestones)

    # ------------------------------------------------------------------
    # Phase 5: TaskDecomposition
    # ------------------------------------------------------------------

    def _phase_task_decomposition(
        self,
        goal_graph: dict[str, Any],
        milestones: tuple[dict[str, Any], ...],
        existing_tasks: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], ...]:
        """Decompose milestones into tasks."""
        logger.debug('dec.planning.phase5_task_decomposition')

        if existing_tasks:
            tasks: list[dict[str, Any]] = []
            for t in existing_tasks:
                tasks.append({
                    'task_id': t.get('task_id', str(uuid.uuid4())),
                    'name': t.get('name', t.get('description', '')),
                    'description': t.get('description', ''),
                    'status': t.get('status', 'pending'),
                    'estimated_hours': t.get('estimated_hours', 1.0),
                    'priority': t.get('priority', 0.5),
                    'milestone_id': t.get('milestone_id', ''),
                    'dependencies': t.get('dependencies', []),
                })
            return tuple(tasks)

        # Generate default tasks from milestones
        tasks = []
        for milestone in milestones:
            tasks.append({
                'task_id': str(uuid.uuid4()),
                'name': f"Work on: {milestone.get('name', '')}",
                'description': milestone.get('description', ''),
                'status': 'pending',
                'estimated_hours': 2.0,
                'priority': 0.5,
                'milestone_id': milestone.get('milestone_id', ''),
                'dependencies': [],
            })

        return tuple(tasks)

    # ------------------------------------------------------------------
    # Phase 6: ScheduleGeneration
    # ------------------------------------------------------------------

    def _phase_schedule_generation(
        self,
        tasks: tuple[dict[str, Any], ...],
        dependencies: tuple[dict[str, Any], ...],
        context: dict[str, Any],
    ) -> tuple[ScheduleSlot, ...]:
        """Generate a schedule from tasks and dependencies."""
        logger.debug('dec.planning.phase6_schedule_generation')

        schedule: list[ScheduleSlot] = []
        current_offset = 0.0

        for task in tasks:
            duration = task.get('estimated_hours', 1.0)
            schedule.append(ScheduleSlot(
                slot_id=str(uuid.uuid4()),
                task_id=task.get('task_id', ''),
                start_offset_hours=current_offset,
                duration_hours=duration,
                resource_required=task.get('resource', ''),
                priority=task.get('priority', 0.5),
            ))
            current_offset += duration

        return tuple(schedule)

    # ------------------------------------------------------------------
    # Phase 7: RiskReview
    # ------------------------------------------------------------------

    def _phase_risk_review(
        self,
        tasks: tuple[dict[str, Any], ...],
        dependencies: tuple[dict[str, Any], ...],
        constraints: tuple[dict[str, Any], ...],
    ) -> tuple[tuple[PlanRiskAssessment, ...], tuple[str, ...]]:
        """Review risks and identify critical path."""
        logger.debug('dec.planning.phase7_risk_review')

        risks: list[PlanRiskAssessment] = []

        # Risk: too many tasks
        if len(tasks) > 10:
            risks.append(PlanRiskAssessment(
                risk_id=str(uuid.uuid4()),
                description=f'Plan has {len(tasks)} tasks — may be too ambitious',
                probability=0.4,
                impact=0.6,
                mitigations=('Split into phases', 'Prioritize essential tasks'),
                affected_tasks=tuple(t.get('task_id', '') for t in tasks),
            ))

        # Risk: constraint conflicts
        for constraint in constraints:
            if constraint.get('severity', 0.0) > 0.6:
                risks.append(PlanRiskAssessment(
                    risk_id=str(uuid.uuid4()),
                    description=f"High-severity constraint: {constraint.get('description', '')}",
                    probability=0.3,
                    impact=constraint.get('severity', 0.5),
                    mitigations=('Find workaround', 'Relax constraint'),
                ))

        # Critical path: tasks on the longest dependency chain
        critical_path = self._compute_critical_path(tasks, dependencies)

        return tuple(risks), critical_path

    def _compute_critical_path(
        self,
        tasks: tuple[dict[str, Any], ...],
        dependencies: tuple[dict[str, Any], ...],
    ) -> tuple[str, ...]:
        """Compute the critical path through the task graph."""
        if not tasks:
            return ()

        # Simple heuristic: tasks with most dependencies are on critical path
        dep_counts: dict[str, int] = {}
        for dep in dependencies:
            target = dep.get('target_task', '')
            dep_counts[target] = dep_counts.get(target, 0) + 1

        # Sort tasks by dependency count descending
        sorted_tasks = sorted(
            tasks,
            key=lambda t: dep_counts.get(t.get('task_id', ''), 0),
            reverse=True,
        )

        return tuple(t.get('task_id', '') for t in sorted_tasks[:5])

    # ------------------------------------------------------------------
    # Phase 8: ExecutionPlan
    # ------------------------------------------------------------------

    def _phase_execution_plan(
        self,
        goal: dict[str, Any],
        goal_graph: dict[str, Any],
        milestones: tuple[dict[str, Any], ...],
        tasks: tuple[dict[str, Any], ...],
        dependencies: tuple[dict[str, Any], ...],
        constraints: tuple[dict[str, Any], ...],
        schedule: tuple[ScheduleSlot, ...],
        risks: tuple[PlanRiskAssessment, ...],
        critical_path: tuple[str, ...],
        context: dict[str, Any],
    ) -> PlanResult:
        """Produce the final execution plan."""
        logger.debug('dec.planning.phase8_execution_plan')

        total_duration = sum(s.duration_hours for s in schedule)

        risk_dicts = tuple({
            'risk_id': r.risk_id,
            'description': r.description,
            'probability': r.probability,
            'impact': r.impact,
        } for r in risks)

        plan = PlanObject(
            plan_id=str(uuid.uuid4()),
            associated_goal=goal.get('goal_id', ''),
            planning_horizon=context.get('planning_horizon', 'daily'),
            milestones=milestones,
            tasks=tasks,
            dependencies=dependencies,
            constraints=constraints,
            estimated_duration=round(total_duration, 2),
            required_resources=tuple({
                'resource': s.resource_required,
                'slot_id': s.slot_id,
            } for s in schedule if s.resource_required),
            risk_assessment=risk_dicts,
            confidence=0.6 if not risks else max(0.3, 0.6 - len(risks) * 0.05),
            explainability_metadata={
                'phase': 'planning',
                'task_count': len(tasks),
                'milestone_count': len(milestones),
                'schedule_slot_count': len(schedule),
                'risk_count': len(risks),
                'critical_path_length': len(critical_path),
            },
        )

        self._plans[plan.plan_id] = plan

        summary_lines = [
            f"Plan for: {goal.get('description', '')}",
            f"Horizon: {context.get('planning_horizon', 'daily')}",
            f"Tasks: {len(tasks)}",
            f"Milestones: {len(milestones)}",
            f"Estimated duration: {total_duration:.1f} hours",
            f"Risks: {len(risks)}",
            f"Critical path: {len(critical_path)} tasks",
        ]

        return PlanResult(
            plan=plan,
            schedule=schedule,
            risks=risks,
            critical_path=critical_path,
            summary='\n'.join(summary_lines),
            processing_metadata={
                'task_count': len(tasks),
                'milestone_count': len(milestones),
                'dependency_count': len(dependencies),
                'constraint_count': len(constraints),
                'schedule_slot_count': len(schedule),
                'risk_count': len(risks),
                'total_duration': total_duration,
            },
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_plan(self, plan_id: str) -> PlanObject | None:
        """Retrieve a plan by ID."""
        return self._plans.get(plan_id)

    def get_all_plans(self) -> list[PlanObject]:
        """Retrieve all stored plans."""
        return list(self._plans.values())
