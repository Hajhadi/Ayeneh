"""Tests for COG observability — metrics and tracing."""

from __future__ import annotations

import time

from ayeneh.cog.observability import COGMetrics, COGMetricsCollector, COGTrace


# ---------------------------------------------------------------------------
# COGMetricsCollector tests
# ---------------------------------------------------------------------------


class TestCOGMetricsCollector:
    def test_record_execution(self):
        collector = COGMetricsCollector()
        collector.record_execution('engine_a', 100.0, objects_extracted=5)
        snapshot = collector.get_snapshot('engine_a')
        assert snapshot.executions == 1
        assert snapshot.total_duration_ms == 100.0
        assert snapshot.objects_extracted == 5

    def test_record_multiple_executions(self):
        collector = COGMetricsCollector()
        collector.record_execution('engine_a', 100.0, 3)
        collector.record_execution('engine_a', 200.0, 5)
        snapshot = collector.get_snapshot('engine_a')
        assert snapshot.executions == 2
        assert snapshot.total_duration_ms == 300.0
        assert snapshot.objects_extracted == 8
        assert snapshot.avg_duration_ms == 150.0

    def test_record_llm_call_success(self):
        collector = COGMetricsCollector()
        collector.record_execution('engine_a', 50.0)
        collector.record_llm_call('engine_a', success=True)
        snapshot = collector.get_snapshot('engine_a')
        assert snapshot.llm_calls == 1
        assert snapshot.llm_fallbacks == 0

    def test_record_llm_call_fallback(self):
        collector = COGMetricsCollector()
        collector.record_execution('engine_a', 50.0)
        collector.record_llm_call('engine_a', success=False)
        snapshot = collector.get_snapshot('engine_a')
        assert snapshot.llm_calls == 1
        assert snapshot.llm_fallbacks == 1

    def test_record_error(self):
        collector = COGMetricsCollector()
        collector.record_execution('engine_a', 50.0)
        collector.record_error('engine_a')
        snapshot = collector.get_snapshot('engine_a')
        assert snapshot.errors == 1

    def test_get_snapshot_empty_engine(self):
        collector = COGMetricsCollector()
        snapshot = collector.get_snapshot('nonexistent')
        assert snapshot.engine_name == 'nonexistent'
        assert snapshot.executions == 0
        assert snapshot.avg_duration_ms == 0.0

    def test_get_all_snapshots(self):
        collector = COGMetricsCollector()
        collector.record_execution('eng1', 10.0)
        collector.record_execution('eng2', 20.0)
        all_snapshots = collector.get_all_snapshots()
        assert len(all_snapshots) == 2
        assert 'eng1' in all_snapshots
        assert 'eng2' in all_snapshots

    def test_record_llm_call_unknown_engine(self):
        collector = COGMetricsCollector()
        # Should not raise
        collector.record_llm_call('unknown', success=True)
        collector.record_error('unknown')

    def test_multiple_llm_calls(self):
        collector = COGMetricsCollector()
        collector.record_execution('eng', 10.0)
        collector.record_llm_call('eng', success=True)
        collector.record_llm_call('eng', success=False)
        collector.record_llm_call('eng', success=True)
        snapshot = collector.get_snapshot('eng')
        assert snapshot.llm_calls == 3
        assert snapshot.llm_fallbacks == 1

    def test_multiple_errors(self):
        collector = COGMetricsCollector()
        collector.record_execution('eng', 10.0)
        collector.record_error('eng')
        collector.record_error('eng')
        snapshot = collector.get_snapshot('eng')
        assert snapshot.errors == 2


# ---------------------------------------------------------------------------
# COGMetrics dataclass tests
# ---------------------------------------------------------------------------


class TestCOGMetrics:
    def test_default_values(self):
        metrics = COGMetrics(engine_name='test')
        assert metrics.engine_name == 'test'
        assert metrics.executions == 0
        assert metrics.total_duration_ms == 0.0
        assert metrics.avg_duration_ms == 0.0
        assert metrics.objects_extracted == 0
        assert metrics.llm_calls == 0
        assert metrics.llm_fallbacks == 0
        assert metrics.errors == 0
        assert metrics.timestamp is not None

    def test_frozen(self):
        metrics = COGMetrics(engine_name='test')
        try:
            metrics.executions = 5  # type: ignore[misc]
            # If frozen, this should raise
            assert False, "Should have raised AttributeError"
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# COGTrace tests
# ---------------------------------------------------------------------------


class TestCOGTrace:
    def test_record_stage(self):
        trace = COGTrace('run-001')
        trace.record_stage('segmentation', 50.0, input_count=5, output_count=5)
        trace.record_stage('analysis', 100.0, input_count=5, output_count=10)
        result = trace.complete()
        assert result['run_id'] == 'run-001'
        assert result['stage_count'] == 2
        assert result['stages'][0]['stage'] == 'segmentation'
        assert result['stages'][0]['duration_ms'] == 50.0
        assert result['stages'][0]['input_count'] == 5
        assert result['stages'][0]['output_count'] == 5
        assert result['stages'][1]['stage'] == 'analysis'

    def test_complete_returns_total_duration(self):
        trace = COGTrace('run-002')
        trace.record_stage('step1', 10.0)
        result = trace.complete()
        assert 'total_duration_ms' in result
        assert result['total_duration_ms'] >= 0

    def test_empty_trace(self):
        trace = COGTrace('run-003')
        result = trace.complete()
        assert result['stage_count'] == 0
        assert result['stages'] == []

    def test_stages_have_timestamps(self):
        trace = COGTrace('run-004')
        trace.record_stage('s1', 1.0)
        result = trace.complete()
        assert 'timestamp' in result['stages'][0]
        assert isinstance(result['stages'][0]['timestamp'], str)
