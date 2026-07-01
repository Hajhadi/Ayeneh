"""Cross-agent goal coordination — structured goal reference exchange between agents.

Agents can share goal references without creating circular ownership.
Goal Engine remains independent; coordination happens through typed messages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentGoalReference:
    """A structured goal reference passed between agents."""

    agent_name: str
    goal_id: str
    goal_title: str
    reference_type: str = "observation"
    confidence: float = 0.5
    reasoning: str = ""
    supporting_evidence: list[str] = field(default_factory=list)
    related_memories: list[str] = field(default_factory=list)
    related_patterns: list[str] = field(default_factory=list)
    related_reflections: list[str] = field(default_factory=list)


@dataclass
class GoalCoordinationMessage:
    """Message exchanged between agents about goals."""

    source_agent: str
    target_agent: str | None = None
    references: list[AgentGoalReference] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class GoalCoordinationService:
    """Facilitates structured goal reference exchange between agents.

    Agents register their outputs. Other agents can query for goal
    references from specific agent types. No circular dependencies.
    """

    def __init__(self) -> None:
        self._references: dict[str, list[AgentGoalReference]] = {}
        self._messages: list[GoalCoordinationMessage] = []

    def register_references(
        self, agent_name: str, references: list[AgentGoalReference]
    ) -> None:
        self._references[agent_name] = references

    def get_references_from(
        self, source_agent: str, target_agent: str | None = None
    ) -> list[AgentGoalReference]:
        refs = self._references.get(source_agent, [])
        if target_agent:
            return [r for r in refs if r.reference_type in ("observation", "suggestion")]
        return refs

    def get_all_references(self) -> dict[str, list[AgentGoalReference]]:
        return dict(self._references)

    def send_message(self, message: GoalCoordinationMessage) -> None:
        self._messages.append(message)

    def get_messages_for(self, agent_name: str) -> list[GoalCoordinationMessage]:
        return [m for m in self._messages if m.target_agent == agent_name or m.target_agent is None]

    def clear(self) -> None:
        self._references.clear()
        self._messages.clear()
