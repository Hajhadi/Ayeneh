"""Tool calling framework — registration, execution, multi-call, recursion."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import structlog

from ayeneh.llm.types import (
    LLMConfig,
    LLMMessage,
    LLMResponse,
    ToolCall,
    ToolDefinition,
)

logger = structlog.get_logger(__name__)


@dataclass
class ToolResult:
    tool_call_id: str
    name: str
    output: str
    success: bool = True
    error: str | None = None


@dataclass
class ToolRegistry:
    """Registry of callable tools with their schemas."""

    _tools: dict[str, Callable[..., Awaitable[Any]]] = field(default_factory=dict)
    _schemas: dict[str, ToolDefinition] = field(default_factory=dict)

    def register(
        self,
        name: str,
        func: Callable[..., Awaitable[Any]],
        description: str,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        self._tools[name] = func
        self._schemas[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters or {
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    def get_definitions(self) -> list[ToolDefinition]:
        return list(self._schemas.values())

    def get_func(self, name: str) -> Callable[..., Awaitable[Any]] | None:
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        return name in self._tools


async def execute_tool_call(
    registry: ToolRegistry,
    tool_call: ToolCall,
) -> ToolResult:
    """Execute a single tool call and return the result."""
    func = registry.get_func(tool_call.name)
    if func is None:
        return ToolResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            output="",
            success=False,
            error=f"Tool '{tool_call.name}' not found",
        )

    try:
        args = tool_call.parse_arguments()
        result = await func(**args)
        output = json.dumps(result, default=str) if not isinstance(result, str) else result
        return ToolResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            output=output,
        )
    except Exception as exc:
        logger.warning("tool_execution_failed", tool=tool_call.name, error=str(exc))
        return ToolResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            output="",
            success=False,
            error=str(exc),
        )


async def execute_all_tool_calls(
    registry: ToolRegistry,
    tool_calls: list[ToolCall],
) -> list[ToolResult]:
    """Execute multiple tool calls concurrently."""
    tasks = [execute_tool_call(registry, tc) for tc in tool_calls]
    return await asyncio.gather(*tasks)


async def run_tool_loop(
    gateway: Any,
    messages: list[LLMMessage],
    registry: ToolRegistry,
    config: LLMConfig | None = None,
    max_iterations: int = 5,
) -> LLMResponse:
    """Run the tool calling loop: chat → tool calls → execute → append results → repeat."""
    current_messages = list(messages)
    cfg = config or LLMConfig()

    if registry.get_definitions() and not cfg.tools:
        cfg.tools = registry.get_definitions()

    for iteration in range(max_iterations):
        response = await gateway.chat(current_messages, cfg)

        if not response.has_tool_calls:
            return response

        tool_results = await execute_all_tool_calls(registry, response.tool_calls)

        current_messages.append(LLMMessage(
            role="assistant",
            content=response.content or None,
            tool_calls=response.tool_calls,
        ))

        for result in tool_results:
            current_messages.append(LLMMessage(
                role="tool",
                content=result.output if result.success else f"Error: {result.error}",
                tool_call_id=result.tool_call_id,
            ))

        logger.info("tool_loop_iteration", iteration=iteration, tools_called=len(tool_results))

    return await gateway.chat(current_messages, cfg)
