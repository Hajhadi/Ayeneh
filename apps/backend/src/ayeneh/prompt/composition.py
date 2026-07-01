"""Prompt composition engine — assembles prompts from reusable modules with adaptive selection and compression."""

from __future__ import annotations

import structlog
from typing import Any

from ayeneh.prompt.types import (
    AdaptiveSelection,
    GroundingResult,
    PromptComposition,
    PromptModule,
    PromptProfile,
    ReasoningMetadata,
    ReasoningPolicy,
)

logger = structlog.get_logger(__name__)

_TOKENS_PER_WORD = 4 // 3


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()) * _TOKENS_PER_WORD)


class PromptComposer:
    """Assembles prompts from modular components with adaptive selection and compression."""

    def __init__(self, grounding_service: Any | None = None) -> None:
        self._grounding = grounding_service

    async def compose(
        self,
        profile: PromptProfile,
        policy: ReasoningPolicy,
        selection: AdaptiveSelection,
        query: str,
        token_budget: int = 12000,
        product_profile: Any = None,
    ) -> PromptComposition:
        comp = PromptComposition(
            token_budget=token_budget,
            profile_version=profile.version,
            reasoning_metadata={"policy": policy.name},
        )

        comp.system_prompt = self._build_system_prompt(profile, policy, selection, product_profile)
        comp.user_prompt = self._build_user_prompt(selection, query, policy)
        comp.modules_used = [m.name for m in profile.modules]

        comp.token_estimate = _estimate_tokens(comp.system_prompt) + _estimate_tokens(comp.user_prompt)

        if comp.token_estimate > token_budget:
            comp = self._compress(comp, token_budget)
            comp.compression_applied = True

        comp.grounding_stats = self._compute_grounding_stats(selection)
        comp.reasoning_metadata = {
            "profile_version": profile.version,
            "policy": policy.name,
            "tokens_used": comp.token_estimate,
            "budget": token_budget,
            "compression_applied": comp.compression_applied,
            "modules": comp.modules_used,
        }

        return comp

    def _build_system_prompt(
        self, profile: PromptProfile, policy: ReasoningPolicy, selection: AdaptiveSelection,
        product_profile: Any = None,
    ) -> str:
        parts = []

        if product_profile and product_profile.behavior.identity:
            parts.append(product_profile.behavior.identity)
        else:
            parts.append(profile.system_instructions)

        if product_profile and product_profile.behavior.philosophy:
            parts.append(product_profile.behavior.philosophy)

        if product_profile and product_profile.behavior.safety_policy:
            parts.append(product_profile.behavior.safety_policy)
        elif profile.safety_rules and policy.reasoning_depth != "shallow":
            parts.append("\n".join(profile.safety_rules))

        if product_profile and product_profile.behavior.uncertainty_policy:
            parts.append(product_profile.behavior.uncertainty_policy)

        if product_profile and product_profile.behavior.communication_style:
            parts.append(product_profile.behavior.communication_style)

        if selection.goals_to_inject and policy.goal_priority != "low":
            parts.append("\n" + profile.goal_usage_policy)

        if selection.memories_to_inject and policy.memory_priority != "low":
            parts.append("\n" + profile.memory_usage_policy)

        return "\n".join(parts)

    def _build_user_prompt(
        self, selection: AdaptiveSelection, query: str, policy: ReasoningPolicy
    ) -> str:
        parts = []

        if selection.goals_to_inject:
            parts.append(self._format_goals(selection.goals_to_inject))

        if selection.memories_to_inject:
            parts.append(self._format_memories(selection.memories_to_inject))

        if selection.knowledge_to_inject:
            parts.append(self._format_knowledge(selection.knowledge_to_inject))

        if selection.patterns_to_inject:
            parts.append(self._format_patterns(selection.patterns_to_inject))

        if selection.reflections_to_inject:
            parts.append(self._format_reflections(selection.reflections_to_inject))

        parts.append(f"\nUser query: {query}")

        return "\n\n".join(parts)

    def _format_goals(self, goals: list[dict[str, Any]]) -> str:
        lines = ["Active goals:"]
        for g in goals[:5]:
            progress = f"{g.get('progress', 0):.0%}"
            priority = g.get('priority', 'medium')
            deadline = g.get('deadline', '')
            suffix = f" (due {deadline})" if deadline else ""
            lines.append(f"- [{priority}] {g.get('title', 'Unknown')} ({progress} done){suffix}")
        return "\n".join(lines)

    def _format_memories(self, memories: list[dict[str, Any]]) -> str:
        lines = ["Relevant memories:"]
        for m in memories[:8]:
            conf = m.get("confidence", 0.5)
            lines.append(f"- [{m.get('type', 'unknown')} conf={conf:.2f}] {m.get('content', '')}")
        return "\n".join(lines)

    def _format_knowledge(self, chunks: list[dict[str, Any]]) -> str:
        lines = ["Knowledge from library:"]
        for c in chunks[:5]:
            source = c.get("book_title", "Unknown")
            content = c.get("content", "")[:200]
            lines.append(f"  [{source}] {content}")
        return "\n".join(lines)

    def _format_patterns(self, patterns: list[dict[str, Any]]) -> str:
        lines = ["Detected patterns:"]
        for p in patterns[:3]:
            lines.append(f"- {p.get('description', '')}")
        return "\n".join(lines)

    def _format_reflections(self, reflections: list[dict[str, Any]]) -> str:
        lines = ["Recent reflections:"]
        for r in reflections[:2]:
            title = r.get("title", "")
            narrative = r.get("narrative", "")[:150]
            lines.append(f"- {title}: {narrative}")
        return "\n".join(lines)

    def _compress(self, comp: PromptComposition, budget: int) -> PromptCompression:
        comp.compression_stats = {"original_tokens": comp.token_estimate, "target": budget}

        user_tokens = _estimate_tokens(comp.user_prompt)
        system_tokens = _estimate_tokens(comp.system_prompt)

        if system_tokens + _estimate_tokens(self._strip_metadata(comp.user_prompt)) <= budget:
            comp.user_prompt = self._strip_metadata(comp.user_prompt)
            comp.compression_stats["strategy"] = "strip_metadata"
        else:
            comp.user_prompt = self._truncate_proportionally(comp.user_prompt, budget - system_tokens)
            comp.compression_stats["strategy"] = "proportional_truncation"

        comp.token_estimate = _estimate_tokens(comp.system_prompt) + _estimate_tokens(comp.user_prompt)
        comp.compression_stats["final_tokens"] = comp.token_estimate
        return comp

    def _strip_metadata(self, text: str) -> str:
        lines = text.split("\n")
        stripped = []
        for line in lines:
            if line.startswith("[memory:") or line.startswith("[goal:") or line.startswith("[knowledge:"):
                continue
            stripped.append(line)
        return "\n".join(stripped)

    def _truncate_proportionally(self, text: str, target_tokens: int) -> str:
        words = text.split()
        target_words = max(1, int(target_tokens / _TOKENS_PER_WORD))
        if len(words) <= target_words:
            return text
        return " ".join(words[:target_words]) + "..."

    @staticmethod
    def _compute_grounding_stats(selection: AdaptiveSelection) -> dict[str, Any]:
        total = (len(selection.memories_to_inject) + len(selection.goals_to_inject)
                 + len(selection.knowledge_to_inject))
        return {"sources_injected": total, "token_budget": selection.token_budget}
