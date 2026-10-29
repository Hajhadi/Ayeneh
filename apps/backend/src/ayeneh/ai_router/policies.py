from __future__ import annotations

from dataclasses import dataclass

from .types import AITaskType, ProviderType, TaskComplexity


@dataclass
class RoutingPolicy:
    name: str = "default"


class PolicyEngine:
    def get_provider_preference(self, task_type, provider_type):
        local = {
            AITaskType.CONCEPT_DISCOVERY,
            AITaskType.EXTRACTION,
            AITaskType.CLASSIFICATION,
            AITaskType.SUMMARIZATION,
        }
        return 0.85 if ((task_type in local) == (provider_type == ProviderType.LOCAL)) else 0.35

    def evaluate(self, task, providers):
        if task.complexity == TaskComplexity.HIGH or task.task_type in {
            AITaskType.FINAL_RESPONSE,
            AITaskType.REASONING,
        }:
            preferred = ProviderType.CLOUD
        else:
            preferred = ProviderType.LOCAL
        for p in providers.values():
            if p.provider_type == preferred:
                return preferred, f"{preferred.value} preferred by policy"
        p = next(iter(providers.values()), None)
        return (p.provider_type, "fallback provider") if p else (preferred, "no provider")
