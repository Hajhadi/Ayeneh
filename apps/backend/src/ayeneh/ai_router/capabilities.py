"""Capability declarations and lightweight provider scoring."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .types import AITaskType


class Capability(StrEnum):
    STREAMING = "streaming"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    MULTILINGUAL = "multilingual"
    LOW_COST = "low_cost"
    LOCAL_ONLY = "local_only"
    OFFLINE = "offline"
    DETERMINISTIC = "deterministic"
    STRUCTURED_OUTPUT = "structured_output"
    JSON_MODE = "json_mode"
    TOOL_CALLING = "tool_calling"
    LONG_CONTEXT = "long_context"
    REASONING = "reasoning"
    HIGH_ACCURACY = "high_accuracy"
    CLOUD_ONLY = "cloud_only"
    VISION = "vision"


@dataclass(frozen=True)
class CapabilitySet:
    capabilities: frozenset[Capability]

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def supports_all(self, capabilities) -> bool:
        return all(self.supports(c) for c in capabilities)

    def supports_any(self, capabilities) -> bool:
        return any(self.supports(c) for c in capabilities)

    def coverage(self, required) -> float:
        return sum(self.supports(c) for c in required) / len(required) if required else 1.0


@dataclass(frozen=True)
class ProviderScore:
    total_score: float
    capability_coverage: float
    matched_capabilities: tuple[str, ...]
    missing_capabilities: tuple[str, ...]


def get_required_capabilities(task_type: str) -> list[Capability]:
    mapping = {
        AITaskType.CONCEPT_DISCOVERY.value: [
            Capability.EXTRACTION,
            Capability.MULTILINGUAL,
            Capability.DETERMINISTIC,
        ],
        AITaskType.FINAL_RESPONSE.value: [
            Capability.REASONING,
            Capability.LONG_CONTEXT,
            Capability.STREAMING,
        ],
        AITaskType.REASONING.value: [Capability.REASONING, Capability.LONG_CONTEXT],
        AITaskType.SUMMARIZATION.value: [Capability.SUMMARIZATION, Capability.LONG_CONTEXT],
        AITaskType.EXTRACTION.value: [Capability.EXTRACTION, Capability.DETERMINISTIC],
        AITaskType.CLASSIFICATION.value: [Capability.CLASSIFICATION, Capability.DETERMINISTIC],
    }
    return mapping.get(task_type, [Capability.STREAMING])


def score_provider(
    caps,
    required,
    *,
    latency_ms=0,
    cost_usd=0,
    success_rate=1.0,
    is_healthy=True,
    policy_preference=0.5,
):
    coverage = caps.coverage(required)
    matched = tuple(c.value for c in required if caps.supports(c))
    missing = tuple(c.value for c in required if not caps.supports(c))
    latency_score = 1 / (1 + max(latency_ms, 0) / 1000)
    cost_score = 1 / (1 + max(cost_usd, 0) * 1000)
    total = (
        (
            coverage * 0.55
            + policy_preference * 0.25
            + success_rate * 0.1
            + latency_score * 0.05
            + cost_score * 0.05
        )
        if is_healthy
        else 0
    )
    return ProviderScore(total, coverage, matched, missing)
