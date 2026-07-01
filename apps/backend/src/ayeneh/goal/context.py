"""GoalContextBuilder — assembles goal context for prompt injection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class GoalContext:
    active_goals: list[dict[str, Any]] = field(default_factory=list)
    blocked_goals: list[dict[str, Any]] = field(default_factory=list)
    urgent_goals: list[dict[str, Any]] = field(default_factory=list)
    upcoming_milestones: list[dict[str, Any]] = field(default_factory=list)
    recent_progress: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


class GoalContextBuilder:
    """Assembles goal context for injection into prompts.

    Budget-aware and priority-aware.
    """

    def __init__(self, goal_retrieval: Any, goal_service: Any) -> None:
        self._retrieval = goal_retrieval
        self._service = goal_service

    async def build(self, user_id: str, token_budget: int = 2000) -> GoalContext:
        ctx = GoalContext()

        active = await self._service.get_active_goals(user_id)
        ctx.active_goals = [
            {"id": g.id, "title": g.title, "progress": g.progress,
             "priority": g.priority, "deadline": g.deadline,
             "importance": g.importance}
            for g in active[:10]
        ]

        blocked = await self._retrieval.retrieve_blocked(user_id)
        ctx.blocked_goals = [
            {"id": g.id, "title": g.title, "dependencies": len(g.dependencies)}
            for g in blocked[:5]
        ]

        urgent = await self._retrieval.retrieve_urgent(user_id)
        ctx.urgent_goals = [
            {"id": g.id, "title": g.title, "deadline": g.deadline,
             "progress": g.progress}
            for g in urgent[:5]
        ]

        for g in active:
            for m in g.milestones:
                if not m.completed and m.due_date:
                    ctx.upcoming_milestones.append({
                        "goal": g.title, "milestone": m.title,
                        "due": m.due_date, "progress": m.progress_pct,
                    })
        ctx.upcoming_milestones = ctx.upcoming_milestones[:5]

        for g in active:
            if g.last_progress_at:
                ctx.recent_progress.append({
                    "goal": g.title, "progress": g.progress,
                    "at": g.last_progress_at,
                })
        ctx.recent_progress = ctx.recent_progress[:5]

        ctx.summary = (
            f"{len(active)} active goals, "
            f"{len(blocked)} blocked, "
            f"{len(urgent)} urgent"
        )

        return ctx

    def format_for_prompt(self, ctx: GoalContext, token_budget: int = 1500) -> str:
        lines = []
        if ctx.urgent_goals:
            lines.append("Urgent goals:")
            for g in ctx.urgent_goals:
                lines.append(f"- {g['title']} (due {g['deadline']}, {g['progress']:.0%} done)")

        if ctx.active_goals:
            lines.append("Active goals:")
            for g in ctx.active_goals[:5]:
                lines.append(f"- {g['title']} ({g['priority']}, {g['progress']:.0%})")

        if ctx.blocked_goals:
            lines.append("Blocked goals:")
            for g in ctx.blocked_goals[:3]:
                lines.append(f"- {g['title']} ({g['dependencies']} blockers)")

        if ctx.upcoming_milestones:
            lines.append("Upcoming milestones:")
            for m in ctx.upcoming_milestones[:3]:
                lines.append(f"- {m['goal']}: {m['milestone']} (due {m['due']})")

        if not lines:
            return "No active goals."

        return "\n".join(lines)
