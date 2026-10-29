"""Small, dependency-free types for capability based provider routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ProviderType(StrEnum):
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"


class TaskComplexity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AITaskType(StrEnum):
    CONCEPT_DISCOVERY = "concept_discovery"
    FINAL_RESPONSE = "final_response"
    CONVERSATION_GENERATION = "conversation_generation"
    REASONING = "reasoning"
    SUMMARIZATION = "summarization"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"


@dataclass
class AITask:
    task_type: AITaskType
    content: str = ""
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    context: dict[str, Any] = field(default_factory=dict)
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class RoutingDecision:
    task_type: AITaskType
    chosen_provider: str
    chosen_model: str = ""
    routing_reason: str = ""
    policy_used: str = "default"
    alternative_providers: list[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_tokens: int = 0
    confidence: float = 0.0
    fallbacks_used: list[str] = field(default_factory=list)


@dataclass
class RoutingMetrics:
    task_type: AITaskType
    provider: str
    model: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    success: bool = True
    fallback_used: bool = False
