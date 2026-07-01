"""Prompt service — loads, versions, and assembles prompts."""

from __future__ import annotations

from typing import Any


class PromptService:
    """Manages prompt templates and assembly."""

    async def get_active_template(self, task_type: str) -> dict[str, Any]:
        """Placeholder — will load the active prompt template for a task type."""
        return {"task_type": task_type, "version": "1.0.0", "content": ""}

    async def assemble(self, task_type: str, context: dict[str, Any]) -> dict[str, Any]:
        """Placeholder — will assemble a complete prompt context."""
        template = await self.get_active_template(task_type)
        return {
            "template": template,
            "context": context,
            "token_count": 0,
        }
