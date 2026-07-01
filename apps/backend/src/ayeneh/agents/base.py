"""Base agent contract — every agent implements this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentOutput:
    """Standard output from any agent execution."""

    status: str = "success"
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)


class BaseAgent(ABC):
    """Abstract base for all agents."""

    name: str = "base"

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> AgentOutput:
        """Execute the agent's cognitive task and return structured output."""
