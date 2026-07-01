"""Prompt context builder — assembles prompts from templates and context components."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class ComponentPriority(IntEnum):
    """Priority order for context budget allocation. Lower number = higher priority."""

    INSTRUCTIONS = 1
    SYSTEM_CONTEXT = 2
    CONVERSATION = 3
    USER = 4
    MEMORY = 5
    LIBRARY = 6
    PATTERN = 7
    REFLECTION = 8
    RUNTIME = 9


@dataclass
class ContextComponent:
    """A single piece of context injected into a prompt."""

    name: str
    content: str
    priority: ComponentPriority
    token_estimate: int = 0
    is_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptTemplate:
    """A versioned prompt template."""

    id: str
    task_type: str
    version: int
    content: str
    is_active: bool = True
    output_contract: str = ""
    safety_rules: str = ""


@dataclass
class TokenBudget:
    """Token budget configuration for a task type."""

    total: int = 8000
    instructions_tokens: int = 500
    system_context_tokens: int = 300
    user_context_tokens: int = 200
    dynamic_budget: int = 0

    def __post_init__(self) -> None:
        self.dynamic_budget = (
            self.total
            - self.instructions_tokens
            - self.system_context_tokens
            - self.user_context_tokens
        )


@dataclass
class PromptContext:
    """Fully assembled prompt context ready for LLM consumption."""

    task_type: str
    template_version: int
    messages: list[dict[str, str]] = field(default_factory=list)
    system_prompt: str = ""
    components: list[ContextComponent] = field(default_factory=list)
    total_tokens: int = 0
    truncated_components: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class PromptContextBuilder:
    """Assembles prompts from templates and context components.

    Responsibilities:
    - Load prompt templates by task type and version
    - Merge context from multiple sources
    - Apply prioritization rules
    - Manage token budgets
    - Truncate low-priority context
    - Inject output contracts
    - Produce immutable PromptContext objects
    """

    def __init__(
        self,
        template_repository: PromptTemplateRepository,
        budget_config: dict[str, TokenBudget] | None = None,
    ) -> None:
        self._template_repo = template_repository
        self._budgets = budget_config or {}

    async def build(
        self,
        task_type: str,
        *,
        system_context: str = "",
        runtime_context: str = "",
        user_context: str = "",
        memory_context: str = "",
        pattern_context: str = "",
        reflection_context: str = "",
        library_context: str = "",
        conversation_context: str = "",
        instructions: str = "",
        output_contract: str = "",
        template_version: int | None = None,
        budget: TokenBudget | None = None,
    ) -> PromptContext:
        """Build a complete prompt context from components."""
        template = await self._load_template(task_type, template_version)
        if template is None:
            raise ValueError(f"No active template found for task_type={task_type}")

        effective_budget = budget or self._budgets.get(task_type, TokenBudget())

        components = self._collect_components(
            system_context=system_context,
            runtime_context=runtime_context,
            user_context=user_context,
            memory_context=memory_context,
            pattern_context=pattern_context,
            reflection_context=reflection_context,
            library_context=library_context,
            conversation_context=conversation_context,
            instructions=instructions or template.content,
            output_contract=output_contract or template.output_contract,
        )

        components = self._prioritize(components)

        truncated: list[str] = []
        components, truncated = self._apply_budget(components, effective_budget)

        system_prompt = self._assemble_system_prompt(template, components)
        messages = self._build_messages(conversation_context, components)

        total_tokens = sum(c.token_estimate for c in components)

        ctx = PromptContext(
            task_type=task_type,
            template_version=template.version,
            messages=messages,
            system_prompt=system_prompt,
            components=components,
            total_tokens=total_tokens,
            truncated_components=truncated,
            metadata={
                "template_id": template.id,
                "budget_total": effective_budget.total,
                "budget_used": total_tokens,
            },
        )

        logger.info(
            "prompt_built",
            task_type=task_type,
            version=template.version,
            tokens=total_tokens,
            truncated=len(truncated),
        )
        return ctx

    async def _load_template(
        self, task_type: str, version: int | None
    ) -> PromptTemplate | None:
        if version is not None:
            return await self._template_repo.get_by_version(task_type, version)
        return await self._template_repo.get_active(task_type)

    def _collect_components(
        self,
        *,
        system_context: str,
        runtime_context: str,
        user_context: str,
        memory_context: str,
        pattern_context: str,
        reflection_context: str,
        library_context: str,
        conversation_context: str,
        instructions: str,
        output_contract: str,
    ) -> list[ContextComponent]:
        components: list[ContextComponent] = []

        if instructions:
            components.append(
                ContextComponent(
                    name="instructions",
                    content=instructions,
                    priority=ComponentPriority.INSTRUCTIONS,
                    token_estimate=self._estimate_tokens(instructions),
                    is_required=True,
                )
            )

        if output_contract:
            components.append(
                ContextComponent(
                    name="output_contract",
                    content=output_contract,
                    priority=ComponentPriority.INSTRUCTIONS,
                    token_estimate=self._estimate_tokens(output_contract),
                    is_required=True,
                )
            )

        if system_context:
            components.append(
                ContextComponent(
                    name="system_context",
                    content=system_context,
                    priority=ComponentPriority.SYSTEM_CONTEXT,
                    token_estimate=self._estimate_tokens(system_context),
                    is_required=True,
                )
            )

        if conversation_context:
            components.append(
                ContextComponent(
                    name="conversation",
                    content=conversation_context,
                    priority=ComponentPriority.CONVERSATION,
                    token_estimate=self._estimate_tokens(conversation_context),
                )
            )

        if user_context:
            components.append(
                ContextComponent(
                    name="user",
                    content=user_context,
                    priority=ComponentPriority.USER,
                    token_estimate=self._estimate_tokens(user_context),
                )
            )

        if memory_context:
            components.append(
                ContextComponent(
                    name="memory",
                    content=memory_context,
                    priority=ComponentPriority.MEMORY,
                    token_estimate=self._estimate_tokens(memory_context),
                )
            )

        if library_context:
            components.append(
                ContextComponent(
                    name="library",
                    content=library_context,
                    priority=ComponentPriority.LIBRARY,
                    token_estimate=self._estimate_tokens(library_context),
                )
            )

        if pattern_context:
            components.append(
                ContextComponent(
                    name="pattern",
                    content=pattern_context,
                    priority=ComponentPriority.PATTERN,
                    token_estimate=self._estimate_tokens(pattern_context),
                )
            )

        if reflection_context:
            components.append(
                ContextComponent(
                    name="reflection",
                    content=reflection_context,
                    priority=ComponentPriority.REFLECTION,
                    token_estimate=self._estimate_tokens(reflection_context),
                )
            )

        if runtime_context:
            components.append(
                ContextComponent(
                    name="runtime",
                    content=runtime_context,
                    priority=ComponentPriority.RUNTIME,
                    token_estimate=self._estimate_tokens(runtime_context),
                )
            )

        return components

    def _prioritize(self, components: list[ContextComponent]) -> list[ContextComponent]:
        """Sort components by priority (lowest number = highest priority)."""
        return sorted(components, key=lambda c: (c.priority, -c.token_estimate))

    def _apply_budget(
        self,
        components: list[ContextComponent],
        budget: TokenBudget,
    ) -> tuple[list[ContextComponent], list[str]]:
        """Truncate components to fit within token budget."""
        fixed_tokens = budget.instructions_tokens + budget.system_context_tokens + budget.user_context_tokens
        remaining = budget.total - fixed_tokens

        kept: list[ContextComponent] = []
        truncated: list[str] = []

        for comp in components:
            if comp.is_required:
                kept.append(comp)
                remaining -= comp.token_estimate
                continue

            if comp.token_estimate <= remaining:
                kept.append(comp)
                remaining -= comp.token_estimate
            else:
                if remaining > 0:
                    truncated_content = comp.content[: remaining * 4]
                    kept.append(
                        ContextComponent(
                            name=comp.name,
                            content=truncated_content + "...",
                            priority=comp.priority,
                            token_estimate=remaining,
                        )
                    )
                    truncated.append(comp.name)
                    remaining = 0
                else:
                    truncated.append(comp.name)

        return kept, truncated

    def _assemble_system_prompt(
        self, template: PromptTemplate, components: list[ContextComponent]
    ) -> str:
        """Assemble the system prompt from template and required components."""
        parts = []
        for comp in components:
            if comp.is_required:
                parts.append(f"[{comp.name.upper()}]\n{comp.content}")

        if template.safety_rules:
            parts.append(f"[SAFETY]\n{template.safety_rules}")

        return "\n\n".join(parts)

    def _build_messages(
        self, conversation_context: str, components: list[ContextComponent]
    ) -> list[dict[str, str]]:
        """Build the messages array for the LLM."""
        messages: list[dict[str, str]] = []

        for comp in components:
            if not comp.is_required and comp.name not in ("conversation",):
                messages.append({"role": "system", "content": f"[{comp.name.upper()}]\n{comp.content}"})

        if conversation_context:
            messages.append({"role": "user", "content": conversation_context})

        return messages

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimation: ~4 characters per token."""
        return max(1, len(text) // 4)



class PromptTemplateRepository:
    """Abstract prompt template repository interface."""

    async def get_active(self, task_type: str) -> PromptTemplate | None:
        raise NotImplementedError

    async def get_by_version(self, task_type: str, version: int) -> PromptTemplate | None:
        raise NotImplementedError

    async def list_versions(self, task_type: str) -> list[PromptTemplate]:
        raise NotImplementedError
