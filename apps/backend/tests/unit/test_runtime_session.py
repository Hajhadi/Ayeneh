"""Tests for RuntimeSession and RuntimeContext per SPEC-01A."""

import pytest
from ayeneh.runtime.session import (
    RuntimeSession,
    RuntimeContext,
    RuntimeState,
    RuntimeMetrics,
    StageMetrics,
    ArtifactRef,
)


# ---------------------------------------------------------------------------
# RuntimeSession
# ---------------------------------------------------------------------------


class TestRuntimeSession:
    def test_creates_with_unique_id(self):
        s1 = RuntimeSession()
        s2 = RuntimeSession()
        assert s1.session_id != s2.session_id

    def test_has_request_id(self):
        s = RuntimeSession()
        assert s.request_id is not None
        assert len(s.request_id) > 0

    def test_has_timestamp(self):
        s = RuntimeSession()
        assert s.timestamp is not None

    def test_immutable(self):
        s = RuntimeSession()
        with pytest.raises(AttributeError):
            s.session_id = "new-id"

    def test_optional_fields(self):
        s = RuntimeSession()
        assert s.user_context_id is None
        assert s.conversation_id is None

    def test_version_fields(self):
        s = RuntimeSession()
        assert s.knowledge_version == "0.0.0"
        assert s.graph_version == "0.0.0"
        assert s.policy_version == "0.0.0"


# ---------------------------------------------------------------------------
# RuntimeContext
# ---------------------------------------------------------------------------


class TestRuntimeContext:
    def test_creates_with_session(self):
        ctx = RuntimeContext()
        assert ctx.session is not None
        assert isinstance(ctx.session, RuntimeSession)

    def test_register_artifact(self):
        ctx = RuntimeContext()
        ref = ctx.register_artifact("QueryAnalysis", "query_understanding")
        assert ref.artifact_type == "QueryAnalysis"
        assert ref.owner == "query_understanding"
        assert ctx.get_artifact("QueryAnalysis") is ref

    def test_get_nonexistent_artifact(self):
        ctx = RuntimeContext()
        assert ctx.get_artifact("NonExistent") is None

    def test_artifacts_dict(self):
        ctx = RuntimeContext()
        ctx.register_artifact("QueryAnalysis", "query_understanding")
        ctx.register_artifact("RetrievalPlan", "retrieval_planning")
        assert len(ctx.artifacts) == 2

    def test_user_message(self):
        ctx = RuntimeContext(user_message="test query")
        assert ctx.user_message == "test query"

    def test_stage_data_fields(self):
        ctx = RuntimeContext()
        assert ctx.query_analysis is None
        assert ctx.retrieval_plan is None
        assert ctx.retrieved_knowledge is None
        assert ctx.integrated_knowledge is None
        assert ctx.reasoning_result is None
        assert ctx.interpretation_result is None
        assert ctx.safety_report is None
        assert ctx.response_draft is None
        assert ctx.final_response is None


# ---------------------------------------------------------------------------
# ArtifactRef
# ---------------------------------------------------------------------------


class TestArtifactRef:
    def test_creation(self):
        ref = ArtifactRef(artifact_type="QueryAnalysis", owner="query_understanding")
        assert ref.artifact_type == "QueryAnalysis"
        assert ref.owner == "query_understanding"
        assert ref.version == "1.0.0"
        assert ref.created_at is not None

    def test_immutable(self):
        ref = ArtifactRef(artifact_type="QueryAnalysis", owner="query_understanding")
        with pytest.raises(AttributeError):
            ref.artifact_type = "Other"


# ---------------------------------------------------------------------------
# RuntimeState
# ---------------------------------------------------------------------------


class TestRuntimeState:
    def test_all_states_defined(self):
        assert RuntimeState.NEW == "new"
        assert RuntimeState.INITIALIZING == "initializing"
        assert RuntimeState.READY == "ready"
        assert RuntimeState.RUNNING == "running"
        assert RuntimeState.RETRIEVING == "retrieving"
        assert RuntimeState.REASONING == "reasoning"
        assert RuntimeState.INTERPRETING == "interpreting"
        assert RuntimeState.VALIDATING == "validating"
        assert RuntimeState.GENERATING == "generating"
        assert RuntimeState.STREAMING == "streaming"
        assert RuntimeState.COMPLETED == "completed"
        assert RuntimeState.FAILED == "failed"


# ---------------------------------------------------------------------------
# StageMetrics
# ---------------------------------------------------------------------------


class TestStageMetrics:
    def test_creation(self):
        m = StageMetrics(stage_name="test_stage")
        assert m.stage_name == "test_stage"
        assert m.success is True

    def test_complete(self):
        m = StageMetrics(stage_name="test_stage")
        m.complete()
        assert m.end_time is not None
        assert m.duration_ms >= 0

    def test_fail(self):
        m = StageMetrics(stage_name="test_stage")
        m.fail("infrastructure")
        assert m.success is False
        assert m.failure_category == "infrastructure"
        assert m.end_time is not None


# ---------------------------------------------------------------------------
# RuntimeMetrics
# ---------------------------------------------------------------------------


class TestRuntimeMetrics:
    def test_creation(self):
        m = RuntimeMetrics(session_id="test-session")
        assert m.session_id == "test-session"
        assert len(m.stages) == 0

    def test_add_stage(self):
        m = RuntimeMetrics()
        s = StageMetrics(stage_name="stage1")
        s.complete()
        m.add_stage(s)
        assert len(m.stages) == 1

    def test_finalize(self):
        m = RuntimeMetrics()
        s1 = StageMetrics(stage_name="stage1")
        s1.complete()
        s2 = StageMetrics(stage_name="stage2")
        s2.complete()
        m.add_stage(s1)
        m.add_stage(s2)
        m.finalize()
        assert m.total_duration_ms >= 0


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_session_has_all_required_fields(self):
        s = RuntimeSession()
        assert hasattr(s, 'session_id')
        assert hasattr(s, 'request_id')
        assert hasattr(s, 'timestamp')
        assert hasattr(s, 'user_context_id')
        assert hasattr(s, 'conversation_id')
        assert hasattr(s, 'product_profile')
        assert hasattr(s, 'active_policy')
        assert hasattr(s, 'selected_providers')
        assert hasattr(s, 'knowledge_version')
        assert hasattr(s, 'graph_version')
        assert hasattr(s, 'policy_version')
        assert hasattr(s, 'provider_version')
        assert hasattr(s, 'interpretation_version')
        assert hasattr(s, 'reasoning_version')
        assert hasattr(s, 'router_version')

    def test_context_has_all_required_fields(self):
        ctx = RuntimeContext()
        assert hasattr(ctx, 'session')
        assert hasattr(ctx, 'user_message')
        assert hasattr(ctx, 'conversation_history')
        assert hasattr(ctx, 'artifacts')
        assert hasattr(ctx, 'query_analysis')
        assert hasattr(ctx, 'retrieval_plan')
        assert hasattr(ctx, 'retrieved_knowledge')
        assert hasattr(ctx, 'integrated_knowledge')
        assert hasattr(ctx, 'reasoning_result')
        assert hasattr(ctx, 'interpretation_result')
        assert hasattr(ctx, 'safety_report')
        assert hasattr(ctx, 'response_draft')
        assert hasattr(ctx, 'final_response')
