"""PromptContext service — assembles grounded prompt context from all data sources.

Goal context is injected as a dedicated block, budget-aware and priority-aware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ayeneh.application.services.retrieval import RetrievalResult

logger = structlog.get_logger(__name__)


@dataclass
class PromptContext:
    """Assembled prompt context with all grounded sources."""

    system_context: str = ""
    goal_context: str = ""
    memory_context: str = ""
    knowledge_context: str = ""
    pattern_context: str = ""
    reflection_context: str = ""
    conversation_context: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    token_estimate: int = 0
    token_budget: int = 12000
    truncated_components: list[str] = field(default_factory=list)

    # Goal-specific metadata
    active_goal_count: int = 0
    urgent_goal_count: int = 0
    blocked_goal_count: int = 0
    goal_truncated: bool = False

    # Epistemic metadata
    epistemic_context: str = ""


class PromptContextService:
    """Assembles prompt context from all data sources for the ConversationAgent.

    Priority: system > goals > memory > knowledge > pattern > reflection > conversation.
    Goals are injected as a dedicated block before memories.
    """

    def __init__(
        self,
        retrieval_service: Any | None = None,
        conversation_service: Any | None = None,
    ) -> None:
        self._retrieval = retrieval_service
        self._conversation_service = conversation_service

    async def assemble(
        self,
        user_id: str,
        query: str,
        *,
        conversation_id: str | None = None,
        token_budget: int = 12000,
    ) -> PromptContext:
        ctx = PromptContext(token_budget=token_budget)
        ctx.system_context = (
            "You are Ayeneh, a Cognitive Companion for self-observation "
            "and cognitive growth. Reflect the user's thinking patterns back to them. "
            "Ground your responses in retrieved context. "
            "Cite sources when referencing knowledge. "
            "Ask reflective questions. Avoid premature answers."
        )

        retrieval = await self._retrieve(user_id, query)
        if retrieval is None:
            return ctx

        ctx.citations = retrieval.citations

        # Goal context — injected before memory
        ctx.goal_context = self._format_goals(retrieval)
        ctx.active_goal_count = len(retrieval.active_goals)
        ctx.urgent_goal_count = len(retrieval.urgent_goals)
        ctx.blocked_goal_count = len(retrieval.blocked_goals)

        ctx.memory_context = self._format_memories(retrieval)
        ctx.knowledge_context = self._format_knowledge(retrieval)
        ctx.pattern_context = self._format_patterns(retrieval)
        ctx.reflection_context = self._format_reflections(retrieval)
        ctx.epistemic_context = self._format_epistemic(retrieval)

        if conversation_id and self._conversation_service:
            ctx.conversation_context = await self._format_conversation(user_id, conversation_id)

        ctx = self._apply_budget(ctx)
        ctx.token_estimate = sum(
            self._estimate_tokens(getattr(ctx, f, ""))
            for f in [
                "system_context",
                "goal_context",
                "memory_context",
                "knowledge_context",
                "pattern_context",
                "reflection_context",
                "conversation_context",
                "epistemic_context",
            ]
        )

        return ctx

    async def _retrieve(self, user_id: str, query: str) -> RetrievalResult | None:
        if not self._retrieval:
            return None
        try:
            return await self._retrieval.retrieve_context(user_id, query)
        except Exception as exc:
            logger.warning("retrieval_failed", error=str(exc))
            return None

    def _format_goals(self, retrieval: RetrievalResult) -> str:
        """Format goal context as a dedicated prompt block."""
        lines = []

        if retrieval.urgent_goals:
            lines.append("Urgent goals (require immediate attention):")
            for g in retrieval.urgent_goals:
                lines.append(f"- {g['title']} (due {g['deadline']}, {g['progress']:.0%} done)")

        if retrieval.active_goals:
            lines.append("Active goals:")
            for g in retrieval.active_goals[:5]:
                lines.append(f"- {g['title']} ({g['priority']}, {g['progress']:.0%})")

        if retrieval.blocked_goals:
            lines.append("Blocked goals:")
            for g in retrieval.blocked_goals[:3]:
                lines.append(f"- {g['title']} ({g['dependencies']} blockers)")

        if retrieval.recent_goal_progress:
            lines.append("Recent goal progress:")
            for p in retrieval.recent_goal_progress[:3]:
                lines.append(f"- {p['goal']}: {p['progress']:.0%}")

        if not lines:
            return "No active goals."

        return "\n".join(lines)

    def _format_memories(self, retrieval: RetrievalResult) -> str:
        if not retrieval.memories:
            return ""
        evolved_count = getattr(retrieval, "evolved_memory_count", 0)
        header = "Relevant memories"
        if evolved_count > 0:
            header += f" ({evolved_count} evolved)"
        header += ":"
        lines = [header]
        # Keep retrieval compact: ranking already happened upstream, so preserve
        # the strongest evidence and avoid spending prompt budget on verbose
        # duplicate prose. Provenance and confidence remain visible to the model.
        for mem in retrieval.memories[:8]:
            ev_ver = mem.get("evolution_version", 1)
            tag = f"v{ev_ver}" if ev_ver > 1 else mem.get("type", "unknown")
            conf = mem.get("confidence", 0.5)
            content = self._compact_text(str(mem.get("content", "")), 260)
            if content:
                lines.append(f"- [{tag} conf={conf:.2f}] {content}")
        return "\n".join(lines)

    def _format_knowledge(self, retrieval: RetrievalResult) -> str:
        if not retrieval.knowledge_chunks:
            return ""
        lines = ["Relevant knowledge from your library:"]
        for chunk in retrieval.knowledge_chunks[:6]:
            source = chunk.get("book_title", "Unknown")
            section = chunk.get("section", "")
            prefix = f"  [{source}"
            if section:
                prefix += f" — {section}"
            prefix += "]"
            lines.append(f"{prefix} {self._compact_text(str(chunk.get('content', '')), 240)}")
        return "\n".join(lines)

    def _format_patterns(self, retrieval: RetrievalResult) -> str:
        if not retrieval.patterns:
            return ""
        lines = ["Detected cognitive patterns:"]
        for pat in retrieval.patterns[:5]:
            lines.append(f"- {pat.get('description', '')}")
        return "\n".join(lines)

    def _format_reflections(self, retrieval: RetrievalResult) -> str:
        if not retrieval.reflections:
            return ""
        lines = ["Recent reflections:"]
        for ref in retrieval.reflections[:2]:
            title = ref.get("title", "")
            narrative = self._compact_text(str(ref.get("narrative", "")), 180)
            lines.append(f"- {title}: {narrative}")
        return "\n".join(lines)

    def _format_epistemic(self, retrieval: RetrievalResult) -> str:
        """Format epistemic context as concise explanations."""
        if not retrieval.epistemic_metadata:
            return ""

        meta = retrieval.epistemic_metadata
        lines: list[str] = []

        if meta.selection_reasons:
            lines.append("Source selection rationale:")
            for reason in meta.selection_reasons[:3]:
                lines.append(f"- {reason}")

        if meta.confidence_explanations:
            lines.append("Confidence notes:")
            for exp in meta.confidence_explanations[:3]:
                lines.append(f"- {exp}")

        if meta.applicability_explanations:
            lines.append("Applicability:")
            for exp in meta.applicability_explanations[:3]:
                lines.append(f"- {exp}")

        if meta.scope_filtered_count > 0:
            lines.append(f"Note: {meta.scope_filtered_count} sources excluded by scope filtering.")

        return "\n".join(lines) if lines else ""

    async def _format_conversation(self, user_id: str, conversation_id: str) -> str:
        if not self._conversation_service:
            return ""
        try:
            messages = await self._conversation_service.get_messages(conversation_id, limit=20)
            if not messages:
                return ""
            lines = ["Recent conversation:"]
            for msg in messages[-6:]:
                role = msg.get("role", "user").capitalize()
                content = self._compact_text(str(msg.get("content", "")), 180)
                lines.append(f"{role}: {content}")
            return "\n".join(lines)
        except Exception:
            return ""

    def _apply_budget(self, ctx: PromptContext) -> PromptContext:
        """Truncate components that exceed the remaining token budget.

        Priority order: system > goals > memory > knowledge > pattern > reflection > conversation.
        Goals are truncated before memories when budget is tight.
        """
        priority_order = [
            ("system_context", 2000),
            ("goal_context", 1500),
            ("memory_context", 2000),
            ("knowledge_context", 3000),
            ("pattern_context", 1000),
            ("reflection_context", 1000),
            ("conversation_context", 2000),
        ]
        remaining = ctx.token_budget
        for field_name, max_tokens in priority_order:
            if remaining <= 0:
                setattr(ctx, field_name, "")
                ctx.truncated_components.append(field_name)
                if field_name == "goal_context":
                    ctx.goal_truncated = True
                continue
            cap = min(max_tokens, remaining)
            text = getattr(ctx, field_name, "")
            tokens = self._estimate_tokens(text)
            if tokens > cap:
                setattr(ctx, field_name, self._fit_lines(text, cap))
                ctx.truncated_components.append(field_name)
                if field_name == "goal_context":
                    ctx.goal_truncated = True
                tokens = cap
            remaining -= tokens
        return ctx

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, len(text.split()) * 4 // 3)

    @staticmethod
    def _compact_text(text: str, max_chars: int) -> str:
        """Normalize whitespace and cap one evidence item without losing its start."""
        compact = " ".join(text.split())
        if len(compact) <= max_chars:
            return compact
        clipped = compact[: max_chars - 1].rsplit(" ", 1)[0]
        return clipped + "…"

    def _fit_lines(self, text: str, token_cap: int) -> str:
        """Budget context by complete lines so evidence bullets stay valid."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return ""
        kept: list[str] = []
        used = 0
        for line in lines:
            line_tokens = self._estimate_tokens(line)
            if used + line_tokens > token_cap:
                break
            kept.append(line)
            used += line_tokens
        if len(kept) < len(lines):
            if not kept:
                return self._compact_text(lines[0], max(32, int(token_cap * 3 / 2))) + "…"
            kept[-1] = kept[-1].rstrip("…") + "…"
        return "\n".join(kept)
