"""Goal grounding — ensures every goal reference is traceable, scored, and hallucination-free."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GroundedGoal:
    """A goal reference that has been grounded in retrieved Goal objects.

    Every agent that references a goal must use this structure.
    Goals not grounded in actual Goal objects are rejected.
    """

    goal_id: str
    title: str
    retrieval_score: float = 0.0
    reason_selected: str = ""
    source: str = ""
    version: int = 1
    confidence: float = 0.5
    priority: str = "medium"
    progress: float = 0.0
    deadline: str | None = None
    related_memories: list[str] = field(default_factory=list)
    related_patterns: list[str] = field(default_factory=list)
    related_reflections: list[str] = field(default_factory=list)
    reasoning_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GoalGroundingResult:
    """Result of grounding goals for an agent response."""

    grounded_goals: list[GroundedGoal] = field(default_factory=list)
    total_goals_evaluated: int = 0
    goals_selected: int = 0
    goals_rejected: int = 0
    grounding_latency_ms: float = 0.0
    reasoning_metadata: dict[str, Any] = field(default_factory=dict)


class GoalGroundingService:
    """Ensures every goal reference is grounded in retrieved Goal objects.

    Rejects any goal reference that cannot be traced to a real Goal.
    Prevents hallucination of goals.
    """

    def __init__(self, goal_service: Any, goal_retrieval: Any) -> None:
        self._goal_service = goal_service
        self._goal_retrieval = goal_retrieval

    async def ground_goals(
        self,
        user_id: str,
        candidate_goal_ids: list[str] | None = None,
        *,
        max_goals: int = 10,
        min_score: float = 0.0,
    ) -> GoalGroundingResult:
        """Ground goal references by verifying they exist and scoring relevance."""
        import time
        start = time.monotonic()

        result = GoalGroundingResult()

        active_goals = await self._goal_service.get_active_goals(user_id)
        goal_map = {g.id: g for g in active_goals}
        result.total_goals_evaluated = len(active_goals)

        candidate_ids = candidate_goal_ids or [g.id for g in active_goals]
        seen = set()

        for gid in candidate_ids:
            if gid in seen or len(result.grounded_goals) >= max_goals:
                continue
            seen.add(gid)

            goal = goal_map.get(gid)
            if goal is None:
                result.goals_rejected += 1
                continue

            grounded = GroundedGoal(
                goal_id=goal.id,
                title=goal.title,
                retrieval_score=goal.importance,
                reason_selected="retrieved from active goals",
                source="goal_service",
                version=1,
                confidence=goal.confidence,
                priority=goal.priority,
                progress=goal.progress,
                deadline=goal.deadline,
            )
            if grounded.retrieval_score >= min_score:
                result.grounded_goals.append(grounded)
                result.goals_selected += 1
            else:
                result.goals_rejected += 1

        result.grounding_latency_ms = (time.monotonic() - start) * 1000
        return result

    def validate_grounding(
        self,
        agent_output: dict[str, Any],
        grounded_goals: GoalGroundingResult,
    ) -> tuple[bool, list[str]]:
        """Validate that all goal references in agent output are grounded."""
        grounded_ids = {g.goal_id for g in grounded_goals.grounded_goals}
        referenced = agent_output.get("referenced_goal_ids", [])

        issues = []
        for ref_id in referenced:
            if ref_id not in grounded_ids:
                issues.append(f"Ungrounded goal reference: {ref_id}")

        return len(issues) == 0, issues
