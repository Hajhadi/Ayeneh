"""Product Profile — first-class abstraction for multi-product cognitive platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BehaviorPolicy:
    philosophy: str = ""
    identity: str = ""
    communication_style: str = ""
    intervention_strategy: str = ""
    uncertainty_policy: str = ""
    epistemic_policy: str = ""
    reasoning_policy: str = ""
    safety_policy: str = ""
    dependency_policy: str = ""


@dataclass
class ResourcePolicy:
    enabled_agents: list[str] = field(default_factory=list)
    enabled_services: list[str] = field(default_factory=list)
    enabled_prompt_profiles: list[str] = field(default_factory=list)
    enabled_evaluation_suites: list[str] = field(default_factory=list)
    enabled_jobs: list[str] = field(default_factory=list)
    enabled_apis: list[str] = field(default_factory=list)


@dataclass
class KnowledgePolicy:
    enabled_libraries: list[str] = field(default_factory=list)
    retrieval_strategy: str = "hybrid"
    citation_policy: str = "always"


@dataclass
class GoalPolicy:
    goal_strategy: str = "standard"
    goal_reasoning_mode: str = "balanced"


@dataclass
class MemoryPolicy:
    memory_policy: str = "standard"
    evolution_policy: str = "standard"


@dataclass
class ProductProfile:
    """A complete product configuration that defines behavior, resources, and philosophy."""

    id: str = ""
    name: str = ""
    version: str = "1.0"
    description: str = ""
    behavior: BehaviorPolicy = field(default_factory=BehaviorPolicy)
    resources: ResourcePolicy = field(default_factory=ResourcePolicy)
    knowledge: KnowledgePolicy = field(default_factory=KnowledgePolicy)
    goals: GoalPolicy = field(default_factory=GoalPolicy)
    memory: MemoryPolicy = field(default_factory=MemoryPolicy)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_system_prompt(self) -> str:
        parts = []
        if self.behavior.identity:
            parts.append(self.behavior.identity)
        if self.behavior.philosophy:
            parts.append(self.behavior.philosophy)
        if self.behavior.safety_policy:
            parts.append(self.behavior.safety_policy)
        if self.behavior.uncertainty_policy:
            parts.append(self.behavior.uncertainty_policy)
        return "\n\n".join(parts)

    def has_agent(self, agent_name: str) -> bool:
        return not self.resources.enabled_agents or agent_name in self.resources.enabled_agents

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "philosophy": self.behavior.philosophy[:200],
            "identity": self.behavior.identity[:200],
            "enabled_agents": self.resources.enabled_agents,
            "retrieval_strategy": self.knowledge.retrieval_strategy,
        }
