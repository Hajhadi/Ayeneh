"""Prompt observability — tracks prompt generation metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptMetrics:
    """Tracks prompt generation metrics for observability."""

    total_prompts_generated: int = 0
    total_prompt_tokens: int = 0
    total_compressions: int = 0
    avg_prompt_length: float = 0.0
    avg_compression_ratio: float = 0.0
    grounding_rates: list[float] = field(default_factory=list)
    module_sizes: dict[str, list[int]] = field(default_factory=dict)
    profile_usage: dict[str, int] = field(default_factory=dict)
    policy_usage: dict[str, int] = field(default_factory=list)  # type: ignore

    def record_prompt(
        self, profile: str, policy: str, tokens: int,
        modules: list[str], compressed: bool = False,
        grounding_rate: float = 0.0, module_sizes: dict[str, int] | None = None,
    ) -> None:
        self.total_prompts_generated += 1
        self.total_prompt_tokens += tokens
        self.avg_prompt_length = (
            (self.avg_prompt_length * (self.total_prompts_generated - 1) + tokens)
            / self.total_prompts_generated
        )
        if compressed:
            self.total_compressions += 1
        self.grounding_rates.append(grounding_rate)
        if len(self.grounding_rates) > 1000:
            self.grounding_rates = self.grounding_rates[-500:]
        self.profile_usage[profile] = self.profile_usage.get(profile, 0) + 1
        if isinstance(self.policy_usage, dict):
            self.policy_usage[policy] = self.policy_usage.get(policy, 0) + 1
        for mod, size in (module_sizes or {}).items():
            self.module_sizes.setdefault(mod, []).append(size)

    def get_summary(self) -> dict[str, Any]:
        avg_grounding = (
            sum(self.grounding_rates) / len(self.grounding_rates)
            if self.grounding_rates else 0.0
        )
        return {
            "total_prompts": self.total_prompts_generated,
            "total_tokens": self.total_prompt_tokens,
            "avg_tokens": round(self.avg_prompt_length),
            "compression_rate": self.total_compressions / max(self.total_prompts_generated, 1),
            "avg_grounding": round(avg_grounding, 3),
            "profile_usage": dict(self.profile_usage),
        }

    def export_prometheus_text(self) -> str:
        summary = self.get_summary()
        lines = [
            f"ayeneh_prompts_total {summary['total_prompts']}",
            f"ayeneh_prompt_tokens_total {summary['total_tokens']}",
            f"ayeneh_prompt_avg_tokens {summary['avg_tokens']}",
            f"ayeneh_prompt_compression_rate {summary['compression_rate']:.4f}",
            f"ayeneh_prompt_grounding_rate {summary['avg_grounding']:.4f}",
        ]
        return "\n".join(lines) + "\n"
