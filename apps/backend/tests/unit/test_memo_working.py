"""Tests for the working memory subsystem (MEM-04)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from ayeneh.memo.working.types import (
    COMPRESSION_STRATEGIES,
    CONTEXT_WINDOWS,
    OPEN_LOOP_CATEGORIES,
    WORKING_MEMORY_SOURCES,
    CompressionResult,
    ContextSwitch,
    ContextWindow,
    ExplainabilityMetadata,
    OpenLoop,
    WorkingMemoryObject,
    WorkingMemorySnapshot,
)
from ayeneh.memo.working.engine import WorkingMemoryEngine
from ayeneh.memo.working.context_switching import ContextSwitchingManager
from ayeneh.memo.working.compression import WorkingMemoryCompressor


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestWorkingMemoryObject:
    def test_creation(self) -> None:
        obj = WorkingMemoryObject(
            identifier='wm_1',
            source_memory='episodic_memory',
            activation_reason='test',
        )
        assert obj.identifier == 'wm_1'
        assert obj.source_memory == 'episodic_memory'

    def test_effective_score(self) -> None:
        obj = WorkingMemoryObject(
            identifier='wm_1',
            source_memory='test',
            activation_reason='test',
            activation_score=0.8,
            priority_score=0.6,
        )
        expected = 0.8 * 0.6 + 0.6 * 0.4
        assert abs(obj.effective_score - expected) < 1e-6

    def test_is_expired(self) -> None:
        obj = WorkingMemoryObject(
            identifier='wm_1',
            source_memory='test',
            activation_reason='test',
            estimated_lifetime=0.0,
        )
        assert obj.is_expired

    def test_not_expired(self) -> None:
        obj = WorkingMemoryObject(
            identifier='wm_1',
            source_memory='test',
            activation_reason='test',
            estimated_lifetime=100.0,
        )
        assert not obj.is_expired

    def test_frozen(self) -> None:
        obj = WorkingMemoryObject(
            identifier='wm_1',
            source_memory='test',
            activation_reason='test',
        )
        with pytest.raises(AttributeError):
            obj.identifier = 'wm_2'


class TestContextWindow:
    def test_creation(self) -> None:
        window = ContextWindow(window_type='immediate', window_id='cw_1')
        assert window.window_type == 'immediate'
        assert window.window_id == 'cw_1'

    def test_utilization_empty(self) -> None:
        window = ContextWindow(window_type='immediate', window_id='cw_1')
        assert window.utilization == 0.0

    def test_utilization_partial(self) -> None:
        obj = WorkingMemoryObject(
            identifier='wm_1', source_memory='test', activation_reason='test'
        )
        window = ContextWindow(
            window_type='immediate',
            window_id='cw_1',
            activated_objects=(obj,),
            max_capacity=10,
        )
        assert abs(window.utilization - 0.1) < 1e-6

    def test_is_full(self) -> None:
        obj = WorkingMemoryObject(
            identifier='wm_1', source_memory='test', activation_reason='test'
        )
        window = ContextWindow(
            window_type='immediate',
            window_id='cw_1',
            activated_objects=(obj,),
            max_capacity=1,
        )
        assert window.is_full

    def test_available_capacity(self) -> None:
        obj = WorkingMemoryObject(
            identifier='wm_1', source_memory='test', activation_reason='test'
        )
        window = ContextWindow(
            window_type='immediate',
            window_id='cw_1',
            activated_objects=(obj,),
            max_capacity=5,
        )
        assert window.available_capacity == 4


class TestContextSwitch:
    def test_creation(self) -> None:
        switch = ContextSwitch(reason='test_switch')
        assert switch.reason == 'test_switch'
        assert len(switch.previous_state) == 0
        assert len(switch.new_activation_set) == 0

    def test_with_objects(self) -> None:
        obj = WorkingMemoryObject(
            identifier='wm_1', source_memory='test', activation_reason='test'
        )
        switch = ContextSwitch(
            previous_state=(obj,),
            reason='switch',
            new_activation_set=(obj,),
        )
        assert len(switch.previous_state) == 1
        assert len(switch.new_activation_set) == 1


class TestOpenLoop:
    def test_creation(self) -> None:
        loop = OpenLoop(
            loop_id='ol_1',
            category='unanswered_questions',
            description='What is X?',
        )
        assert loop.loop_id == 'ol_1'
        assert not loop.resolved

    def test_age_seconds(self) -> None:
        loop = OpenLoop(
            loop_id='ol_1',
            category='unanswered_questions',
            description='test',
            created_at=datetime.now(UTC) - timedelta(seconds=10),
        )
        assert loop.age_seconds >= 9.0


class TestCompressionResult:
    def test_compression_ratio(self) -> None:
        result = CompressionResult(
            original_count=10,
            compressed_count=5,
            strategy_used='grouping',
        )
        assert abs(result.compression_ratio - 0.5) < 1e-6

    def test_compression_ratio_empty(self) -> None:
        result = CompressionResult(
            original_count=0,
            compressed_count=0,
            strategy_used='none',
        )
        assert result.compression_ratio == 0.0


class TestWorkingMemorySnapshot:
    def test_total_items(self) -> None:
        obj = WorkingMemoryObject(
            identifier='wm_1', source_memory='test', activation_reason='test'
        )
        snap = WorkingMemorySnapshot(
            snapshot_id='snap_1',
            active_objects=(obj, obj),
        )
        assert snap.total_items == 2

    def test_unresolved_loops(self) -> None:
        loop1 = OpenLoop(loop_id='ol_1', category='test', description='a')
        loop2 = OpenLoop(
            loop_id='ol_2', category='test', description='b', resolved=True
        )
        snap = WorkingMemorySnapshot(
            snapshot_id='snap_1',
            open_loops=(loop1, loop2),
        )
        assert snap.unresolved_loops == 1


class TestExplainabilityMetadata:
    def test_creation(self) -> None:
        meta = ExplainabilityMetadata(
            activation_reasons=('reason1',),
            explanation_text='because',
        )
        assert meta.activation_reasons == ('reason1',)
        assert meta.explanation_text == 'because'


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------


class TestConstants:
    def test_working_memory_sources(self) -> None:
        assert 'current_conversation' in WORKING_MEMORY_SOURCES
        assert 'episodic_memory' in WORKING_MEMORY_SOURCES
        assert 'goals' in WORKING_MEMORY_SOURCES
        assert len(WORKING_MEMORY_SOURCES) == 13

    def test_context_windows(self) -> None:
        assert 'immediate' in CONTEXT_WINDOWS
        assert 'longitudinal' in CONTEXT_WINDOWS
        assert len(CONTEXT_WINDOWS) == 5

    def test_compression_strategies(self) -> None:
        assert 'grouping' in COMPRESSION_STRATEGIES
        assert len(COMPRESSION_STRATEGIES) == 4

    def test_open_loop_categories(self) -> None:
        assert 'unanswered_questions' in OPEN_LOOP_CATEGORIES
        assert len(OPEN_LOOP_CATEGORIES) == 6


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestWorkingMemoryEngine:
    def test_creation(self) -> None:
        engine = WorkingMemoryEngine()
        assert engine._max_capacity == 30

    def test_activate(self) -> None:
        engine = WorkingMemoryEngine()
        obj = engine.activate('mem_1', 'test_reason')
        assert obj.identifier.startswith('wm_')
        assert obj.source_memory == 'mem_1'
        assert len(engine.get_active_objects()) == 1

    def test_activate_capacity_enforcement(self) -> None:
        engine = WorkingMemoryEngine(max_capacity=3)
        for i in range(5):
            engine.activate(f'mem_{i}', 'test', activation_score=float(i) / 5)
        assert len(engine.get_active_objects()) == 3

    def test_deactivate(self) -> None:
        engine = WorkingMemoryEngine()
        obj = engine.activate('mem_1', 'test')
        assert engine.deactivate(obj.identifier)
        assert len(engine.get_active_objects()) == 0

    def test_deactivate_nonexistent(self) -> None:
        engine = WorkingMemoryEngine()
        assert not engine.deactivate('nonexistent')

    def test_register_open_loop(self) -> None:
        engine = WorkingMemoryEngine()
        loop = engine.register_open_loop('unanswered_questions', 'What?')
        assert loop.loop_id.startswith('ol_')
        assert len(engine.get_open_loops()) == 1

    def test_resolve_open_loop(self) -> None:
        engine = WorkingMemoryEngine()
        loop = engine.register_open_loop('unanswered_questions', 'What?')
        assert engine.resolve_open_loop(loop.loop_id, 'res_mem')
        assert len(engine.get_open_loops()) == 0

    def test_resolve_nonexistent_loop(self) -> None:
        engine = WorkingMemoryEngine()
        assert not engine.resolve_open_loop('nonexistent', '')

    def test_decay_all(self) -> None:
        engine = WorkingMemoryEngine(decay_rate=0.5)
        engine.activate('mem_1', 'test', estimated_lifetime=0.4)
        expired = engine.decay_all()
        assert expired == 1

    def test_decay_reduces_lifetime(self) -> None:
        engine = WorkingMemoryEngine(decay_rate=0.1)
        obj = engine.activate('mem_1', 'test', estimated_lifetime=1.0)
        engine.decay_all()
        active = engine.get_active_objects()
        assert len(active) == 1
        assert active[0].estimated_lifetime < 1.0

    def test_take_snapshot(self) -> None:
        engine = WorkingMemoryEngine()
        engine.activate('mem_1', 'test')
        snap = engine.take_snapshot()
        assert snap.total_items == 1
        assert snap.snapshot_id.startswith('snap_')

    def test_create_context_window(self) -> None:
        engine = WorkingMemoryEngine()
        window = engine.create_context_window('immediate')
        assert window.window_type == 'immediate'

    def test_run_pipeline_basic(self) -> None:
        engine = WorkingMemoryEngine()
        result = engine.run_pipeline('Hello, what do you remember?')
        assert result.snapshot is not None
        assert isinstance(result.metadata, dict)

    def test_run_pipeline_with_retrieved(self) -> None:
        engine = WorkingMemoryEngine()
        retrieved = [
            {'id': 'mem_1', 'source': 'episodic_memory', 'score': 0.8, 'reason': 'test'},
            {'id': 'mem_2', 'source': 'semantic', 'score': 0.6, 'reason': 'test2'},
        ]
        result = engine.run_pipeline(
            'Tell me about my goals',
            retrieved_memories=retrieved,
        )
        assert result.snapshot is not None

    def test_run_pipeline_intent_analysis(self) -> None:
        engine = WorkingMemoryEngine()
        result = engine.run_pipeline('Why did I decide to learn Python?')
        assert result.snapshot is not None

    def test_run_pipeline_plan_intent(self) -> None:
        engine = WorkingMemoryEngine()
        result = engine.run_pipeline('What should I do next?')
        assert result.snapshot is not None

    def test_run_pipeline_compare_intent(self) -> None:
        engine = WorkingMemoryEngine()
        result = engine.run_pipeline('Compare my approaches')
        assert result.snapshot is not None


# ---------------------------------------------------------------------------
# Context switching tests
# ---------------------------------------------------------------------------


class TestContextSwitchingManager:
    def test_creation(self) -> None:
        mgr = ContextSwitchingManager()
        assert mgr.get_active_window() is None
        assert not mgr.has_previous_context()

    def test_switch_context(self) -> None:
        mgr = ContextSwitchingManager()
        window = ContextWindow(window_type='immediate', window_id='cw_1')
        switch = mgr.switch_context(window, reason='initial')
        assert switch.reason == 'initial'
        assert mgr.get_active_window() is not None

    def test_switch_preserves_residual(self) -> None:
        mgr = ContextSwitchingManager()
        window1 = ContextWindow(window_type='immediate', window_id='cw_1')
        window2 = ContextWindow(window_type='session', window_id='cw_2')
        mgr.switch_context(window1, reason='start')
        mgr.switch_context(
            window2,
            reason='switch',
            residual_ids=('dep_1', 'dep_2'),
        )
        deps = mgr.get_residual_dependencies('cw_2')
        assert 'dep_1' in deps
        assert 'dep_2' in deps

    def test_switch_preserves_hypotheses(self) -> None:
        mgr = ContextSwitchingManager()
        window = ContextWindow(window_type='session', window_id='cw_1')
        mgr.switch_context(window, hypotheses=('h1', 'h2'))
        hyps = mgr.get_open_hypotheses('cw_1')
        assert 'h1' in hyps

    def test_pop_context(self) -> None:
        mgr = ContextSwitchingManager()
        window1 = ContextWindow(window_type='immediate', window_id='cw_1')
        window2 = ContextWindow(window_type='session', window_id='cw_2')
        mgr.switch_context(window1)
        mgr.switch_context(window2)
        assert mgr.get_window_stack_depth() == 1
        switch = mgr.pop_context()
        assert switch is not None
        active = mgr.get_active_window()
        assert active is not None and active.window_id == 'cw_1'

    def test_pop_empty_stack(self) -> None:
        mgr = ContextSwitchingManager()
        assert mgr.pop_context() is None

    def test_clear_hypotheses(self) -> None:
        mgr = ContextSwitchingManager()
        window = ContextWindow(window_type='session', window_id='cw_1')
        mgr.switch_context(window, hypotheses=('h1',))
        mgr.clear_hypotheses('cw_1')
        assert len(mgr.get_open_hypotheses('cw_1')) == 0

    def test_switch_history(self) -> None:
        mgr = ContextSwitchingManager()
        window = ContextWindow(window_type='immediate', window_id='cw_1')
        mgr.switch_context(window)
        mgr.switch_context(window)
        assert len(mgr.get_switch_history()) == 2


# ---------------------------------------------------------------------------
# Compression tests
# ---------------------------------------------------------------------------


class TestWorkingMemoryCompressor:
    def test_compress_empty(self) -> None:
        compressor = WorkingMemoryCompressor()
        result, metrics = compressor.compress([], target_size=5)
        assert len(result) == 0
        assert metrics.compressed_count == 0

    def test_compress_within_target(self) -> None:
        compressor = WorkingMemoryCompressor()
        objs = [
            WorkingMemoryObject(
                identifier=f'wm_{i}', source_memory='test', activation_reason='test'
            )
            for i in range(3)
        ]
        result, metrics = compressor.compress(objs, target_size=5)
        assert len(result) == 3
        assert metrics.original_count == 3

    def test_group_compression(self) -> None:
        compressor = WorkingMemoryCompressor()
        objs = [
            WorkingMemoryObject(
                identifier=f'wm_{i}',
                source_memory='test',
                activation_reason='test',
                associated_episode='ep_1' if i < 3 else 'ep_2',
                activation_score=float(i) / 10,
            )
            for i in range(6)
        ]
        result, metrics = compressor.compress(objs, target_size=2, strategy='grouping')
        assert len(result) <= 4  # 2 groups + 0 ungrouped (all grouped)
        assert metrics.strategy_used == 'grouping'

    def test_semantic_compression(self) -> None:
        compressor = WorkingMemoryCompressor()
        objs = [
            WorkingMemoryObject(
                identifier=f'wm_{i}',
                source_memory='test',
                activation_reason='test',
                activation_score=float(i) / 10,
            )
            for i in range(10)
        ]
        result, metrics = compressor.compress(
            objs, target_size=3, strategy='replacing_observations_with_semantic_knowledge'
        )
        assert len(result) <= 4  # 3 kept + 1 summary
        assert metrics.strategy_used == 'replacing_observations_with_semantic_knowledge'

    def test_chain_compression(self) -> None:
        compressor = WorkingMemoryCompressor()
        objs = [
            WorkingMemoryObject(
                identifier='wm_1',
                source_memory='test',
                activation_reason='test',
                dependency_links=('wm_2',),
            ),
            WorkingMemoryObject(
                identifier='wm_2',
                source_memory='test',
                activation_reason='test',
            ),
            WorkingMemoryObject(
                identifier='wm_3',
                source_memory='test',
                activation_reason='test',
            ),
        ]
        result, metrics = compressor.compress(
            objs, target_size=2, strategy='collapsing_reasoning_chains'
        )
        assert metrics.strategy_used == 'collapsing_reasoning_chains'

    def test_reference_compression(self) -> None:
        compressor = WorkingMemoryCompressor()
        objs = [
            WorkingMemoryObject(
                identifier=f'wm_{i}',
                source_memory='test',
                activation_reason='test',
                activation_score=float(i) / 10,
                dependency_links=('ref_1',) if i == 3 else (),
            )
            for i in range(8)
        ]
        result, metrics = compressor.compress(
            objs, target_size=3, strategy='preserving_graph_references'
        )
        assert len(result) <= 3

    def test_auto_compress(self) -> None:
        compressor = WorkingMemoryCompressor()
        objs = [
            WorkingMemoryObject(
                identifier=f'wm_{i}',
                source_memory='test',
                activation_reason='test',
                associated_episode='ep_1' if i < 4 else 'ep_2',
                activation_score=float(i) / 10,
            )
            for i in range(8)
        ]
        result, metrics = compressor.auto_compress(objs, target_size=3)
        assert len(result) <= 4

    def test_auto_compress_within_target(self) -> None:
        compressor = WorkingMemoryCompressor()
        objs = [
            WorkingMemoryObject(
                identifier='wm_1', source_memory='test', activation_reason='test'
            )
        ]
        result, metrics = compressor.auto_compress(objs, target_size=5)
        assert len(result) == 1
        assert metrics.strategy_used == 'none'

    def test_compression_history(self) -> None:
        compressor = WorkingMemoryCompressor()
        objs = [
            WorkingMemoryObject(
                identifier=f'wm_{i}',
                source_memory='test',
                activation_reason='test',
                activation_score=float(i) / 10,
            )
            for i in range(6)
        ]
        compressor.compress(objs, target_size=2)
        assert len(compressor.get_compression_history()) == 1

    def test_unknown_strategy_defaults_to_grouping(self) -> None:
        compressor = WorkingMemoryCompressor()
        objs = [
            WorkingMemoryObject(
                identifier=f'wm_{i}',
                source_memory='test',
                activation_reason='test',
                associated_episode='ep_1',
                activation_score=float(i) / 10,
            )
            for i in range(6)
        ]
        result, metrics = compressor.compress(
            objs, target_size=2, strategy='unknown_strategy'
        )
        assert metrics.strategy_used == 'grouping'
