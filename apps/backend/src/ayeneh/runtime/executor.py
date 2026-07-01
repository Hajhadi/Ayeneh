"""Execution executor — runs the plan produced by the planner."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from ayeneh.agents.base import AgentOutput, BaseAgent
from ayeneh.runtime.context import ExecutionContext, StepTrace
from ayeneh.runtime.failure import FailureManager
from ayeneh.runtime.planner import ErrorStrategy, ExecutionPlan, PlanStep, StepStatus

logger = structlog.get_logger(__name__)


class ExecutionExecutor:
    """Executes an ordered plan of agent steps with retries, timeout, and cancellation."""

    def __init__(
        self,
        agents: dict[str, BaseAgent],
        failure_manager: FailureManager | None = None,
    ) -> None:
        self._agents = agents
        self._failure_manager = failure_manager or FailureManager()

    async def execute(self, plan: ExecutionPlan, ctx: ExecutionContext) -> dict[str, Any]:
        """Run each step in the plan and collect outputs."""
        skipped: list[str] = []

        for step in plan.steps:
            if ctx.cancelled:
                logger.info("execution_cancelled", at_step=step.step_id)
                break

            if self._failure_manager.should_skip(step.agent_name):
                logger.info("agent_circuit_broken_skip", agent=step.agent_name)
                ctx.agent_outputs[step.step_id] = AgentOutput(status="skipped")
                skipped.append(step.step_id)
                ctx.record_event("AgentSkipped", {"step_id": step.step_id, "agent": step.agent_name, "reason": "circuit_broken"})
                continue

            if step.condition and not self._evaluate_condition(step.condition, ctx):
                ctx.agent_outputs[step.step_id] = AgentOutput(status="skipped")
                skipped.append(step.step_id)
                ctx.record_event("AgentSkipped", {"step_id": step.step_id, "agent": step.agent_name, "reason": "condition_false"})
                continue

            if not step.optional:
                for dep_id in step.dependencies:
                    dep_output = ctx.get_agent_output(dep_id)
                    if dep_output and dep_output.status == "failed":
                        ctx.agent_outputs[step.step_id] = AgentOutput(status="skipped")
                        skipped.append(step.step_id)
                        ctx.record_event("AgentSkipped", {"step_id": step.step_id, "agent": step.agent_name, "reason": f"dependency_{dep_id}_failed"})
                        break
                else:
                    await self._execute_step(step, ctx, skipped)
            else:
                await self._execute_step(step, ctx, skipped)

        return {
            "step_results": {k: v.data for k, v in ctx.agent_outputs.items()},
            "skipped": skipped,
        }

    async def _execute_step(self, step: PlanStep, ctx: ExecutionContext, skipped: list[str]) -> None:
        agent = self._agents.get(step.agent_name)
        if agent is None:
            ctx.agent_outputs[step.step_id] = AgentOutput(status="failed", data={"error": f"agent '{step.agent_name}' not found"})
            ctx.record_error(step.step_id, f"agent '{step.agent_name}' not found")
            return

        trace = StepTrace(step_id=step.step_id, agent_name=step.agent_name)
        ctx.step_traces.append(trace)

        ctx.record_event("AgentStarted", {"step_id": step.step_id, "agent": step.agent_name})
        trace.status = StepStatus.RUNNING

        agent_input = self._build_agent_input(step, ctx)

        for attempt in range(step.max_retries + 1):
            if ctx.cancelled:
                trace.status = StepStatus.SKIPPED
                return

            trace.started_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
            try:
                output = await asyncio.wait_for(
                    agent.execute(agent_input),
                    timeout=step.timeout_seconds,
                )
                ctx.agent_outputs[step.step_id] = output
                trace.status = StepStatus.COMPLETED
                trace.retry_count = attempt
                self._failure_manager.record_success(step.agent_name)
                ctx.record_event("AgentCompleted", {"step_id": step.step_id, "status": output.status, "retry_count": attempt})
                return
            except TimeoutError:
                trace.error = "timeout"
                logger.warning("step_timeout", step_id=step.step_id, timeout=step.timeout_seconds)
            except Exception as exc:
                trace.error = str(exc)
                logger.exception("step_failed", step_id=step.step_id, attempt=attempt)

            trace.retry_count = attempt + 1
            should_retry, _action = await self._failure_manager.handle_step_failure(step, Exception(trace.error or "unknown"), attempt)
            if not should_retry:
                break

        trace.status = StepStatus.FAILED
        ctx.agent_outputs[step.step_id] = AgentOutput(status="failed", data={"error": trace.error})
        ctx.record_error(step.step_id, trace.error or "execution failed")
        ctx.record_event("AgentFailed", {"step_id": step.step_id, "error": trace.error})
        if step.error_strategy in (ErrorStrategy.SKIP, ErrorStrategy.DEGRADE):
            skipped.append(step.step_id)

    def _build_agent_input(self, step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
        agent_input: dict[str, Any] = {"request_id": ctx.request_id, "user_id": ctx.user_id, "user_message": ctx.user_message}

        for key, binding in step.input_binding.items():
            if binding.startswith("context."):
                field_name = binding[len("context."):]
                agent_input[key] = getattr(ctx, field_name, ctx.accumulated.get(field_name))
            elif binding.startswith("output."):
                ref_step = binding[len("output."):]
                ref_output = ctx.get_agent_output(ref_step)
                agent_input[key] = ref_output.data if ref_output else {}
            else:
                agent_input[key] = binding

        agent_input.update(ctx.accumulated)
        return agent_input

    @staticmethod
    def _evaluate_condition(condition: str, ctx: ExecutionContext) -> bool:
        if condition.startswith("has_output:"):
            step_id = condition[len("has_output:"):]
            return ctx.has_output(step_id)
        if condition == "has_books":
            return ctx.accumulated.get("book_count", 0) > 0
        if condition == "has_memories":
            return ctx.accumulated.get("memory_count", 0) > 0
        return True
