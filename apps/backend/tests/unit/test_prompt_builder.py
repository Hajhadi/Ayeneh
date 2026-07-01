"""Comprehensive tests for the Prompt Builder subsystem."""

from __future__ import annotations

import pytest

from ayeneh.prompts.prompt_context import (
    PromptContextBuilder,
    PromptTemplate,
    PromptTemplateRepository,
    TokenBudget,
)

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class FakeTemplateRepo(PromptTemplateRepository):
    def __init__(self) -> None:
        self._templates: dict[str, list[PromptTemplate]] = {}

    def add(self, template: PromptTemplate) -> None:
        self._templates.setdefault(template.task_type, []).append(template)

    async def get_active(self, task_type: str) -> PromptTemplate | None:
        templates = self._templates.get(task_type, [])
        active = [t for t in templates if t.is_active]
        return max(active, key=lambda t: t.version) if active else None

    async def get_by_version(self, task_type: str, version: int) -> PromptTemplate | None:
        for t in self._templates.get(task_type, []):
            if t.version == version:
                return t
        return None

    async def list_versions(self, task_type: str) -> list[PromptTemplate]:
        return sorted(self._templates.get(task_type, []), key=lambda t: t.version)


def _make_template(
    task_type: str = "conversation",
    version: int = 1,
    content: str = "You are a helpful assistant.",
    output_contract: str = "",
    safety_rules: str = "",
    active: bool = True,
) -> PromptTemplate:
    return PromptTemplate(
        id=f"tpl-{task_type}-v{version}",
        task_type=task_type,
        version=version,
        content=content,
        is_active=active,
        output_contract=output_contract,
        safety_rules=safety_rules,
    )


@pytest.fixture
def repo() -> FakeTemplateRepo:
    r = FakeTemplateRepo()
    r.add(_make_template("conversation", 1, "You are a helpful assistant."))
    r.add(_make_template("conversation", 2, "You are a knowledgeable assistant.", active=True))
    r.add(_make_template("memory_extraction", 1, "Extract memories from messages."))
    return r


@pytest.fixture
def builder(repo: FakeTemplateRepo) -> PromptContextBuilder:
    return PromptContextBuilder(template_repository=repo)


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

