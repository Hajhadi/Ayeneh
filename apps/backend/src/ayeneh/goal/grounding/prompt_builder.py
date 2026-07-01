"""Goal-aware prompt builder — selects relevant goals adaptively for each agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from ayeneh.goal.grounding.service import GoalGroundingResult, GroundedGoal

logger = structlog.get_logger(__name__)


@dataclass
class GoalPromptSelection:
    """Selected goals for prompt injection with reasoning metadata."""

    goals: list[GroundedGoal] = field(default_factory=list)
    token_estimate: int = 0
    selection_reasoning: str = ""
    total_evaluated: int = 0
    selected_count: int = 0
    rejected_count: int = 0
    truncated: bool = False


class GoalPromptBuilder:
    """Selects goals most relevant to the current context and formats for prompt injection.

    Instead of dumping all goals, selects goals most relevant to:
    - current conversation topic
    - recent memories
    - patterns
    - reflection topics
    - knowledge retrieved
    - token budget
    """

    def __init__(self, goal_grounding: Any = None) -> None:
        self._grounding = goal_grounding

    async def build_goal_prompt(
        self,
        user_id: str,
        context: dict[str, Any],
        *,
        token_budget: int = 1500,
        max_goals: int = 8,
        agent_type: str = "conversation",
    ) -> GoalPromptSelection:
        """Build an adaptive goal prompt for a specific agent context."""
        grounding = await self._grounding.ground_goals(user_id, max_goals=max_goals)

        selected = self._select_relevant_goals(
            grounding.grounded_goals, context, agent_type, max_goals
        )

        selection = GoalPromptSelection(
            goals=selected,
            total_evaluated=grounding.total_goals_evaluated,
            selected_count=len(selected),
            rejected_count=grounding.total_goals_evaluated - len(selected),
        )

        selection.token_estimate = sum(self._estimate_goal_tokens(g) for g in selected)
        selection.truncated = selection.token_estimate > token_budget

        if selection.truncated:
            selected = selected[:max_goals // 2]
            selection.goals = selected
            selection.truncated = True
            selection.selection_reasoning = "Truncated due to token budget"
        else:
            selection.selection_reasoning = self._explain_selection(selected, context)

        return selection

    def format_goals_for_agent(
        self,
        selection: GoalPromptSelection,
        agent_type: str,
    ) -> str:
        """Format selected goals as a prompt block for a specific agent."""
        if not selection.goals:
            return ""

        lines = []

        if agent_type == "conversation":
            lines.append("User's active goals (consider in your response):")
            for g in selection.goals:
                status = f"{g.progress:.0%} complete"
                if g.deadline:
                    status += f", due {g.deadline}"
                lines.append(f"- [{g.priority}] {g.title} ({status})")

        elif agent_type == "reflection":
            lines.append("Goals to reflect upon:")
            for g in selection.goals:
                lines.append(f"- {g.title} (progress: {g.progress:.0%}, priority: {g.priority})")

        elif agent_type == "pattern":
            lines.append("Goals for pattern analysis:")
            for g in selection.goals:
                lines.append(f"- {g.title} (progress: {g.progress:.0%})")

        elif agent_type == "blind_spot":
            lines.append("Goals to check for blind spots:")
            for g in selection.goals:
                lines.append(f"- {g.title} (priority: {g.priority}, progress: {g.progress:.0%})")

        else:
            lines.append("Active goals:")
            for g in selection.goals:
                lines.append(f"- {g.title}")

        return "\n".join(lines)

    def _select_relevant_goals(
        self,
        goals: list[GroundedGoal],
        context: dict[str, Any],
        agent_type: str,
        max_goals: int,
    ) -> list[GroundedGoal]:
        """Score and rank goals by relevance to the current context."""
        scored = []
        for g in goals:
            score = self._score_relevance(g, context, agent_type)
            scored.append((score, g))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [g for _, g in scored[:max_goals]]

    def _score_relevance(
        self, goal: GroundedGoal, context: dict[str, Any], agent_type: str
    ) -> float:
        """Score goal relevance based on context signals."""
        score = goal.confidence * 0.3 + goal.retrieval_score * 0.3

        query = context.get("query", "").lower()
        title_words = set(goal.title.lower().split())
        query_words = set(query.split())
        overlap = len(title_words & query_words)
        score += min(0.3, overlap * 0.1)

        if agent_type == "conversation":
            if goal.priority in ("critical", "high"):
                score += 0.2
            if goal.deadline:
                score += 0.1

        elif agent_type == "reflection":
            if goal.progress > 0 and goal.progress < 1.0:
                score += 0.2
            if goal.progress == 0:
                score += 0.1

        elif agent_type == "blind_spot":
            if goal.progress == 0:
                score += 0.2
            if goal.priority in ("critical", "high"):
                score += 0.15

        elif agent_type == "pattern":
            score += 0.1

        return min(1.0, score)

    def _explain_selection(
        self, goals: list[GroundedGoal], context: dict[str, Any]
    ) -> str:
        if not goals:
            return "No goals selected"
        reasons = []
        for g in goals[:3]:
            reasons.append(f"'{g.title}' selected for relevance (score: {g.retrieval_score:.2f})")
        return "; ".join(reasons)

    @staticmethod
    def _estimate_goal_tokens(goal: GroundedGoal) -> int:
        words = len(goal.title.split()) + 10
        return words * 4 // 3
