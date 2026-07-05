"""TraceRegistry — manages trace lifecycle per pipeline run.

Tracks begin/end of each stage, assembles RuntimeTrace at completion.
"""

from __future__ import annotations

import uuid
from typing import Any

from ayeneh.observability.trace_types import (
    ExecutionTiming,
    RuntimeTrace,
    TraceBase,
)


class TraceRegistry:
    """Manages trace lifecycle for a single pipeline execution.

    Usage:
        registry = TraceRegistry()
        eid = registry.begin_stage("query_understanding", request_id="req-1")
        # ... run pipeline ...
        registry.end_stage("query_understanding", QueryTrace(execution_id=eid, ...))
        runtime_trace = registry.build_runtime_trace(request_id="req-1")
    """

    def __init__(self) -> None:
        self._active: dict[str, str] = {}  # stage_name -> execution_id
        self._completed: dict[str, TraceBase] = {}  # stage_name -> trace
        self._timers: dict[str, float] = {}  # stage_name -> start monotonic

    def begin_stage(self, stage_name: str, request_id: str = "") -> str:
        """Begin tracking a stage. Returns execution_id for this stage."""
        import time

        execution_id = str(uuid.uuid4())
        self._active[stage_name] = execution_id
        self._timers[stage_name] = time.monotonic()
        return execution_id

    def end_stage(self, stage_name: str, trace: TraceBase) -> None:
        """Record the completed trace for a stage."""
        import time

        if stage_name in self._active:
            del self._active[stage_name]
        start = self._timers.pop(stage_name, None)
        self._completed[stage_name] = trace

    def get_trace(self, stage_name: str) -> TraceBase | None:
        return self._completed.get(stage_name)

    def get_all(self) -> dict[str, TraceBase]:
        return dict(self._completed)

    def build_runtime_trace(
        self,
        request_id: str = "",
        config_version: str = "0.0.0",
    ) -> RuntimeTrace:
        """Assemble all completed stage traces into a single RuntimeTrace."""
        from ayeneh.observability.trace_types import (
            QueryTrace,
            ReasoningTrace,
            ResponseTrace,
            RetrievalExecutionTrace,
            RetrievalPlanningTrace,
            RouterTrace,
        )

        def _as(cls: type, name: str) -> Any:
            t = self._completed.get(name)
            if t is not None and isinstance(t, cls):
                return t
            return None

        total_ms = 0.0
        for trace in self._completed.values():
            total_ms += trace.timing.wall_ms

        return RuntimeTrace(
            request_id=request_id,
            config_version=config_version,
            query_trace=_as(QueryTrace, "query_understanding"),
            retrieval_plan_trace=_as(RetrievalPlanningTrace, "retrieval_planning"),
            retrieval_exec_trace=_as(RetrievalExecutionTrace, "knowledge_retrieval"),
            reasoning_trace=_as(ReasoningTrace, "reasoning"),
            response_trace=_as(ResponseTrace, "response"),
            router_trace=_as(RouterTrace, "ai_router"),
            total_duration_ms=total_ms,
            stages_completed=len(self._completed),
            stages_failed=0,
        )

    def reset(self) -> None:
        self._active.clear()
        self._completed.clear()
        self._timers.clear()
