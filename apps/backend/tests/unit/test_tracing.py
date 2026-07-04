"""Tests for Metrics and Trace Recording per SPEC-01A §13, §36-38."""

import pytest
from ayeneh.runtime.tracing import (
    ExecutionEvent,
    StageTiming,
    ProvenanceRecord,
    TraceRecord,
    TraceRecorder,
)


# ---------------------------------------------------------------------------
# ExecutionEvent
# ---------------------------------------------------------------------------


class TestExecutionEvent:
    def test_creation(self):
        e = ExecutionEvent(stage_id="test", execution_state="running")
        assert e.stage_id == "test"
        assert e.execution_state == "running"
        assert e.event_id is not None

    def test_immutable(self):
        e = ExecutionEvent(stage_id="test", execution_state="running")
        with pytest.raises(AttributeError):
            e.stage_id = "changed"


# ---------------------------------------------------------------------------
# StageTiming
# ---------------------------------------------------------------------------


class TestStageTiming:
    def test_creation(self):
        t = StageTiming()
        assert t.total_duration_ms == 0.0

    def test_total_calculation(self):
        t = StageTiming(
            queue_duration_ms=1.0,
            execution_duration_ms=10.0,
            provider_duration_ms=5.0,
            serialization_duration_ms=0.5,
        )
        assert t.total_duration_ms == 16.5


# ---------------------------------------------------------------------------
# ProvenanceRecord
# ---------------------------------------------------------------------------


class TestProvenanceRecord:
    def test_creation(self):
        p = ProvenanceRecord(session_id="s1", producing_stage="test", producing_module="test_module")
        assert p.producing_stage == "test"
        assert p.producing_module == "test_module"
        assert p.session_id == "s1"
        assert p.record_id is not None

    def test_immutable(self):
        p = ProvenanceRecord(session_id="s1", producing_stage="test", producing_module="test_module")
        with pytest.raises(AttributeError):
            p.producing_stage = "changed"


# ---------------------------------------------------------------------------
# TraceRecord
# ---------------------------------------------------------------------------


class TestTraceRecord:
    def test_creation(self):
        t = TraceRecord(session_id="test-session")
        assert t.session_id == "test-session"
        assert len(t.events) == 0

    def test_counts_via_recorder(self):
        r = TraceRecorder()
        r.record_event("s1", "completed")
        r.record_event("s2", "failed")
        r.record_event("s3", "completed")
        trace = r.build_trace()
        assert trace.stages_completed == 2
        assert trace.stages_failed == 1


# ---------------------------------------------------------------------------
# TraceRecorder
# ---------------------------------------------------------------------------


class TestTraceRecorder:
    def test_creation(self):
        r = TraceRecorder(session_id="test")
        assert r._session_id == "test"

    def test_record_event(self):
        r = TraceRecorder(session_id="test")
        e = r.record_event("stage1", "completed", duration_ms=10.0)
        assert e.stage_id == "stage1"
        assert e.duration_ms == 10.0
        assert len(r.get_events()) == 1

    def test_record_provenance(self):
        r = TraceRecorder(session_id="test")
        p = r.record_provenance("stage1", "module1", engine_version="1.0.0")
        assert p.producing_stage == "stage1"
        assert p.session_id == "test"
        assert len(r.get_provenance()) == 1

    def test_build_trace(self):
        r = TraceRecorder(session_id="test")
        r.record_event("s1", "completed", duration_ms=10.0)
        r.record_event("s2", "failed", duration_ms=5.0)
        r.record_provenance("s1", "m1")
        trace = r.build_trace(total_duration_ms=15.0)
        assert trace.session_id == "test"
        assert trace.stages_completed == 1
        assert trace.stages_failed == 1
        assert trace.total_duration_ms == 15.0
        assert len(trace.events) == 2
        assert len(trace.provenance_records) == 1

    def test_record_event_with_artifacts(self):
        r = TraceRecorder()
        r.record_event("stage1", "completed", artifact_ids=["art1", "art2"])
        trace = r.build_trace()
        assert "art1" in trace.artifacts_produced
        assert "art2" in trace.artifacts_produced


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_execution_event_has_all_fields(self):
        e = ExecutionEvent(stage_id="test", execution_state="completed")
        assert hasattr(e, 'stage_id')
        assert hasattr(e, 'execution_state')
        assert hasattr(e, 'artifact_ids')
        assert hasattr(e, 'duration_ms')
        assert hasattr(e, 'provider')
        assert hasattr(e, 'cache_status')
        assert hasattr(e, 'success')
        assert hasattr(e, 'failure_category')
        assert hasattr(e, 'timestamp')
        assert hasattr(e, 'event_id')
