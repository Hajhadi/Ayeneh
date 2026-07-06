"""Unit tests for INT-02 Global Context Manager types and engine."""

from __future__ import annotations

import pytest

from ayeneh.int.global_context.types import (
    CONTEXT_DIMENSIONS,
    CONTEXT_PERSISTENCE,
    HIERARCHICAL_LEVELS,
    ContextConflict,
    ContextDistribution,
    ContextEntry,
    ContextPriority,
    ExplainabilityMetadata,
    GlobalContextObject,
    GlobalContextResult,
)
from ayeneh.int.global_context.engine import GlobalContextManager


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestContextEntry:
    def test_valid_entry(self) -> None:
        entry = ContextEntry(
            entry_id='e1',
            dimension='temporal',
            level='task',
            persistence='session',
        )
        assert entry.entry_id == 'e1'
        assert entry.dimension == 'temporal'

    def test_all_valid_dimensions(self) -> None:
        for dim in CONTEXT_DIMENSIONS:
            entry = ContextEntry(dimension=dim)
            assert entry.dimension == dim

    def test_invalid_dimension_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid dimension"):
            ContextEntry(dimension='invalid')

    def test_all_valid_persistence(self) -> None:
        for p in CONTEXT_PERSISTENCE:
            entry = ContextEntry(persistence=p)
            assert entry.persistence == p

    def test_invalid_persistence_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid persistence"):
            ContextEntry(persistence='invalid')

    def test_all_valid_levels(self) -> None:
        for level in HIERARCHICAL_LEVELS:
            entry = ContextEntry(level=level)
            assert entry.level == level

    def test_invalid_level_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid level"):
            ContextEntry(level='invalid')


class TestContextConflict:
    def test_creation(self) -> None:
        conflict = ContextConflict(
            conflict_id='c1',
            entry_a_id='e1',
            entry_b_id='e2',
            conflict_type='contradiction',
        )
        assert conflict.conflict_id == 'c1'
        assert conflict.severity == 'low'


class TestContextPriority:
    def test_creation(self) -> None:
        priority = ContextPriority(entry_id='e1', priority_score=0.85)
        assert priority.entry_id == 'e1'
        assert priority.priority_score == 0.85


class TestGlobalContextObject:
    def test_default_creation(self) -> None:
        obj = GlobalContextObject(context_id='ctx1')
        assert obj.context_id == 'ctx1'
        assert obj.confidence == 0.0
        assert len(obj.current_goals) == 0

    def test_frozen(self) -> None:
        obj = GlobalContextObject(context_id='ctx1')
        with pytest.raises(AttributeError):
            obj.context_id = 'ctx2'  # type: ignore[misc]


class TestGlobalContextResult:
    def test_has_conflicts_false(self) -> None:
        result = GlobalContextResult()
        assert result.has_conflicts is False

    def test_has_conflicts_true(self) -> None:
        result = GlobalContextResult(conflicts=(ContextConflict(),))
        assert result.has_conflicts is True

    def test_entry_count(self) -> None:
        result = GlobalContextResult(entries=(ContextEntry(), ContextEntry()))
        assert result.entry_count == 2


class TestConstants:
    def test_context_dimensions(self) -> None:
        assert len(CONTEXT_DIMENSIONS) == 8
        assert 'temporal' in CONTEXT_DIMENSIONS
        assert 'behavioral' in CONTEXT_DIMENSIONS

    def test_context_persistence(self) -> None:
        assert 'transient' in CONTEXT_PERSISTENCE
        assert 'persistent' in CONTEXT_PERSISTENCE

    def test_hierarchical_levels(self) -> None:
        assert 'global' in HIERARCHICAL_LEVELS
        assert 'immediate' in HIERARCHICAL_LEVELS


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestGlobalContextManager:
    def setup_method(self) -> None:
        self.manager = GlobalContextManager()

    def test_default_management(self) -> None:
        result = self.manager.manage_context()
        assert result.context_id
        assert result.context_object is not None
        assert result.duration_ms >= 0

    def test_management_with_sources(self) -> None:
        result = self.manager.manage_context(
            context_sources={
                'goals': ['understand_user_intent'],
                'dialogue_state': 'active',
                'temporal': {'session_start': '2024-01-01'},
            },
        )
        assert result.entry_count >= 1
        assert result.context_object is not None

    def test_management_with_goals(self) -> None:
        result = self.manager.manage_context(
            goals=['goal1', 'goal2'],
        )
        obj = result.context_object
        assert obj is not None
        assert 'goal1' in obj.current_goals

    def test_conflict_detection(self) -> None:
        result = self.manager.manage_context(
            context_sources={
                'dialogue_state': 'state_a',
            },
        )
        # No conflicts expected with single source
        assert isinstance(result.conflicts, tuple)

    def test_module_registration(self) -> None:
        self.manager.register_module('mod1')
        self.manager.register_module('mod2')
        result = self.manager.manage_context()
        # Should have distributions for registered modules
        assert len(result.distributions) == 2

    def test_management_with_target_modules(self) -> None:
        result = self.manager.manage_context(
            target_modules=['mem', 'dlg'],
        )
        assert len(result.distributions) == 2

    def test_context_completes_all_phases(self) -> None:
        result = self.manager.manage_context(
            context_sources={
                'goals': ['test'],
                'dialogue_state': 'testing',
                'temporal': {'now': True},
                'environment': {'env_key': 'env_val'},
                'memory_references': ['ref1'],
            },
        )
        assert result.context_object is not None
        assert result.duration_ms >= 0

    def test_explainability_metadata(self) -> None:
        result = self.manager.manage_context(
            context_sources={'goals': ['test']},
        )
        meta = result.context_object.explainability_metadata
        assert 'reasoning_chain' in meta
        assert len(meta['reasoning_chain']) > 0

    def test_priority_map_populated(self) -> None:
        result = self.manager.manage_context(
            context_sources={
                'goals': ['important_goal'],
                'dialogue_state': 'active',
            },
        )
        obj = result.context_object
        assert obj is not None
        assert len(obj.priority_map) > 0

    def test_frozen_result(self) -> None:
        result = self.manager.manage_context()
        with pytest.raises(AttributeError):
            result.context_id = 'changed'  # type: ignore[misc]
