"""Cognitive Prompting Framework — core types and base classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptModule:
    """A reusable prompt component with versioning."""

    name: str
    content: str
    version: str = "1.0"
    token_estimate: int = 0
    priority: int = 10
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptProfile:
    """Versioned prompt configuration for an agent type."""

    agent_type: str
    version: str = "1.0"
    system_instructions: str = ""
    output_contract: str = ""
    reasoning_rules: list[str] = field(default_factory=list)
    safety_rules: list[str] = field(default_factory=list)
    citation_rules: list[str] = field(default_factory=list)
    goal_usage_policy: str = ""
    memory_usage_policy: str = ""
    modules: list[PromptModule] = field(default_factory=list)


@dataclass
class ReasoningPolicy:
    """Configures reasoning behavior for an agent execution."""

    name: str = "fast"
    reasoning_depth: str = "standard"
    retrieval_strategy: str = "default"
    citation_required: bool = True
    goal_priority: str = "medium"
    memory_priority: str = "medium"
    reflection_usage: str = "minimal"
    max_reasoning_tokens: int = 500
    uncertainty_expression: str = "when_evidence_weak"


@dataclass
class PromptComposition:
    """A fully assembled prompt with all modules combined."""

    system_prompt: str = ""
    user_prompt: str = ""
    modules_used: list[str] = field(default_factory=list)
    token_estimate: int = 0
    token_budget: int = 12000
    compression_applied: bool = False
    compression_stats: dict[str, Any] = field(default_factory=dict)
    grounding_stats: dict[str, Any] = field(default_factory=dict)
    reasoning_metadata: dict[str, Any] = field(default_factory=dict)
    profile_version: str = ""


@dataclass
class ReasoningMetadata:
    """Exposed reasoning metadata for every LLM execution."""

    selected_memories: list[dict[str, Any]] = field(default_factory=list)
    ignored_memories: list[dict[str, Any]] = field(default_factory=list)
    selected_goals: list[dict[str, Any]] = field(default_factory=list)
    ignored_goals: list[dict[str, Any]] = field(default_factory=list)
    selected_knowledge: list[dict[str, Any]] = field(default_factory=list)
    ignored_knowledge: list[dict[str, Any]] = field(default_factory=list)
    reasoning_policy: str = ""
    prompt_profile_version: str = ""
    prompt_token_allocation: dict[str, int] = field(default_factory=dict)
    compression_statistics: dict[str, Any] = field(default_factory=dict)
    grounding_statistics: dict[str, Any] = field(default_factory=dict)
    confidence_estimate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_memories": len(self.selected_memories),
            "ignored_memories": len(self.ignored_memories),
            "selected_goals": len(self.selected_goals),
            "ignored_goals": len(self.ignored_goals),
            "selected_knowledge": len(self.selected_knowledge),
            "ignored_knowledge": len(self.ignored_knowledge),
            "reasoning_policy": self.reasoning_policy,
            "prompt_profile_version": self.prompt_profile_version,
            "token_allocation": self.prompt_token_allocation,
            "compression": self.compression_statistics,
            "grounding": self.grounding_statistics,
            "confidence": self.confidence_estimate,
        }


@dataclass
class AdaptiveSelection:
    """Result of adaptive context selection."""

    memories_to_inject: list[dict[str, Any]] = field(default_factory=list)
    goals_to_inject: list[dict[str, Any]] = field(default_factory=list)
    knowledge_to_inject: list[dict[str, Any]] = field(default_factory=list)
    patterns_to_inject: list[dict[str, Any]] = field(default_factory=list)
    reflections_to_inject: list[dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    token_budget: int = 12000
    rejected_items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GroundingResult:
    """Result of grounding validation."""

    is_grounded: bool = True
    grounding_score: float = 1.0
    unsupported_claims: list[str] = field(default_factory=list)
    citations_used: int = 0
    total_claims: int = 0
