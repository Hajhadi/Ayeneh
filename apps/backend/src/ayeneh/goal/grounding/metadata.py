"""Goal reasoning metadata — tracks how each agent used goals in its reasoning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GoalReasoningMetadata:
    """Reasoning metadata attached to agent outputs.

    Every agent should expose this in its AgentOutput.metadata
    to explain how goals influenced its response.
    """

    agent_name: str = ""
    goals_used: list[dict[str, Any]] = field(default_factory=list)
    goals_ignored: list[dict[str, Any]] = field(default_factory=list)
    reasoning_confidence: float = 0.0
    grounding_score: float = 0.0
    supporting_memories: list[str] = field(default_factory=list)
    supporting_patterns: list[str] = field(default_factory=list)
    supporting_reflections: list[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "goals_used": self.goals_used,
            "goals_ignored": self.goals_ignored,
            "reasoning_confidence": self.reasoning_confidence,
            "grounding_score": self.grounding_score,
            "supporting_memories": self.supporting_memories,
            "supporting_patterns": self.supporting_patterns,
            "supporting_reflections": self.supporting_reflections,
            "explanation": self.explanation,
        }


def attach_goal_metadata(
    output_data: dict[str, Any],
    agent_name: str,
    grounded_goal_ids: list[str],
    ignored_goal_ids: list[str],
    explanation: str = "",
    confidence: float = 0.0,
) -> dict[str, Any]:
    """Attach goal reasoning metadata to agent output data dict."""
    output_data["goal_reasoning"] = GoalReasoningMetadata(
        agent_name=agent_name,
        goals_used=[{"goal_id": gid} for gid in grounded_goal_ids],
        goals_ignored=[{"goal_id": gid} for gid in ignored_goal_ids],
        reasoning_confidence=confidence,
        explanation=explanation,
    ).to_dict()
    return output_data
