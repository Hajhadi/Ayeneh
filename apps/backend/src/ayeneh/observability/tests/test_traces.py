"""Tests for observability.trace_types and trace_registry."""

from __future__ import annotations

import pytest

from ayeneh.observability.trace_registry import TraceRegistry
from ayeneh.observability.trace_types import (
    ExecutionTiming,
    ExtractionTrace,
    ImportTrace,
    NormalizationTrace,
    ObservabilityTrace,
    QueryTrace,
    ReasoningTrace,
    ResponseTrace,
    RetrievalExecutionTrace,
    RetrievalPlanningTrace,
    RouterTrace,
    RuntimeTrace,
    TelemetryTrace,
    TraceBase,
)


# ---------------------------------------------------------------------------
# TraceBase
# ---------------------------------------------------------------------------


class TestTraceBase:
    def test_default_fields(self) -> None:
        t = TraceBase()
        assert t.request_id == ""
        assert t.execution_id == ""
        assert t.spec_version == "1.0.0"
        assert t.warnings == ()
        assert t.errors == ()
        assert t.timestamp is not None

    def test_frozen(self) -> None:
        t = TraceBase(request_id="req-1")
        with pytest.raises(AttributeError):
            t.request_id = "changed"  # type: ignore[misc]

    def test_with_custom_fields(self) -> None:
        t = TraceBase(
            request_id="r1",
            execution_id="e1",
            warnings=("w1",),
            errors=("e1",),
        )
        assert t.request_id == "r1"
        assert t.warnings == ("w1",)


# ---------------------------------------------------------------------------
# ExecutionTiming
# ---------------------------------------------------------------------------


class TestExecutionTiming:
    def test_defaults(self) -> None:
        t = ExecutionTiming()
        assert t.wall_ms == 0.0
        assert t.queue_ms == 0.0

    def test_frozen(self) -> None:
        t = ExecutionTiming(wall_ms=100.0)
        with pytest.raises(AttributeError):
            t.wall_ms = 200.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# All 10 Trace Types — frozen + constructible
# ---------------------------------------------------------------------------


class TestQueryTrace:
    def test_construction(self) -> None:
        t = QueryTrace(
            request_id="r1",
            execution_id="e1",
            raw_input="test query",
            language=("fa",),
            intent="definition",
            concepts=("Self", "Awareness"),
            entities=("ACT",),
            complexity_level="medium",
            capabilities=("concept_resolution",),
        )
        assert t.raw_input == "test query"
        assert t.language == ("fa",)
        assert len(t.concepts) == 2

    def test_frozen(self) -> None:
        t = QueryTrace()
        with pytest.raises(AttributeError):
            t.raw_input = "x"  # type: ignore[misc]


class TestRetrievalPlanningTrace:
    def test_construction(self) -> None:
        t = RetrievalPlanningTrace(
            request_id="r1",
            plan_id="p1",
            strategy="book_first",
            budget=20,
        )
        assert t.plan_id == "p1"
        assert t.strategy == "book_first"

    def test_frozen(self) -> None:
        t = RetrievalPlanningTrace()
        with pytest.raises(AttributeError):
            t.plan_id = "x"  # type: ignore[misc]


class TestRetrievalExecutionTrace:
    def test_construction(self) -> None:
        t = RetrievalExecutionTrace(
            retrieved_chunks=10,
            retrieved_profiles=3,
            cache_hits=2,
            cache_misses=1,
        )
        assert t.retrieved_chunks == 10
        assert t.cache_hits == 2


class TestReasoningTrace:
    def test_construction(self) -> None:
        t = ReasoningTrace(
            reasoning_mode="cross_book",
            conclusions_count=5,
            conflicts_count=1,
        )
        assert t.reasoning_mode == "cross_book"
        assert t.conclusions_count == 5


class TestResponseTrace:
    def test_construction(self) -> None:
        t = ResponseTrace(
            validation_passed=True,
            citation_count=3,
            response_length=500,
        )
        assert t.validation_passed is True
        assert t.citation_count == 3


class TestRouterTrace:
    def test_construction(self) -> None:
        t = RouterTrace(
            task_type="conversation",
            selected_provider="openrouter",
            selected_model="qwen3:8b",
            fallback_used=False,
        )
        assert t.selected_provider == "openrouter"


