"""Runtime persistence — saves execution trace, agent runs, and agent outputs."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from ayeneh.infrastructure.persistence.models.agent_run import AgentRunModel
from ayeneh.infrastructure.persistence.models.execution_plan import ExecutionPlanModel

if TYPE_CHECKING:
    from ayeneh.runtime.context import ExecutionContext

logger = structlog.get_logger(__name__)


class RuntimePersistence:
    """Persists execution plans, agent runs, and processes agent outputs.

    Called by the RuntimeCoordinator after each request to produce
    a complete execution trace in the database.
    """

    def __init__(self, uow_factory: Any) -> None:
        self._uow_factory = uow_factory

    async def save_execution_plan(
        self,
        ctx: ExecutionContext,
        plan: Any,
        status: str = "completed",
    ) -> str:
        now = datetime.now(UTC)
        plan_id = uuid.uuid4()

        steps_data = []
        for step in plan.steps:
            steps_data.append({
                "step_id": step.step_id,
                "agent_name": step.agent_name,
                "input_binding": step.input_binding,
                "error_strategy": step.error_strategy.value
                if hasattr(step.error_strategy, "value")
                else str(step.error_strategy),
                "timeout_seconds": step.timeout_seconds,
                "optional": step.optional,
                "dependencies": step.dependencies,
            })

        async with self._uow_factory() as uow:
            ep = ExecutionPlanModel(
                id=plan_id,
                request_id=uuid.UUID(ctx.request_id) if ctx.request_id else uuid.uuid4(),
                user_id=uuid.UUID(ctx.user_id) if ctx.user_id else uuid.uuid4(),
                strategy=plan.strategy,
                confidence=plan.confidence,
                steps=steps_data,
                status=status,
                created_at=now,
                completed_at=now,
            )
            await uow.execution_plans.create(ep)
            await uow.commit()
            logger.info(
                "execution_plan_saved",
                plan_id=str(plan_id),
                strategy=plan.strategy,
                steps=len(steps_data),
            )
            return str(plan_id)

    async def save_agent_runs(
        self,
        plan_id: str,
        ctx: ExecutionContext,
    ) -> int:
        now = datetime.now(UTC)
        saved = 0
        async with self._uow_factory() as uow:
            for trace in ctx.step_traces:
                output = ctx.agent_outputs.get(trace.step_id)
                input_summary = json.dumps(
                    {"user_message": ctx.user_message[:200]},
                    default=str,
                )
                output_summary = ""
                if output and output.data:
                    if output.data.get("response_text"):
                        output_summary = output.data["response_text"][:500]
                    elif output.data.get("error"):
                        output_summary = f"ERROR: {output.data['error']}"

                duration_ms = None
                if trace.started_at:
                    elapsed = now - trace.started_at
                    duration_ms = int(elapsed.total_seconds() * 1000)

                run = AgentRunModel(
                    id=uuid.uuid4(),
                    plan_id=uuid.UUID(plan_id),
                    step_id=trace.step_id,
                    agent_name=trace.agent_name,
                    status=trace.status.value
                    if hasattr(trace.status, "value")
                    else str(trace.status),
                    input_summary=input_summary,
                    output_summary=output_summary,
                    started_at=trace.started_at,
                    completed_at=now,
                    duration_ms=duration_ms,
                    error_message=trace.error,
                    retry_count=trace.retry_count,
                    created_at=now,
                )
                await uow.agent_runs.create(run)
                saved += 1
            await uow.commit()
        logger.info("agent_runs_saved", plan_id=plan_id, count=saved)
        return saved

    async def process_agent_outputs(
        self,
        ctx: ExecutionContext,
        conversation_service: Any | None = None,
        memory_service: Any | None = None,
        pattern_service: Any | None = None,
        reflection_service: Any | None = None,
        insight_service: Any | None = None,
    ) -> dict[str, int]:
        counts: dict[str, int] = {"messages": 0, "memories": 0, "patterns": 0, "reflections": 0, "observations": 0}

        for step_id, output in ctx.agent_outputs.items():
            if output.status != "success":
                continue

            data = output.data

            if conversation_service and data.get("response_text"):
                try:
                    await conversation_service.create_message(
                        user_id=ctx.user_id,
                        conversation_id=ctx.conversation_id,
                        content=data["response_text"],
                        role="assistant",
                    )
                    counts["messages"] += 1
                except Exception as exc:
                    logger.warning("failed_to_save_conversation_response", error=str(exc))

            if memory_service and data.get("memories"):
                for mem_data in data["memories"]:
                    try:
                        if isinstance(mem_data, dict) and mem_data.get("content"):
                            from ayeneh.application.services.memory import MemoryCreate, MemoryType
                            mem_type = MemoryType(mem_data.get("type", "episodic"))
                            await memory_service.store(MemoryCreate(
                                user_id=uuid.UUID(ctx.user_id),
                                type=mem_type,
                                content=mem_data["content"],
                                confidence=mem_data.get("confidence", 0.5),
                            ))
                            counts["memories"] += 1
                    except Exception as exc:
                        logger.warning("failed_to_save_memory", error=str(exc))

            if pattern_service and data.get("patterns"):
                for pat_data in data["patterns"]:
                    try:
                        if isinstance(pat_data, dict) and pat_data.get("description"):
                            await pattern_service.create_pattern(
                                user_id=ctx.user_id,
                                description=pat_data["description"],
                                strength=pat_data.get("strength", 0.5),
                                evidence_ids=pat_data.get("evidence_ids"),
                            )
                            counts["patterns"] += 1
                    except Exception as exc:
                        logger.warning("failed_to_save_pattern", error=str(exc))

            if reflection_service and data.get("reflection"):
                try:
                    ref = data["reflection"]
                    if isinstance(ref, dict) and ref.get("narrative"):
                        await reflection_service.create_reflection(
                            user_id=ctx.user_id,
                            title=ref.get("title", "Auto-generated Reflection"),
                            narrative=ref["narrative"],
                            period_start=datetime.now(UTC),
                            period_end=datetime.now(UTC),
                        )
                        counts["reflections"] += 1
                except Exception as exc:
                    logger.warning("failed_to_save_reflection", error=str(exc))

            if insight_service and data.get("observations"):
                for obs_data in data["observations"]:
                    try:
                        if isinstance(obs_data, dict) and obs_data.get("content"):
                            await insight_service.create_observation(
                                user_id=ctx.user_id,
                                content=obs_data["content"],
                                source_agent=obs_data.get("source", step_id),
                            )
                            counts["observations"] += 1
                    except Exception as exc:
                        logger.warning("failed_to_save_observation", error=str(exc))

        logger.info("agent_outputs_processed", **counts)
        return counts
