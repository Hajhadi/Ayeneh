"""Tests for INT-04 Unified Cognitive State."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.int.cognitive_state.types import (
    HEALTH_THRESHOLDS,
    STATE_DIMENSIONS,
    STATE_TRANSITIONS,
    VALID_FROM_STATES,
    VALID_TO_STATES,
    ArchitectureSyncRecord,
    CognitiveStateObject,
    CognitiveStateResult,
    ConflictRecord,
    DimensionStatus,
    ExplainabilityMetadata,
    StateTransition,
)
from ayeneh.int.cognitive_state.engine import CognitiveStateEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return CognitiveStateEngine()


@pytest.fixture
def sample_context():
    return {
        'active_modules': ['cog', 'inf', 'dlg'],
        'active_goals': ['goal-1'],
        'module_data': {
            'memory': {'active': True, 'confidence': 0.9, 'modules': ['memo']},
            'inference': {'active': True, 'confidence': 0.85, 'modules': ['inf']},
            'executive': {'active': True, 'confidence': 0.8, 'modules': ['dec']},
            'action': {'active': True, 'confidence': 0.75, 'modules': ['act']},
            'self': {'active': True, 'confidence': 0.7, 'modules': ['cog']},
            'communication': {'active': True, 'confidence': 0.6, 'modules': ['int']},
            'context': {'active': True, 'confidence': 0.65, 'modules': ['int']},
            'governance': {'active': True, 'confidence': 0.9, 'modules': ['gov']},
        },
    }


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestCognitiveStateTypes:
    """Tests for INT-04 type definitions."""

    def test_state_dimensions_count(self):
        assert len(STATE_DIMENSIONS) == 8

    def test_state_dimensions_include_expected(self):
        expected = {
            'memory', 'inference', 'executive', 'action',
            'self', 'communication', 'context', 'governance',
        }
        assert set(STATE_DIMENSIONS) == expected

    def test_state_transitions_count(self):
        assert len(STATE_TRANSITIONS) == 6

    def test_valid_from_states_covers_all_transitions(self):
        for transition in STATE_TRANSITIONS:
            assert transition in VALID_FROM_STATES

    def test_valid_to_states_covers_all_transitions(self):
        for transition in STATE_TRANSITIONS:
            assert transition in VALID_TO_STATES

    def test_health_thresholds_count(self):
        assert len(HEALTH_THRESHOLDS) == 4

    def test_health_thresholds_keys(self):
        assert 'critical' in HEALTH_THRESHOLDS
        assert 'degraded' in HEALTH_THRESHOLDS
        assert 'healthy' in HEALTH_THRESHOLDS
        assert 'optimal' in HEALTH_THRESHOLDS


class TestCognitiveStateDataclasses:
    """Tests for INT-04 frozen dataclasses."""

    def test_dimension_status_creation(self):
        ds = DimensionStatus(dimension='memory', active=True, confidence=0.9)
        assert ds.dimension == 'memory'
        assert ds.active is True
        assert ds.confidence == 0.9

    def test_dimension_status_immutability(self):
        ds = DimensionStatus(dimension='memory')
        with pytest.raises(AttributeError):
            ds.dimension = 'inference'  # type: ignore[misc]

    def test_dimension_status_invalid_dimension(self):
        with pytest.raises(ValueError, match="Invalid dimension"):
            DimensionStatus(dimension='nonexistent')

    def test_dimension_status_valid_dimensions(self):
        for dim in STATE_DIMENSIONS:
            ds = DimensionStatus(dimension=dim)
            assert ds.dimension == dim

    def test_state_transition_creation(self):
        st = StateTransition(
            transition_id='t-1',
            transition_type='idle_to_active',
            from_state='idle',
            to_state='active',
        )
        assert st.transition_id == 't-1'
        assert st.transition_type == 'idle_to_active'

    def test_state_transition_invalid_type(self):
        with pytest.raises(ValueError, match="Invalid transition"):
            StateTransition(transition_type='invalid_transition')

    def test_state_transition_valid_types(self):
        for t in STATE_TRANSITIONS:
            st = StateTransition(transition_type=t)
            assert st.transition_type == t

    def test_conflict_record_creation(self):
        cr = ConflictRecord(
            conflict_id='c-1',
            source_dimension='memory',
            target_dimension='inference',
            conflict_type='inconsistency',
            severity='medium',
        )
        assert cr.conflict_id == 'c-1'
        assert cr.severity == 'medium'

    def test_architecture_sync_record_creation(self):
        ar = ArchitectureSyncRecord(
            sync_id='s-1',
            synced_dimensions=('memory', 'inference'),
            conflicts_resolved=2,
            health_before=0.6,
            health_after=0.85,
        )
        assert ar.sync_id == 's-1'
        assert ar.conflicts_resolved == 2

    def test_cognitive_state_object_creation(self):
        cso = CognitiveStateObject(state_id='cs-1')
        assert cso.state_id == 'cs-1'
        assert cso.consistency_status == 'consistent'
        assert cso.architecture_health == 1.0
        assert cso.active_modules == ()
        assert cso.active_goals == ()
        assert cso.running_workflows == ()
        assert cso.resource_status == {}
        assert cso.confidence_map == {}
        assert cso.execution_snapshot == {}
        assert cso.revision_history == ()
        assert isinstance(cso.creation_timestamp, datetime)
        assert cso.explainability_metadata == {}

    def test_cognitive_state_object_immutability(self):
        cso = CognitiveStateObject(state_id='cs-1')
        with pytest.raises(AttributeError):
            cso.state_id = 'cs-2'  # type: ignore[misc]

    def test_cognitive_state_result_creation(self):
        csr = CognitiveStateResult(state_id='csr-1')
        assert csr.state_id == 'csr-1'
        assert csr.state_object is None
        assert csr.dimension_statuses == ()
        assert csr.transitions == ()
        assert csr.conflicts == ()
        assert csr.sync_records == ()
        assert csr.global_confidence == 0.0
        assert csr.duration_ms == 0.0
        assert csr.errors == ()
        assert csr.pipeline_phases_completed == ()

    def test_cognitive_state_result_has_conflicts_false(self):
        csr = CognitiveStateResult()
        assert csr.has_conflicts is False

    def test_cognitive_state_result_has_conflicts_true(self):
        csr = CognitiveStateResult(
            conflicts=(ConflictRecord(conflict_id='c-1'),),
        )
        assert csr.has_conflicts is True

    def test_cognitive_state_result_dimension_count(self):
        csr = CognitiveStateResult(
            dimension_statuses=(
                DimensionStatus(dimension='memory'),
                DimensionStatus(dimension='inference'),
            ),
        )
        assert csr.dimension_count == 2


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestCognitiveStateEngine:
    """Tests for INT-04 CognitiveStateEngine."""

    def test_process_empty_request(self, engine):
        result = engine.process()
        assert isinstance(result, CognitiveStateResult)
        assert len(result.pipeline_phases_completed) == 7
        assert result.state_id != ''

    def test_process_phases_order(self, engine):
        result = engine.process()
        expected_phases = (
            'StateCollection',
            'ConsistencyValidation',
            'ConflictDetection',
            'StateIntegration',
            'GlobalCognitiveState',
            'ArchitectureSynchronization',
            'StateDistribution',
        )
        assert result.pipeline_phases_completed == expected_phases

    def test_process_collects_all_dimensions(self, engine):
        result = engine.process()
        assert result.dimension_count == 8

    def test_process_with_context(self, engine, sample_context):
        result = engine.process(context=sample_context)
        assert result.dimension_count == 8
        assert result.state_object is not None

    def test_process_state_object_has_state_id(self, engine):
        result = engine.process()
        assert result.state_object is not None
        assert result.state_object.state_id == result.state_id

    def test_process_global_confidence_range(self, engine):
        result = engine.process()
        assert 0.0 <= result.global_confidence <= 1.0

    def test_process_with_high_confidence_modules(self, engine):
        ctx = {
            'module_data': {
                dim: {'active': True, 'confidence': 0.95}
                for dim in STATE_DIMENSIONS
            },
        }
        result = engine.process(context=ctx)
        assert result.global_confidence > 0.8

    def test_process_with_low_confidence_modules(self, engine):
        ctx = {
            'module_data': {
                dim: {'active': True, 'confidence': 0.1}
                for dim in STATE_DIMENSIONS
            },
        }
        result = engine.process(context=ctx)
        assert result.global_confidence < 0.3

    def test_process_detects_low_conflict(self, engine):
        ctx = {
            'module_data': {
                dim: {'active': True, 'confidence': 0.9}
                for dim in STATE_DIMENSIONS
            },
        }
        result = engine.process(context=ctx)
        assert not result.has_conflicts

    def test_process_detects_inactive_majority(self, engine):
        ctx = {
            'module_data': {
                dim: {'active': False, 'confidence': 0.5}
                for dim in STATE_DIMENSIONS
            },
        }
        result = engine.process(context=ctx)
        assert result.has_conflicts

    def test_process_consistency_status_consistent(self, engine):
        result = engine.process()
        assert result.state_object.consistency_status == 'consistent'

    def test_process_with_active_modules(self, engine, sample_context):
        result = engine.process(context=sample_context)
        state_obj = result.state_object
        assert state_obj is not None
        assert 'cog' in state_obj.active_modules

    def test_register_subscriber(self, engine):
        engine.register_subscriber('module_a')
        engine.register_subscriber('module_b')
        assert len(engine._subscribers) == 2

    def test_register_subscriber_no_duplicates(self, engine):
        engine.register_subscriber('module_a')
        engine.register_subscriber('module_a')
        assert len(engine._subscribers) == 1

    def test_process_state_history(self, engine):
        engine.process()
        engine.process()
        assert len(engine._state_history) == 2

    def test_process_no_errors(self, engine):
        result = engine.process()
        assert len(result.errors) == 0

    def test_process_with_empty_module_data(self, engine):
        ctx = {'module_data': {}}
        result = engine.process(context=ctx)
        assert result.dimension_count == 8
        assert result.duration_ms >= 0

    def test_process_architecture_health_range(self, engine):
        result = engine.process()
        assert 0.0 <= result.state_object.architecture_health <= 1.0
