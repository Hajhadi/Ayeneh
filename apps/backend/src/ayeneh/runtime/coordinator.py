"""Runtime coordinator — top-level entry point for request processing."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

from ayeneh.runtime.composer import ResponseComposer, RuntimeResponse
from ayeneh.runtime.context import ExecutionContext, RuntimeState
from ayeneh.runtime.failure import FailureManager

if TYPE_CHECKING:
    from ayeneh.runtime.events import RuntimeEventPublisher
    from ayeneh.runtime.executor import ExecutionExecutor
    from ayeneh.runtime.persistence import RuntimePersistence
    from ayeneh.runtime.planner import ExecutionPlanner

logger = structlog.get_logger(__name__)


@dataclass
class RuntimeResult:
    """Complete result of a runtime execution."""

    response: RuntimeResponse
    context: ExecutionContext
    duration_ms: int = 0


class RuntimeCoordinator:
    """Orchestrates planning, execution, and response composition."""

    def __init__(
        self,
        planner: ExecutionPlanner,
        executor: ExecutionExecutor,
        composer: ResponseComposer,
        event_publisher: RuntimeEventPublisher,
        failure_manager: FailureManager | None = None,
        global_timeout_seconds: int = 60,
        persistence: RuntimePersistence | None = None,
        services: dict[str, Any] | None = None,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._composer = composer
        self._event_publisher = event_publisher
        self._failure_manager = failure_manager or FailureManager()
        self._global_timeout = global_timeout_seconds
        self._persistence = persistence
        self._services = services or {}

    async def process(self, request: dict[str, Any]) -> RuntimeResult:
        ctx = ExecutionContext(
            user_id=request.get("user_id", ""),
            conversation_id=request.get("conversation_id", ""),
            user_message=request.get("message", ""),
            metadata=request.get("metadata", {}),
            user_profile=request.get("user_profile", {}),
            conversation_history=request.get("conversation_history", []),
        )
        ctx.state = RuntimeState.PLANNING
        start = time.monotonic()

        await self._event_publisher.publish(ctx, "RuntimeStarted")

        try:
            plan = await asyncio.wait_for(
                self._planner.plan(ctx.user_message, {"user_id": ctx.user_id}),
                timeout=self._global_timeout,
            )
        except TimeoutError:
            logger.error("planner_timeout")
            ctx.state = RuntimeState.FAILED
            await self._event_publisher.publish(ctx, "RuntimeFailed", {"reason": "planner_timeout"})
            return RuntimeResult(response=RuntimeResponse(response_text=""), context=ctx, duration_ms=int((time.monotonic() - start) * 1000))

        await self._event_publisher.publish(ctx, "PlanCreated", {"plan_id": plan.plan_id, "strategy": plan.strategy, "steps": len(plan.steps)})

        ctx.state = RuntimeState.EXECUTING
        try:
            exec_result = await asyncio.wait_for(
                self._executor.execute(plan, ctx),
                timeout=self._global_timeout,
            )
        except TimeoutError:
            logger.error("executor_timeout")
            ctx.state = RuntimeState.TIMING_OUT
            ctx.cancel()
            await self._event_publisher.publish(ctx, "RuntimeFailed", {"reason": "executor_timeout"})
            return RuntimeResult(response=RuntimeResponse(response_text=""), context=ctx, duration_ms=int((time.monotonic() - start) * 1000))

        ctx.state = RuntimeState.COMPOSING
        response = self._composer.compose(ctx.agent_outputs, exec_result.get("skipped"))

        await self._persist_trace(ctx, plan, "completed")

        ctx.state = RuntimeState.RESPONDING
        await self._event_publisher.publish(ctx, "RuntimeCompleted", {
            "text_length": len(response.response_text),
            "total_outputs": len(ctx.agent_outputs),
        })

        duration = int((time.monotonic() - start) * 1000)
        logger.info("request_completed", duration_ms=duration, steps=len(plan.steps))
        return RuntimeResult(response=response, context=ctx, duration_ms=duration)

    async def _persist_trace(self, ctx: ExecutionContext, plan: Any, status: str) -> None:
        if not self._persistence:
            return
        try:
            plan_id = await self._persistence.save_execution_plan(ctx, plan, status)
            await self._persistence.save_agent_runs(plan_id, ctx)
            await self._persistence.process_agent_outputs(
                ctx,
                conversation_service=self._services.get("conversation"),
                memory_service=self._services.get("memory"),
                pattern_service=self._services.get("pattern"),
                reflection_service=self._services.get("reflection"),
                insight_service=self._services.get("insight"),
            )
        except Exception as exc:
            logger.error("persistence_failed", error=str(exc))