class TestTemplateLoading:
    @pytest.mark.asyncio
    async def test_loads_active_template(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build("conversation")
        assert ctx.template_version == 2

    @pytest.mark.asyncio
    async def test_loads_specific_version(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build("conversation", template_version=1)
        assert ctx.template_version == 1

    @pytest.mark.asyncio
    async def test_missing_template_raises(self, builder: PromptContextBuilder) -> None:
        with pytest.raises(ValueError, match="No active template"):
            await builder.build("nonexistent_task")

    @pytest.mark.asyncio
    async def test_no_active_template_raises(self) -> None:
        repo = FakeTemplateRepo()
        repo.add(_make_template("empty", 1, "test", active=False))
        builder = PromptContextBuilder(template_repository=repo)
        with pytest.raises(ValueError, match="No active template"):
            await builder.build("empty")


# ---------------------------------------------------------------------------
# Context merging
# ---------------------------------------------------------------------------

class TestContextMerging:
    @pytest.mark.asyncio
    async def test_all_contexts_merged(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build(
            "conversation",
            system_context="You are Ayeneh.",
            runtime_context="Request ID: abc123",
            user_context="User: John",
            memory_context="User likes cats.",
            pattern_context="User tends to procrastinate.",
            reflection_context="User has been reading more.",
            library_context="Book: Thinking Fast and Slow.",
            conversation_context="User: Hello!",
            instructions="Be helpful.",
            output_contract="Return JSON.",
        )
        assert len(ctx.components) >= 8
        names = {c.name for c in ctx.components}
        assert "system_context" in names
        assert "memory" in names
        assert "library" in names

    @pytest.mark.asyncio
    async def test_partial_contexts(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build(
            "conversation",
            system_context="You are Ayeneh.",
            memory_context="User likes cats.",
        )
        names = {c.name for c in ctx.components}
        assert "system_context" in names
        assert "memory" in names
        assert "library" not in names


# ---------------------------------------------------------------------------
# Prioritization
# ---------------------------------------------------------------------------

class TestPrioritization:
    @pytest.mark.asyncio
    async def test_components_ordered_by_priority(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build(
            "conversation",
            system_context="sys",
            memory_context="mem",
            runtime_context="run",
            reflection_context="ref",
        )
        priorities = [c.priority for c in ctx.components]
        assert priorities == sorted(priorities)

    @pytest.mark.asyncio
    async def test_instructions_highest_priority(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build(
            "conversation",
            instructions="Do this.",
            runtime_context="metadata",
        )
        assert ctx.components[0].name == "instructions"

    @pytest.mark.asyncio
    async def test_runtime_lowest_priority(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build(
            "conversation",
            instructions="Do this.",
            system_context="sys",
            conversation_context="conv",
            user_context="user",
            memory_context="mem",
            library_context="lib",
            pattern_context="pat",
            reflection_context="ref",
            runtime_context="run",
        )
        assert ctx.components[-1].name == "runtime"


# ---------------------------------------------------------------------------
# Token budgeting
# ---------------------------------------------------------------------------

class TestTokenBudgeting:
    @pytest.mark.asyncio
    async def test_budget_respected(self, builder: PromptContextBuilder) -> None:
        budget = TokenBudget(total=200, instructions_tokens=20, system_context_tokens=20, user_context_tokens=20)
        ctx = await builder.build(
            "conversation",
            system_context="x" * 400,
            memory_context="y" * 400,
            runtime_context="z" * 400,
            budget=budget,
        )
        assert ctx.total_tokens <= 200

    @pytest.mark.asyncio
    async def test_default_budget_used(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build("conversation")
        assert ctx.metadata["budget_total"] == 8000

    @pytest.mark.asyncio
    async def test_custom_budget_per_task(self) -> None:
        repo = FakeTemplateRepo()
        repo.add(_make_template("conversation", 1, "test"))
        budgets = {"conversation": TokenBudget(total=2000)}
        builder = PromptContextBuilder(template_repository=repo, budget_config=budgets)
        ctx = await builder.build("conversation")
        assert ctx.metadata["budget_total"] == 2000


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------

class TestTruncation:
    @pytest.mark.asyncio
    async def test_low_priority_truncated_first(self, builder: PromptContextBuilder) -> None:
        budget = TokenBudget(total=50, instructions_tokens=5, system_context_tokens=5, user_context_tokens=5)
        ctx = await builder.build(
            "conversation",
            instructions="x" * 200,
            system_context="y" * 200,
            memory_context="m" * 200,
            runtime_context="r" * 200,
            budget=budget,
        )
        assert "runtime" in ctx.truncated_components

    @pytest.mark.asyncio
    async def test_required_components_never_truncated(self, builder: PromptContextBuilder) -> None:
        budget = TokenBudget(total=30, instructions_tokens=5, system_context_tokens=5, user_context_tokens=5)
        ctx = await builder.build(
            "conversation",
            instructions="x" * 200,
            system_context="y" * 200,
            budget=budget,
        )
        names = {c.name for c in ctx.components}
        assert "instructions" in names
        assert "system_context" in names

    @pytest.mark.asyncio
    async def test_truncation_metadata_recorded(self, builder: PromptContextBuilder) -> None:
        budget = TokenBudget(total=30, instructions_tokens=5, system_context_tokens=5, user_context_tokens=5)
        ctx = await builder.build(
            "conversation",
            instructions="x" * 200,
            memory_context="m" * 200,
            runtime_context="r" * 200,
            budget=budget,
        )
        assert len(ctx.truncated_components) >= 1


# ---------------------------------------------------------------------------
# Prompt version selection
# ---------------------------------------------------------------------------

class TestPromptVersionSelection:
    @pytest.mark.asyncio
    async def test_uses_latest_active_version(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build("conversation")
        assert ctx.template_version == 2

    @pytest.mark.asyncio
    async def test_specific_version_override(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build("conversation", template_version=1)
        assert ctx.template_version == 1

    @pytest.mark.asyncio
    async def test_template_content_in_system_prompt(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build("conversation")
        assert "knowledgeable assistant" in ctx.system_prompt


# ---------------------------------------------------------------------------
# Output contract injection
# ---------------------------------------------------------------------------

class TestOutputContract:
    @pytest.mark.asyncio
    async def test_output_contract_from_template(self, builder: PromptContextBuilder) -> None:
        repo = FakeTemplateRepo()
        repo.add(_make_template("extraction", 1, "Extract data.", output_contract="Return JSON with keys: facts, emotions."))
        builder = PromptContextBuilder(template_repository=repo)
        ctx = await builder.build("extraction")
        assert "output_contract" in {c.name for c in ctx.components}

    @pytest.mark.asyncio
    async def test_output_contract_override(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build(
            "conversation",
            output_contract="Custom output: {text: string}",
        )
        assert any("Custom output" in c.content for c in ctx.components)

    @pytest.mark.asyncio
    async def test_output_contract_is_required(self, builder: PromptContextBuilder) -> None:
        repo = FakeTemplateRepo()
        repo.add(_make_template("x", 1, "test", output_contract="schema"))
        builder = PromptContextBuilder(template_repository=repo)
        ctx = await builder.build("x")
        comp = next(c for c in ctx.components if c.name == "output_contract")
        assert comp.is_required


# ---------------------------------------------------------------------------
# Safety rules
# ---------------------------------------------------------------------------

class TestSafetyRules:
    @pytest.mark.asyncio
    async def test_safety_rules_in_system_prompt(self, builder: PromptContextBuilder) -> None:
        repo = FakeTemplateRepo()
        repo.add(_make_template("safe", 1, "Be safe.", safety_rules="Never give medical advice."))
        builder = PromptContextBuilder(template_repository=repo)
        ctx = await builder.build("safe")
        assert "Never give medical advice" in ctx.system_prompt


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

class TestPromptAssembly:
    @pytest.mark.asyncio
    async def test_system_prompt_structure(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build(
            "conversation",
            system_context="You are Ayeneh.",
            instructions="Be helpful.",
        )
        assert "[INSTRUCTIONS]" in ctx.system_prompt
        assert "[SYSTEM_CONTEXT]" in ctx.system_prompt
        assert "You are Ayeneh." in ctx.system_prompt

    @pytest.mark.asyncio
    async def test_messages_array(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build(
            "conversation",
            conversation_context="User: Hello!",
            memory_context="User likes cats.",
        )
        assert len(ctx.messages) >= 1
        assert ctx.messages[-1]["role"] == "user"
        assert "Hello!" in ctx.messages[-1]["content"]

    @pytest.mark.asyncio
    async def test_metadata_populated(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build("conversation")
        assert "template_id" in ctx.metadata
        assert "budget_total" in ctx.metadata
        assert "budget_used" in ctx.metadata


# ---------------------------------------------------------------------------
# Empty context handling
# ---------------------------------------------------------------------------

class TestEmptyContext:
    @pytest.mark.asyncio
    async def test_empty_contexts_builds_prompt(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build("conversation")
        assert ctx.task_type == "conversation"
        assert ctx.system_prompt != ""

    @pytest.mark.asyncio
    async def test_only_instructions(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build("conversation", instructions="Do something.")
        assert any("Do something." in c.content for c in ctx.components)

    @pytest.mark.asyncio
    async def test_only_system_context(self, builder: PromptContextBuilder) -> None:
        ctx = await builder.build("conversation", system_context="You are a bot.")
        assert any("You are a bot." in c.content for c in ctx.components)


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

class TestTokenEstimation:
    def test_estimate_tokens(self) -> None:
        assert PromptContextBuilder._estimate_tokens("hello") == 1
        assert PromptContextBuilder._estimate_tokens("a" * 100) == 25
        assert PromptContextBuilder._estimate_tokens("") == 1

    def test_token_budget_dynamic(self) -> None:
        budget = TokenBudget(total=1000, instructions_tokens=100, system_context_tokens=50, user_context_tokens=50)
        assert budget.dynamic_budget == 800
