"""Tests for the COG-15 Reality Calibration pipeline."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.cog.reality_calibration.types import (
    CALIBRATION_STATES,
    EVIDENCE_HIERARCHY,
    CalibrationObject,
    MentalStoryObject,
)
from ayeneh.cog.reality_calibration.engine import (
    RealityCalibrationEngine,
    CalibrationResult,
)
from ayeneh.cog.reality_calibration.fusion import (
    CognitiveFusionDetector,
    FusionResult,
    NarrativeFusionDetector,
    OBJECT_TYPES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def calibration_engine():
    return RealityCalibrationEngine()


@pytest.fixture
def fusion_detector():
    return CognitiveFusionDetector()


@pytest.fixture
def narrative_fusion_detector():
    return NarrativeFusionDetector()


@pytest.fixture
def sample_evidence():
    return [
        {'identifier': 'ev-1', 'type': 'observation', 'text': 'The person arrived late'},
        {'identifier': 'ev-2', 'type': 'self_report', 'text': 'I always try my best'},
        {'identifier': 'ev-3', 'type': 'behavioral_report', 'text': 'They worked hard every day'},
    ]


@pytest.fixture
def sample_narratives():
    return [
        {'identifier': 'narr-1', 'text': 'The person believes in hard work', 'summary': 'Hard work narrative', 'influence_score': 0.8, 'confidence': 0.7, 'core_assumptions': ('effort equals success',), 'emotional_associations': ('pride',)},
        {'identifier': 'narr-2', 'text': 'Life is a struggle', 'summary': 'Struggle narrative', 'influence_score': 0.6, 'confidence': 0.5},
    ]


@pytest.fixture
def sample_beliefs():
    return [
        {'identifier': 'b-1', 'belief_statement': 'Hard work always pays off', 'strength': 0.7, 'influence': 0.8, 'identity_coupling_score': 0.6},
        {'identifier': 'b-2', 'belief_statement': 'I must be perfect', 'strength': 0.9, 'influence': 0.7, 'identity_coupling_score': 0.8},
    ]


@pytest.fixture
def sample_identity():
    return [
        {'identifier': 'id-1', 'identity_statement': 'I am a hard worker', 'confidence': 0.8, 'centrality': 0.9, 'narrative_identification_score': 0.7},
    ]


# ---------------------------------------------------------------------------
# CalibrationObject tests
# ---------------------------------------------------------------------------


class TestCalibrationObject:
    def test_creation(self):
        obj = CalibrationObject(identifier='c1', observed_event='test event')
        assert obj.identifier == 'c1'
        assert obj.observed_event == 'test event'

    def test_defaults(self):
        obj = CalibrationObject(identifier='c2', observed_event='event')
        assert obj.confidence == 0.0
        assert obj.evidence_quality == 0.0
        assert obj.calibration_status == 'unknown'
        assert obj.evidence_level == 8
        assert obj.identity_involvement == 0.0
        assert obj.specification_version == '1.0.0'

    def test_frozen(self):
        obj = CalibrationObject(identifier='c3', observed_event='event')
        with pytest.raises(AttributeError):
            obj.confidence = 0.5  # type: ignore[misc]

    def test_evidence_tuples(self):
        obj = CalibrationObject(
            identifier='c4',
            observed_event='event',
            available_evidence=('ev-1', 'ev-2'),
            interpretations=('interp-1',),
            narratives=('narr-1',),
        )
        assert len(obj.available_evidence) == 2
        assert len(obj.interpretations) == 1
        assert len(obj.narratives) == 1

    def test_calibration_states(self):
        assert 'well_anchored' in CALIBRATION_STATES
        assert 'contradicted' in CALIBRATION_STATES
        assert 'unknown' in CALIBRATION_STATES
        assert len(CALIBRATION_STATES) == 7

    def test_evidence_hierarchy(self):
        assert EVIDENCE_HIERARCHY[1] == 'direct_repeated_observation'
        assert EVIDENCE_HIERARCHY[8] == 'speculation'
        assert len(EVIDENCE_HIERARCHY) == 8


# ---------------------------------------------------------------------------
# MentalStoryObject tests
# ---------------------------------------------------------------------------


class TestMentalStoryObject:
    def test_creation(self):
        story = MentalStoryObject(story_id='s1', description='A story about growth')
        assert story.story_id == 's1'
        assert story.description == 'A story about growth'

    def test_defaults(self):
        story = MentalStoryObject(story_id='s2', description='test')
        assert story.story_reality_distance == 0.0
        assert story.narrative_gravity == 0.0
        assert story.cognitive_fusion_level == 0.0
        assert story.identity_involvement == 0.0

    def test_frozen(self):
        story = MentalStoryObject(story_id='s3', description='test')
        with pytest.raises(AttributeError):
            story.story_reality_distance = 0.5  # type: ignore[misc]

    def test_tuples(self):
        story = MentalStoryObject(
            story_id='s4',
            description='test',
            actors=('actor1', 'actor2'),
            roles=('role1',),
            rules=('rule1', 'rule2'),
        )
        assert len(story.actors) == 2
        assert len(story.roles) == 1
        assert len(story.rules) == 2


# ---------------------------------------------------------------------------
# RealityCalibrationEngine tests
# ---------------------------------------------------------------------------


class TestRealityCalibrationEngine:
    def test_process_returns_result(self, calibration_engine, sample_evidence):
        result = calibration_engine.process(sample_evidence)
        assert isinstance(result, CalibrationResult)

    def test_calibrations_created(self, calibration_engine, sample_evidence):
        result = calibration_engine.process(sample_evidence)
        assert len(result.calibrations) > 0

    def test_calibrations_have_identifiers(self, calibration_engine, sample_evidence):
        result = calibration_engine.process(sample_evidence)
        for cal in result.calibrations:
            assert cal.identifier
            assert isinstance(cal.identifier, str)

    def test_calibrations_have_valid_status(self, calibration_engine, sample_evidence):
        result = calibration_engine.process(sample_evidence)
        for cal in result.calibrations:
            assert cal.calibration_status in CALIBRATION_STATES

    def test_calibrations_have_valid_evidence_level(self, calibration_engine, sample_evidence):
        result = calibration_engine.process(sample_evidence)
        for cal in result.calibrations:
            assert 1 <= cal.evidence_level <= 8

    def test_metrics_computed(self, calibration_engine, sample_evidence):
        result = calibration_engine.process(sample_evidence)
        for cal in result.calibrations:
            assert 0.0 <= cal.confidence <= 1.0
            assert 0.0 <= cal.evidence_quality <= 1.0

    def test_with_narratives(self, calibration_engine, sample_evidence, sample_narratives):
        result = calibration_engine.process(sample_evidence, narratives=sample_narratives)
        assert len(result.calibrations) > 0

    def test_with_beliefs(self, calibration_engine, sample_evidence, sample_beliefs):
        result = calibration_engine.process(sample_evidence, beliefs=sample_beliefs)
        assert len(result.calibrations) > 0

    def test_mental_stories_extracted(self, calibration_engine, sample_narratives):
        result = calibration_engine.process([], narratives=sample_narratives)
        assert len(result.mental_stories) > 0

    def test_mental_stories_have_ids(self, calibration_engine, sample_narratives):
        result = calibration_engine.process([], narratives=sample_narratives)
        for story in result.mental_stories:
            assert story.story_id
            assert story.description

    def test_distances_computed(self, calibration_engine, sample_evidence, sample_narratives):
        result = calibration_engine.process(sample_evidence, narratives=sample_narratives)
        assert isinstance(result.distances, dict)

    def test_fusion_detected(self, calibration_engine, sample_evidence, sample_beliefs, sample_identity):
        result = calibration_engine.process(
            sample_evidence, beliefs=sample_beliefs, identity=sample_identity,
        )
        assert isinstance(result.fusion_levels, list)

    def test_narrative_gravity_computed(self, calibration_engine, sample_evidence, sample_narratives):
        result = calibration_engine.process(sample_evidence, narratives=sample_narratives)
        assert isinstance(result.narrative_gravities, dict)

    def test_awakening_index_computed(self, calibration_engine, sample_evidence):
        result = calibration_engine.process(sample_evidence)
        assert 0.0 <= result.awakening_index <= 1.0

    def test_empty_evidence(self, calibration_engine):
        result = calibration_engine.process([])
        assert len(result.calibrations) == 0

    def test_empty_all_inputs(self, calibration_engine):
        result = calibration_engine.process([])
        assert result.awakening_index == 0.0

    def test_processing_timestamp(self, calibration_engine, sample_evidence):
        result = calibration_engine.process(sample_evidence)
        assert isinstance(result.processing_timestamp, datetime)


# ---------------------------------------------------------------------------
# CognitiveFusionDetector tests
# ---------------------------------------------------------------------------


class TestCognitiveFusionDetector:
    def test_detect_empty(self, fusion_detector):
        results = fusion_detector.detect([], [], [])
        assert results == []

    def test_detect_identity_fusion(self, fusion_detector):
        identity = [{'identifier': 'id-1', 'confidence': 0.9, 'centrality': 0.8}]
        results = fusion_detector.detect(identity, [], [])
        assert len(results) == 1
        assert results[0].object_type == 'identity'
        assert results[0].fusion_level > 0.0

    def test_detect_narrative_fusion(self, fusion_detector):
        narratives = [{'identifier': 'n-1', 'influence_score': 0.8, 'confidence': 0.7, 'core_assumptions': ('rule1',)}]
        results = fusion_detector.detect([], narratives, [])
        assert len(results) == 1
        assert results[0].object_type == 'narrative'

    def test_detect_belief_fusion(self, fusion_detector):
        beliefs = [{'identifier': 'b-1', 'strength': 0.8, 'identity_coupling_score': 0.9, 'influence': 0.7}]
        results = fusion_detector.detect([], [], beliefs)
        assert len(results) == 1
        assert results[0].object_type == 'belief'

    def test_fusion_level_range(self, fusion_detector):
        identity = [{'identifier': 'id-1', 'confidence': 1.0, 'centrality': 1.0, 'narrative_identification_score': 1.0}]
        results = fusion_detector.detect(identity, [], [])
        assert results[0].fusion_level <= 1.0

    def test_fusion_result_frozen(self):
        result = FusionResult(object_id='o1', object_type='thought', fusion_level=0.5)
        with pytest.raises(AttributeError):
            result.fusion_level = 0.8  # type: ignore[misc]

    def test_object_types(self):
        assert 'thought' in OBJECT_TYPES
        assert 'narrative' in OBJECT_TYPES
        assert 'belief' in OBJECT_TYPES
        assert 'identity' in OBJECT_TYPES
        assert len(OBJECT_TYPES) == 6


# ---------------------------------------------------------------------------
# NarrativeFusionDetector tests
# ---------------------------------------------------------------------------


class TestNarrativeFusionDetector:
    def test_detect_empty(self, narrative_fusion_detector):
        results = narrative_fusion_detector.detect([], [])
        assert results == []

    def test_detect_fused_narrative(self, narrative_fusion_detector):
        narratives = [{'identifier': 'n-1', 'influence_score': 0.9, 'confidence': 0.8}]
        evidence = [{'identifier': 'ev-1', 'text': 'something'}]
        results = narrative_fusion_detector.detect(narratives, evidence)
        assert len(results) == 1
        assert results[0].object_type == 'narrative'

    def test_grounded_narrative_low_fusion(self, narrative_fusion_detector):
        narratives = [{
            'identifier': 'n-1',
            'influence_score': 0.3,
            'confidence': 0.3,
            'supporting_evidence': ('ev-1',),
        }]
        evidence = [{'identifier': 'ev-1'}]
        results = narrative_fusion_detector.detect(narratives, evidence)
        if results:
            assert results[0].fusion_level < 0.5

    def test_fusion_result_has_timestamp(self):
        result = FusionResult(object_id='o1', object_type='narrative')
        assert isinstance(result.creation_timestamp, datetime)
