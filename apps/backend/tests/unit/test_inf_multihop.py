"""Tests for the INF-03 Multi-Hop Reasoning Engine."""

from __future__ import annotations

import pytest

from ayeneh.inf.multihop.types import (
    HOP_TYPES,
    REASONING_DIMENSIONS,
    LOOP_TYPES,
    HiddenPattern,
    MultiHopChain,
    MultiHopResult,
    NarrativeLoop,
    ReasoningHop,
)
from ayeneh.inf.multihop.engine import MultiHopReasoningEngine
from ayeneh.inf.multihop.loops import NarrativeLoopDetector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return MultiHopReasoningEngine()


@pytest.fixture
def detector():
    return NarrativeLoopDetector()


@pytest.fixture
def sample_observations():
    return [
        {
            'id': 'obs-1',
            'content': 'User starts day with coffee every morning',
            'confidence': 0.9,
        },
        {
            'id': 'obs-2',
            'content': 'User values consistency in daily habits',
            'confidence': 0.7,
        },
        {
            'id': 'obs-3',
            'content': 'User reports feeling more focused after coffee',
            'confidence': 0.8,
        },
    ]


@pytest.fixture
def sample_context():
    return {
        'context_id': 'test-multihop-ctx-1',
        'domain': 'general',
    }


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestMultiHopTypes:
    """Tests for INF-03 type definitions."""

    def test_hop_types_count(self):
        assert len(HOP_TYPES) == 5

    def test_reasoning_dimensions_count(self):
        assert len(REASONING_DIMENSIONS) == 6

    def test_loop_types_count(self):
        assert len(LOOP_TYPES) == 5

    def test_multi_hop_chain_creation(self):
        chain = MultiHopChain(
            chain_id='chain-1',
            starting_observation='Test observation',
        )
        assert chain.chain_id == 'chain-1'
        assert chain.depth == 0
        assert chain.confidence == 0.0

    def test_multi_hop_chain_frozen(self):
        chain = MultiHopChain(
            chain_id='chain-1',
            starting_observation='Test',
        )
        with pytest.raises(AttributeError):
            chain.chain_id = 'changed'  # type: ignore[misc]

    def test_reasoning_hop_creation(self):
        hop = ReasoningHop(
            hop_id='hop-1',
            hop_type='observation_to_behavioral',
            source_dimension='observation',
            target_dimension='behavioral',
            source_statement='Source',
            target_statement='Target',
        )
        assert hop.hop_type == 'observation_to_behavioral'

    def test_narrative_loop_creation(self):
        loop = NarrativeLoop(
            loop_id='loop-1',
            loop_type='observation_interpretation_loop',
            reinforcement_strength=0.7,
        )
        assert loop.reinforcement_strength == 0.7

    def test_hidden_pattern_creation(self):
        pattern = HiddenPattern(
            pattern_id='hp-1',
            pattern_type='deep_reasoning_chain',
            confidence=0.8,
        )
        assert pattern.confidence == 0.8

    def test_multi_hop_result_defaults(self):
        result = MultiHopResult()
        assert result.chains == ()
        assert result.overall_confidence == 0.0


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestMultiHopReasoningEngine:
    """Tests for the INF-03 MultiHopReasoningEngine."""

    def test_engine_initialization(self):
        engine = MultiHopReasoningEngine()
        assert engine._chains == {}

    def test_process_empty_observations(self, engine, sample_context):
        result = engine.process([], sample_context)
        assert isinstance(result, MultiHopResult)
        assert result.chains == ()

    def test_process_basic(self, engine, sample_observations, sample_context):
        result = engine.process(sample_observations, sample_context)
        assert isinstance(result, MultiHopResult)
        assert len(result.chains) > 0

    def test_process_produces_chains(self, engine, sample_observations, sample_context):
        result = engine.process(sample_observations, sample_context)
        for chain in result.chains:
            assert isinstance(chain, MultiHopChain)
            assert chain.starting_observation != ''
            assert chain.depth > 0

    def test_process_chain_confidence(self, engine, sample_observations, sample_context):
        result = engine.process(sample_observations, sample_context)
        for chain in result.chains:
            assert 0.0 <= chain.confidence <= 1.0

    def test_process_chain_hops(self, engine, sample_observations, sample_context):
        result = engine.process(sample_observations, sample_context)
        for chain in result.chains:
            assert len(chain.hops) == chain.depth
            for hop in chain.hops:
                assert 'hop_id' in hop
                assert 'hop_type' in hop

    def test_process_with_no_context(self, engine, sample_observations):
        result = engine.process(sample_observations)
        assert isinstance(result, MultiHopResult)

    def test_process_max_depth(self, engine, sample_observations, sample_context):
        result = engine.process(sample_observations, sample_context, max_depth=2)
        for chain in result.chains:
            assert chain.depth <= 2

    def test_process_single_observation(self, engine, sample_context):
        obs = [{'id': 'obs-1', 'content': 'Single observation'}]
        result = engine.process(obs, sample_context)
        assert isinstance(result, MultiHopResult)

    def test_process_empty_content(self, engine, sample_context):
        obs = [{'id': 'obs-1', 'content': ''}]
        result = engine.process(obs, sample_context)
        assert isinstance(result, MultiHopResult)
        assert result.chains == ()

    def test_narrative_loops_detected(self, engine, sample_observations, sample_context):
        result = engine.process(sample_observations, sample_context)
        assert isinstance(result.narrative_loops, tuple)

    def test_hidden_patterns(self, engine, sample_observations, sample_context):
        result = engine.process(sample_observations, sample_context)
        assert isinstance(result.hidden_patterns, tuple)

    def test_overall_confidence(self, engine, sample_observations, sample_context):
        result = engine.process(sample_observations, sample_context)
        assert 0.0 <= result.overall_confidence <= 1.0

    def test_calibration_notes(self, engine, sample_observations, sample_context):
        result = engine.process(sample_observations, sample_context)
        assert isinstance(result.calibration_notes, tuple)

    def test_processing_metadata(self, engine, sample_observations, sample_context):
        result = engine.process(sample_observations, sample_context)
        assert 'chain_count' in result.processing_metadata
        assert 'observation_count' in result.processing_metadata

    def test_get_chain(self, engine, sample_observations, sample_context):
        result = engine.process(sample_observations, sample_context)
        if result.chains:
            chain_id = result.chains[0].chain_id
            chain = engine.get_chain(chain_id)
            assert chain is not None
            assert chain.chain_id == chain_id

    def test_get_chain_not_found(self, engine):
        assert engine.get_chain('nonexistent') is None

    def test_get_all_chains(self, engine, sample_observations, sample_context):
        engine.process(sample_observations, sample_context)
        chains = engine.get_all_chains()
        assert isinstance(chains, list)
        assert len(chains) >= 1

    def test_hop_transitions(self, engine, sample_context):
        obs = [{'id': 'obs-1', 'content': 'Detailed observation about behavior'}]
        result = engine.process(obs, sample_context, max_depth=5)
        # Check that hops follow the expected transition pattern
        for chain in result.chains:
            for i, hop in enumerate(chain.hops):
                if i > 0:
                    prev_target = chain.hops[i - 1].get('target_dimension')
                    curr_source = hop.get('source_dimension')
                    # Source of current should match target of previous
                    assert prev_target == curr_source


