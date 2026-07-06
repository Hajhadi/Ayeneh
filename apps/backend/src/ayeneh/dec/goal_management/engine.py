"""DEC-02 Goal Management Engine.

Goal management engine implementing an 8-phase pipeline:
1. CurrentContext — gather current context
2. ExistingGoals — retrieve existing goals
3. GoalHierarchyReconstruction — rebuild goal hierarchy
4. ConflictDetection — detect goal conflicts
5. PriorityEvaluation — evaluate goal priorities
6. GoalRevision — suggest goal revisions
7. PlanningInterface — prepare planning interface data
8. UpdatedGoalGraph — produce updated goal graph
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from ayeneh.dec.goal_management.types import (
    GOAL_CATEGORIES,
    GOAL_HIERARCHY_LEVELS,
    GOAL_LIFECYCLE,
    GoalConflict,
    GoalHierarchy,
    GoalObject,
    GoalResult,
)

logger = structlog.get_logger(__name__)


class GoalManagementEngine:
    """Goal management engine (DEC-02).

    Pipeline:
        1. CurrentContext — gather current context
        2. ExistingGoals — retrieve existing goals
        3. GoalHierarchyReconstruction — rebuild goal hierarchy
        4. ConflictDetection — detect goal conflicts
        5. PriorityEvaluation — evaluate goal priorities
        6. GoalRevision — suggest goal revisions
        7. PlanningInterface — prepare planning interface data
        8. UpdatedGoalGraph — produce updated goal graph
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._goals: dict[str, GoalObject] = {}

    def process(
        self,
        context: dict[str, Any] | None = None,
        existing_goals: list[dict[str, Any]] | None = None,
    ) -> GoalResult:
        """Run the full DEC-02 pipeline.

        Parameters
        ----------
        context:
            Optional context dict with current state, projects, values.
        existing_goals:
            Optional list of goal dicts to incorporate.
        """
        ctx = context or {}
        raw_goals = existing_goals or []

        logger.info(
            'dec.goal_management.pipeline_started',
            goal_count=len(raw_goals),
        )

        # Phase 1: CurrentContext
        current_context = self._phase_current_context(ctx)

        # Phase 2: ExistingGoals
        goals = self._phase_existing_goals(raw_goals)

        # Phase 3: GoalHierarchyReconstruction
        hierarchy = self._phase_goal_hierarchy_reconstruction(goals)

        # Phase 4: ConflictDetection
        conflicts = self._phase_conflict_detection(goals)

        # Phase 5: PriorityEvaluation
        prioritized = self._phase_priority_evaluation(goals)

        # Phase 6: GoalRevision
        revisions = self._phase_goal_revision(prioritized, conflicts)

        # Phase 7: PlanningInterface
        planning_data = self._phase_planning_interface(prioritized, hierarchy)

        # Phase 8: UpdatedGoalGraph
        result = self._phase_updated_goal_graph(
            prioritized, hierarchy, conflicts, planning_data,
        )

        logger.info(
            'dec.goal_management.pipeline_completed',
            goal_count=len(result.goals),
            conflict_count=len(result.conflicts),
        )

        return result

    # ------------------------------------------------------------------
    # Phase 1: CurrentContext
    # ------------------------------------------------------------------

    def _phase_current_context(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Gather and structure the current context."""
        logger.debug('dec.goal_management.phase1_current_context')

        return {
            'active_projects': context.get('active_projects', []),
            'available_resources': context.get('available_resources', []),
            'time_horizon': context.get('time_horizon', 'daily'),
            'current_values': context.get('current_values', []),
            'recent_decisions': context.get('recent_decisions', []),
        }

    # ------------------------------------------------------------------
    # Phase 2: ExistingGoals
    # ------------------------------------------------------------------

    def _phase_existing_goals(
        self,
        raw_goals: list[dict[str, Any]],
    ) -> tuple[GoalObject, ...]:
        """Parse and structure existing goals."""
        logger.debug('dec.goal_management.phase2_existing_goals', count=len(raw_goals))

        goals: list[GoalObject] = []
        for g in raw_goals:
            goal = GoalObject(
                goal_id=g.get('goal_id', str(uuid.uuid4())),
                description=g.get('description', ''),
                category=g.get('category', ''),
                parent_goal=g.get('parent_goal', ''),
                child_goals=tuple(g.get('child_goals', ())),
                priority=g.get('priority', 0.5),
                current_status=g.get('current_status', 'proposed'),
                supporting_evidence=tuple(g.get('supporting_evidence', ())),
                motivational_sources=tuple(g.get('motivational_sources', ())),
                associated_values=tuple(g.get('associated_values', ())),
                associated_projects=tuple(g.get('associated_projects', ())),
                progress=g.get('progress', 0.0),
                confidence=g.get('confidence', 0.5),
            )
            goals.append(goal)
            self._goals[goal.goal_id] = goal

        return tuple(goals)

    # ------------------------------------------------------------------
    # Phase 3: GoalHierarchyReconstruction
    # ------------------------------------------------------------------

    def _phase_goal_hierarchy_reconstruction(
        self,
        goals: tuple[GoalObject, ...],
    ) -> GoalHierarchy:
        """Reconstruct the goal hierarchy from flat goal list."""
        logger.debug('dec.goal_management.phase3_goal_hierarchy')

        parent_map: dict[str, str] = {}
        children_map: dict[str, tuple[str, ...]] = {}
        level_map: dict[str, str] = {}
        root_goals: list[str] = []

        # Build parent and children maps
        for goal in goals:
            if goal.parent_goal:
                parent_map[goal.goal_id] = goal.parent_goal
                existing = children_map.get(goal.parent_goal, ())
                children_map[goal.parent_goal] = existing + (goal.goal_id,)
            else:
                root_goals.append(goal.goal_id)

            # Assign hierarchy level based on category heuristics
            level = self._determine_hierarchy_level(goal)
            level_map[goal.goal_id] = level

        return GoalHierarchy(
            root_goals=tuple(root_goals),
            parent_map=parent_map,
            children_map=children_map,
            level_map=level_map,
        )

    def _determine_hierarchy_level(self, goal: GoalObject) -> str:
        """Determine hierarchy level based on goal properties."""
        if goal.category in ('spiritual', 'meta_cognitive') and goal.priority > 0.8:
            return 'life_purpose'
        if goal.category in ('career', 'financial', 'creative'):
            return 'domain_goal'
        if goal.associated_projects:
            return 'project_goal'
        if goal.child_goals:
            return 'milestone'
        if goal.priority < 0.3:
            return 'action'
        return 'task'

    # ------------------------------------------------------------------
    # Phase 4: ConflictDetection
    # ------------------------------------------------------------------

    def _phase_conflict_detection(
        self,
        goals: tuple[GoalObject, ...],
    ) -> tuple[GoalConflict, ...]:
        """Detect conflicts between goals."""
        logger.debug('dec.goal_management.phase4_conflict_detection')

        conflicts: list[GoalConflict] = []
        goal_list = list(goals)

        for i, g_a in enumerate(goal_list):
            for g_b in goal_list[i + 1:]:
                conflict = self._check_conflict(g_a, g_b)
                if conflict:
                    conflicts.append(conflict)

        return tuple(conflicts)

    def _check_conflict(
        self,
        g_a: GoalObject,
        g_b: GoalObject,
    ) -> GoalConflict | None:
        """Check if two goals conflict."""
        # Resource conflict: same category, both high priority, different projects
        if (g_a.category == g_b.category
                and g_a.priority > 0.6
                and g_b.priority > 0.6
                and g_a.associated_projects != g_b.associated_projects):
            return GoalConflict(
                conflict_id=str(uuid.uuid4()),
                goal_a=g_a.goal_id,
                goal_b=g_b.goal_id,
                conflict_type='resource_competition',
                severity=0.5,
                resolution_suggestions=(
                    'Consider consolidating projects',
                    'Prioritize one goal and pause the other',
                ),
            )

        # Parent-child contradiction: parent completed, child still active
        if (g_a.goal_id == g_b.parent_goal
                and g_a.current_status == 'completed'
                and g_b.current_status == 'active'):
            return GoalConflict(
                conflict_id=str(uuid.uuid4()),
                goal_a=g_a.goal_id,
                goal_b=g_b.goal_id,
                conflict_type='lifecycle_contradiction',
                severity=0.7,
                resolution_suggestions=(
                    'Complete or archive the child goal',
                    'Reopen the parent goal',
                ),
            )

        return None

    # ------------------------------------------------------------------
    # Phase 5: PriorityEvaluation
    # ------------------------------------------------------------------

    def _phase_priority_evaluation(
        self,
        goals: tuple[GoalObject, ...],
    ) -> tuple[GoalObject, ...]:
        """Evaluate and adjust goal priorities."""
        logger.debug('dec.goal_management.phase5_priority_evaluation')

        adjusted: list[GoalObject] = []
        for goal in goals:
            adjusted_priority = self._compute_adjusted_priority(goal)
            if adjusted_priority != goal.priority:
                adjusted_goal = GoalObject(
                    goal_id=goal.goal_id,
                    description=goal.description,
                    category=goal.category,
                    parent_goal=goal.parent_goal,
                    child_goals=goal.child_goals,
                    priority=round(adjusted_priority, 4),
                    current_status=goal.current_status,
                    supporting_evidence=goal.supporting_evidence,
                    motivational_sources=goal.motivational_sources,
                    associated_values=goal.associated_values,
                    associated_projects=goal.associated_projects,
                    progress=goal.progress,
                    confidence=goal.confidence,
                    version_history=goal.version_history,
                    creation_timestamp=goal.creation_timestamp,
                    explainability_metadata=goal.explainability_metadata,
                )
                adjusted.append(adjusted_goal)
                self._goals[adjusted_goal.goal_id] = adjusted_goal
            else:
                adjusted.append(goal)

        # Sort by priority descending
        return tuple(sorted(adjusted, key=lambda g: g.priority, reverse=True))

    def _compute_adjusted_priority(self, goal: GoalObject) -> float:
        """Compute adjusted priority based on goal properties."""
        base = goal.priority

        # Boost for active status
        if goal.current_status == 'active':
            base = min(base + 0.05, 1.0)

        # Boost for goals with strong evidence
        if len(goal.supporting_evidence) >= 3:
            base = min(base + 0.05, 1.0)

        # Boost for goals with high confidence
        if goal.confidence > 0.8:
            base = min(base + 0.03, 1.0)

        # Reduce for stalled progress
        if goal.current_status == 'active' and goal.progress < 0.1:
            base = max(base - 0.05, 0.0)

        return round(base, 4)

    # ------------------------------------------------------------------
    # Phase 6: GoalRevision
    # ------------------------------------------------------------------

    def _phase_goal_revision(
        self,
        goals: tuple[GoalObject, ...],
        conflicts: tuple[GoalConflict, ...],
    ) -> tuple[str, ...]:
        """Suggest goal revisions based on conflicts and evaluation."""
        logger.debug('dec.goal_management.phase6_goal_revision')

        revisions: list[str] = []

        for conflict in conflicts:
            revisions.append(
                f"Resolve {conflict.conflict_type} between "
                f"goals {conflict.goal_a} and {conflict.goal_b}: "
                f"{'; '.join(conflict.resolution_suggestions)}"
            )

        for goal in goals:
            if goal.progress == 0.0 and goal.current_status == 'active':
                revisions.append(
                    f"Goal '{goal.goal_id}' is active but has zero progress — "
                    f"consider breaking into smaller milestones"
                )
            if goal.confidence < 0.3:
                revisions.append(
                    f"Goal '{goal.goal_id}' has low confidence "
                    f"({goal.confidence}) — consider gathering more evidence"
                )

        return tuple(revisions)

    # ------------------------------------------------------------------
    # Phase 7: PlanningInterface
    # ------------------------------------------------------------------

    def _phase_planning_interface(
        self,
        goals: tuple[GoalObject, ...],
        hierarchy: GoalHierarchy,
    ) -> dict[str, Any]:
        """Prepare data for the planning interface."""
        logger.debug('dec.goal_management.phase7_planning_interface')

        active_goals = [
            g for g in goals if g.current_status in ('active', 'planned')
        ]

        return {
            'active_count': len(active_goals),
            'active_goal_ids': tuple(g.goal_id for g in active_goals),
            'hierarchy_depth': len(hierarchy.level_map),
            'root_count': len(hierarchy.root_goals),
            'ready_for_planning': tuple(
                g.goal_id for g in active_goals if g.progress < 1.0
            ),
        }

    # ------------------------------------------------------------------
    # Phase 8: UpdatedGoalGraph
    # ------------------------------------------------------------------

    def _phase_updated_goal_graph(
        self,
        goals: tuple[GoalObject, ...],
        hierarchy: GoalHierarchy,
        conflicts: tuple[GoalConflict, ...],
        planning_data: dict[str, Any],
    ) -> GoalResult:
        """Produce the final updated goal graph result."""
        logger.debug('dec.goal_management.phase8_updated_goal_graph')

        priority_ranking = tuple(g.goal_id for g in goals)

        revision_suggestions = self._generate_revision_suggestions(goals, conflicts)

        return GoalResult(
            goals=goals,
            hierarchy=hierarchy,
            conflicts=conflicts,
            priority_ranking=priority_ranking,
            revision_suggestions=revision_suggestions,
            planning_interface=planning_data,
            processing_metadata={
                'total_goals': len(goals),
                'conflict_count': len(conflicts),
                'hierarchy_levels': len(set(hierarchy.level_map.values())),
                'active_goals': planning_data.get('active_count', 0),
            },
        )

    def _generate_revision_suggestions(
        self,
        goals: tuple[GoalObject, ...],
        conflicts: tuple[GoalConflict, ...],
    ) -> tuple[str, ...]:
        """Generate high-level revision suggestions."""
        suggestions: list[str] = []

        if not goals:
            suggestions.append('No goals defined — consider setting initial goals')
            return tuple(suggestions)

        active = [g for g in goals if g.current_status == 'active']
        if len(active) > 5:
            suggestions.append(
                f'{len(active)} active goals may be too many — '
                f'consider focusing on top 3-5'
            )

        if conflicts:
            suggestions.append(
                f'{len(conflicts)} goal conflict(s) need resolution'
            )

        categories = {g.category for g in goals if g.category}
        if len(categories) < 2:
            suggestions.append('Consider diversifying goal categories')

        return tuple(suggestions)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_goal(self, goal_id: str) -> GoalObject | None:
        """Retrieve a goal by ID."""
        return self._goals.get(goal_id)

    def get_all_goals(self) -> list[GoalObject]:
        """Retrieve all stored goals."""
        return list(self._goals.values())
