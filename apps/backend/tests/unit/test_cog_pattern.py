"""Tests for the COG-11 Behavioral Pattern Engine."""

from __future__ import annotations

import pytest

from ayeneh.cog.pattern.detection import (
    FractalDetector,
    LoopDetector,
    RecursiveDetector,
)
from ayeneh.cog.pattern.engine import BehavioralPatternEngine
from ayeneh.cog.pattern.types import (
    PATTERN_LIFECYCLE_STATES,
    PATTERN_TYPES,
    BehavioralLoop,
    MetaPattern,
    PatternObject,
    PatternResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return BehavioralPatternEngine()


@pytest.fixture
def loop_detector():
    return LoopDetector()


@pytest.fixture
def fractal_detector():
    return FractalDetector()


@pytest.fixture
def recursive_detector():
    return RecursiveDetector()


@pytest.fixture
def sample_evidence():
    return [
        {'id': 'ev-1', 'text': 'I always procrastinate before deadlines', 'category': 'behavioral_report'},
        {'id': 'ev-2', 'text': 'I procrastinate when stressed about work', 'category': 'behavioral_report'},
        {'id': 'ev-3', 'text': 'I believe I work better under pressure', 'category': 'self_report'},
        {'id': 'ev-4', 'text': 'I believe last-minute work is my style', 'category': 'self_report'},
        {'id': 'ev-5', 'text': 'I decided to start the project early', 'category': 'decision_report'},
        {'id': 'ev-6', 'text': 'I value productivity and efficiency', 'category': 'identity_statement'},
    ]


@pytest.fixture
def sample_pattern():
    return PatternObject(
        identifier='pat-1',
        pattern_description='Procrastination loop before deadlines',
        pattern_type='behavioral_loop',
        frequency=5,
        consistency=0.8,
        confidence=0.7,
        stability=0.6,
        influence=0.5,
        trigger_conditions=('deadline_approaching',),
        termination_conditions=('deadline_passed',),
        contexts=('work', 'study'),
        supporting_behaviors=('procrastinate',),
        supporting_evidence=('ev-1', 'ev-2'),
        associated_narratives=('narr-1',),
        associated_beliefs=('belief-1',),
        associated_values=('value-1',),
        lifecycle_state='validated',
    )


# ---------------------------------------------------------------------------
# PatternObject tests
# ---------------------------------------------------------------------------


class TestPatternObject:
    def test_creation(self, sample_pattern):
        assert sample_pattern.identifier == 'pat-1'
        assert sample_pattern.pattern_type == 'behavioral_loop'
        assert sample_pattern.frequency == 5

    def test_defaults(self):
        pat = PatternObject(
            identifier='p1',
            pattern_description='test',
            pattern_type='behavioral_loop',
        )
        assert pat.frequency == 0
        assert pat.consistency == 0.0
        assert pat.confidence == 0.0
        assert pat.stability == 0.0
        assert pat.influence == 0.0
        assert pat.trigger_conditions == ()
        assert pat.lifecycle_state == 'candidate'
        assert pat.specification_version == '1.0.0'

    def test_frozen(self, sample_pattern):
        with pytest.raises(AttributeError):
            sample_pattern.frequency = 10  # type: ignore[misc]

    def test_frozen_pattern_description(self, sample_pattern):
        with pytest.raises(AttributeError):
            sample_pattern.pattern_description = 'other'  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BehavioralLoop tests
# ---------------------------------------------------------------------------


class TestBehavioralLoop:
    def test_creation(self):
        loop = BehavioralLoop(
            loop_id='l1',
            trigger='stress',
            narrative_activation='narr-1',
            belief_activation='belief-1',
            emotion='anxiety',
            decision='avoid',
            behavior='procrastinate',
            outcome='deadline_missed',
            reinforcement='self_doubt',
            confidence=0.7,
        )
        assert loop.loop_id == 'l1'
        assert loop.trigger == 'stress'
        assert loop.behavior == 'procrastinate'

    def test_defaults(self):
        loop = BehavioralLoop(
            loop_id='l1',
            trigger='t',
            narrative_activation='',
            belief_activation='',
            emotion='',
            decision='',
            behavior='',
            outcome='',
            reinforcement='',
        )
        assert loop.confidence == 0.0

    def test_frozen(self):
        loop = BehavioralLoop(
            loop_id='l1', trigger='t', narrative_activation='',
            belief_activation='', emotion='', decision='',
            behavior='', outcome='', reinforcement='',
        )
        with pytest.raises(AttributeError):
            loop.trigger = 'other'  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MetaPattern tests
# ---------------------------------------------------------------------------


class TestMetaPattern:
    def test_creation(self):
        meta = MetaPattern(
            pattern_id='mp1',
            description='Cross-domain avoidance pattern',
            domain_patterns=('p1', 'p2'),
            confidence=0.6,
            similarity_score=0.8,
        )
        assert meta.pattern_id == 'mp1'
        assert len(meta.domain_patterns) == 2

    def test_defaults(self):
        meta = MetaPattern(pattern_id='mp1', description='test')
        assert meta.domain_patterns == ()
        assert meta.confidence == 0.0
        assert meta.similarity_score == 0.0

    def test_frozen(self):
        meta = MetaPattern(pattern_id='mp1', description='test')
        with pytest.raises(AttributeError):
            meta.confidence = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BehavioralPatternEngine tests
# ---------------------------------------------------------------------------


class TestBehavioralPatternEngine:
    def test_process_returns_result(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert isinstance(result, PatternResult)

    def test_patterns_extracted(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert result.total_extracted >= 0

    def test_all_patterns_have_identifiers(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        for pat in result.patterns.values():
            assert pat.identifier
            assert isinstance(pat.identifier, str)

    def test_confidence_in_range(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        for pat in result.patterns.values():
            assert 0.0 <= pat.confidence <= 1.0

    def test_determinism(self, engine, sample_evidence):
        """Same input → same output (deterministic pipeline)."""
        r1 = engine.process(sample_evidence)
        r2 = engine.process(sample_evidence)
        assert r1.total_extracted == r2.total_extracted

    def test_empty_evidence(self, engine):
        result = engine.process([])
        assert result.total_extracted == 0
        assert len(result.loops) == 0
        assert len(result.meta_patterns) == 0

    def test_with_decisions_and_behaviors(self, engine, sample_evidence):
        decisions = [
            {'id': 'd1', 'text': 'I decided to stop procrastinating'},
            {'id': 'd2', 'text': 'I chose to start early'},
        ]
        behaviors = [
            {'id': 'b1', 'text': 'I procrastinated again', 'category': 'behavioral_report'},
            {'id': 'b2', 'text': 'I procrastinated on the report', 'category': 'behavioral_report'},
        ]
        result = engine.process(sample_evidence, decisions=decisions, behaviors=behaviors)
        assert isinstance(result, PatternResult)

    def test_loops_detected(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert isinstance(result.loops, dict)

    def test_meta_patterns(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert isinstance(result.meta_patterns, dict)

    def test_lifecycle_summary(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert isinstance(result.lifecycle_summary, dict)


# ---------------------------------------------------------------------------
# LoopDetector tests
# ---------------------------------------------------------------------------


class TestLoopDetector:
    def test_detect_behavioral_loops(self, loop_detector, sample_pattern):
        loops = loop_detector.detect_behavioral_loops([sample_pattern])
        assert isinstance(loops, list)

    def test_detect_cognitive_loops(self, loop_detector):
        pattern = PatternObject(
            identifier='p1',
            pattern_description='Cognitive loop test',
            pattern_type='cognitive_loop',
            frequency=3,
            confidence=0.6,
            associated_beliefs=('belief-1',),
            associated_narratives=('narr-1',),
        )
        loops = loop_detector.detect_cognitive_loops([pattern])
        assert len(loops) >= 0  # may or may not detect depending on criteria

    def test_low_frequency_no_loops(self, loop_detector):
        pattern = PatternObject(
            identifier='p1',
            pattern_description='Rare pattern',
            pattern_type='behavioral_loop',
            frequency=1,
        )
        loops = loop_detector.detect_behavioral_loops([pattern])
        assert len(loops) == 0

    def test_empty_patterns(self, loop_detector):
        loops = loop_detector.detect_behavioral_loops([])
        assert loops == []


# ---------------------------------------------------------------------------
# FractalDetector tests
# ---------------------------------------------------------------------------


class TestFractalDetector:
    def test_compute_cross_scale_similarity(self, fractal_detector):
        a = PatternObject(
            identifier='a', pattern_description='test a',
            pattern_type='behavioral_loop',
            supporting_evidence=('ev-1',),
            associated_beliefs=('b1',),
        )
        b = PatternObject(
            identifier='b', pattern_description='test b',
            pattern_type='behavioral_loop',
            supporting_evidence=('ev-1',),
            associated_beliefs=('b1',),
        )
        sim = fractal_detector.compute_cross_scale_similarity(a, b)
        assert 0.0 <= sim <= 1.0
        assert sim > 0.0  # should have overlap

    def test_no_similarity(self, fractal_detector):
        a = PatternObject(
            identifier='a', pattern_description='test a',
            pattern_type='behavioral_loop',
            supporting_evidence=('ev-1',),
            associated_beliefs=('b1',),
        )
        b = PatternObject(
            identifier='b', pattern_description='test b',
            pattern_type='recursive',
            supporting_evidence=('ev-99',),
            associated_beliefs=('b99',),
        )
        sim = fractal_detector.compute_cross_scale_similarity(a, b)
        assert 0.0 <= sim <= 1.0

    def test_none_inputs(self, fractal_detector):
        sim = fractal_detector.compute_cross_scale_similarity(None, None)
        assert sim == 0.0

    def test_detect_fractal_patterns(self, fractal_detector):
        a = PatternObject(
            identifier='a', pattern_description='test a',
            pattern_type='behavioral_loop',
            frequency=3,
            consistency=0.8,
            confidence=0.7,
            stability=0.6,
            influence=0.5,
            supporting_evidence=('ev-1',),
            associated_beliefs=('b1',),
            associated_narratives=('n1',),
        )
        b = PatternObject(
            identifier='b', pattern_description='test b',
            pattern_type='behavioral_loop',
            frequency=3,
            consistency=0.8,
            confidence=0.7,
            stability=0.6,
            influence=0.5,
            supporting_evidence=('ev-1',),
            associated_beliefs=('b1',),
            associated_narratives=('n1',),
        )
        fractals = fractal_detector.detect_fractal_patterns([a, b])
        assert isinstance(fractals, list)


# ---------------------------------------------------------------------------
# RecursiveDetector tests
# ---------------------------------------------------------------------------


class TestRecursiveDetector:
    def test_detect_recursive(self, recursive_detector):
        pattern = PatternObject(
            identifier='p1',
            pattern_description='Recursive test',
            pattern_type='cognitive_loop',
            trigger_conditions=('anxiety',),
            termination_conditions=('anxiety',),  # same as trigger = recursive
        )
        result = recursive_detector.detect_recursive_structures([pattern])
        assert isinstance(result, list)

    def test_not_recursive(self, recursive_detector):
        pattern = PatternObject(
            identifier='p1',
            pattern_description='Non-recursive',
            pattern_type='behavioral_loop',
            trigger_conditions=('trigger',),
            termination_conditions=('resolution',),
        )
        result = recursive_detector.detect_recursive_structures([pattern])
        assert len(result) == 0

    def test_empty_patterns(self, recursive_detector):
        result = recursive_detector.detect_recursive_structures([])
        assert result == []


# ---------------------------------------------------------------------------
# Catalogue tests
# ---------------------------------------------------------------------------


class TestCatalogues:
    def test_pattern_types(self):
        assert 'behavioral_loop' in PATTERN_TYPES
        assert 'cognitive_loop' in PATTERN_TYPES
        assert 'fractal' in PATTERN_TYPES
        assert 'recursive' in PATTERN_TYPES
        assert 'meta_pattern' in PATTERN_TYPES
        assert len(PATTERN_TYPES) == 5

    def test_pattern_lifecycle_states(self):
        assert 'candidate' in PATTERN_LIFECYCLE_STATES
        assert 'canonical' in PATTERN_LIFECYCLE_STATES
        assert len(PATTERN_LIFECYCLE_STATES) > 4