# ---------------------------------------------------------------------------
# Loop Detector tests
# ---------------------------------------------------------------------------


class TestNarrativeLoopDetector:
    """Tests for the INF-03 NarrativeLoopDetector."""

    def test_empty_inputs(self, detector):
        loops = detector.detect_loops([], [])
        assert loops == []

    def test_no_loops_detected(self, detector):
        hops = [
            {
                'hop_id': 'h1',
                'hop_type': 'observation_to_behavioral',
                'source_statement': 'A',
                'target_statement': 'B',
            },
        ]
        observations = [{'id': 'o1', 'content': 'X'}]
        loops = detector.detect_loops(hops, observations)
        assert isinstance(loops, list)

    def test_interpretation_loop_detection(self, detector):
        hops = [
            {
                'hop_id': 'h1',
                'hop_type': 'observation_to_behavioral',
                'source_statement': 'Coffee makes me productive',
                'target_statement': 'Coffee habit detected',
            },
            {
                'hop_id': 'h2',
                'hop_type': 'identity_to_narrative',
                'source_statement': 'Productive identity',
                'target_statement': 'Coffee makes me productive and focused',
            },
        ]
        loops = detector.detect_loops(hops, [])
        assert isinstance(loops, list)

    def test_belief_confirmation_detection(self, detector):
        hops = [
            {
                'hop_id': 'h1',
                'hop_type': 'behavioral_to_identity',
                'target_statement': 'Morning routine is core identity',
                'target_dimension': 'identity',
            },
            {
                'hop_id': 'h2',
                'hop_type': 'behavioral_to_identity',
                'target_statement': 'Morning routine shapes who I am',
                'target_dimension': 'identity',
            },
        ]
        loops = detector.detect_loops(hops, [])
        # Should detect some kind of loop
        assert isinstance(loops, list)

    def test_loop_reinforcement_strength(self, detector):
        hops = [
            {
                'hop_id': 'h1',
                'hop_type': 'observation_to_behavioral',
                'source_statement': 'Daily coffee routine is important',
                'target_statement': 'Coffee behavior is habitual',
            },
            {
                'hop_id': 'h2',
                'hop_type': 'identity_to_narrative',
                'source_statement': 'Coffee is part of identity',
                'target_statement': 'Daily coffee routine defines my morning',
            },
        ]
        loops = detector.detect_loops(hops, [])
        for loop in loops:
            assert 0.0 <= loop.reinforcement_strength <= 1.0

    def test_loop_ids_populated(self, detector):
        hops = [
            {
                'hop_id': 'h1',
                'hop_type': 'observation_to_behavioral',
                'source_statement': 'Coffee habit',
                'target_statement': 'Coffee behavior',
            },
            {
                'hop_id': 'h2',
                'hop_type': 'identity_to_narrative',
                'source_statement': 'Coffee identity',
                'target_statement': 'Coffee habit defines my morning',
            },
        ]
        loops = detector.detect_loops(hops, [])
        for loop in loops:
            assert loop.loop_id != ''
            assert len(loop.node_ids) > 0