class TestImportTrace:
    def test_construction(self) -> None:
        t = ImportTrace(
            import_id="imp-1",
            file_path="/books/test.pdf",
            chunks_created=15,
            status="completed",
        )
        assert t.import_id == "imp-1"
        assert t.status == "completed"


class TestExtractionTrace:
    def test_construction(self) -> None:
        t = ExtractionTrace(
            source_text_length=5000,
            candidates_found=20,
            candidates_published=15,
        )
        assert t.candidates_found == 20


class TestNormalizationTrace:
    def test_construction(self) -> None:
        t = NormalizationTrace(
            input_count=20,
            resolved_count=18,
            unresolved_count=2,
        )
        assert t.resolved_count == 18


class TestObservabilityTrace:
    def test_construction(self) -> None:
        t = ObservabilityTrace(subsystems_monitored=5, trace_count=100)
        assert t.subsystems_monitored == 5


class TestTelemetryTrace:
    def test_construction(self) -> None:
        t = TelemetryTrace(metric_identifier="m1", telemetry_identifier="t1")
        assert t.metric_identifier == "m1"


# ---------------------------------------------------------------------------
# RuntimeTrace (composite)
# ---------------------------------------------------------------------------


class TestRuntimeTrace:
    def test_construction_empty(self) -> None:
        rt = RuntimeTrace(request_id="r1")
        assert rt.query_trace is None
        assert rt.stages_completed == 0

    def test_construction_with_traces(self) -> None:
        qt = QueryTrace(request_id="r1", raw_input="hello")
        rt = RuntimeTrace(
            request_id="r1",
            query_trace=qt,
            stages_completed=1,
            total_duration_ms=50.0,
        )
        assert rt.query_trace is not None
        assert rt.query_trace.raw_input == "hello"
        assert rt.total_duration_ms == 50.0

    def test_frozen(self) -> None:
        rt = RuntimeTrace()
        with pytest.raises(AttributeError):
            rt.request_id = "x"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TraceRegistry
# ---------------------------------------------------------------------------


class TestTraceRegistry:
    def test_begin_end(self) -> None:
        reg = TraceRegistry()
        eid = reg.begin_stage("query_understanding", request_id="r1")
        assert eid != ""
        assert "query_understanding" in reg._active

        trace = QueryTrace(execution_id=eid, raw_input="test")
        reg.end_stage("query_understanding", trace)
        assert "query_understanding" not in reg._active
        assert reg.get_trace("query_understanding") is trace

    def test_build_runtime_trace(self) -> None:
        reg = TraceRegistry()
        eid1 = reg.begin_stage("query_understanding", request_id="r1")
        reg.end_stage("query_understanding", QueryTrace(execution_id=eid1))

        eid2 = reg.begin_stage("retrieval_planning", request_id="r1")
        reg.end_stage("retrieval_planning", RetrievalPlanningTrace(execution_id=eid2, plan_id="p1"))

        eid3 = reg.begin_stage("reasoning", request_id="r1")
        reg.end_stage("reasoning", ReasoningTrace(execution_id=eid3, reasoning_mode="single_source"))

        rt = reg.build_runtime_trace(request_id="r1")
        assert rt.request_id == "r1"
        assert rt.query_trace is not None
        assert rt.retrieval_plan_trace is not None
        assert rt.reasoning_trace is not None
        assert rt.response_trace is None  # not registered
        assert rt.stages_completed == 3

    def test_reset(self) -> None:
        reg = TraceRegistry()
        reg.begin_stage("s1", request_id="r1")
        reg.end_stage("s1", TraceBase())
        reg.reset()
        assert reg.get_all() == {}

    def test_get_all(self) -> None:
        reg = TraceRegistry()
        reg.begin_stage("s1", request_id="r1")
        reg.end_stage("s1", TraceBase())
        reg.begin_stage("s2", request_id="r1")
        reg.end_stage("s2", TraceBase())
        all_traces = reg.get_all()
        assert len(all_traces) == 2
        assert "s1" in all_traces
        assert "s2" in all_traces
