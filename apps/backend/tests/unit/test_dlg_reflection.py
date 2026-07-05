"""Tests for DLG-04 Reflection Timing."""

from __future__ import annotations

import pytest

from ayeneh.dlg.reflection.engine import ReflectionTimingEngine
from ayeneh.dlg.reflection.trigger import ReflectionTriggerDetector
from ayeneh.dlg.reflection.types import (
    REFLECTION_CATEGORIES,
    REFLECTION_INTENSITY_LEVELS,
    REFLECTION_TRIGGERS,
    DetectedPattern,
    EstimatedBenefit,
    EstimatedReadiness,
    EstimatedRisk,
    OpportunityIdentifier,
    ReflectionEvidence,
    ReflectionIntensity,
    ReflectionOpportunity,
    TRIGGER_TO_CATEGORY,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> ReflectionTimingEngine:
    return ReflectionTimingEngine()


@pytest.fixture
def detector() -> ReflectionTriggerDetector:
    return ReflectionTriggerDetector()


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestReflectionTypes:
    def test_triggers_count(self) -> None:
        assert len(REFLECTION_TRIGGERS) == 9

    def test_trigger_values(self) -> None:
        assert 'recurring_behavioral_pattern' in REFLECTION_TRIGGERS
        assert 'reality_distortion' in REFLECTION_TRIGGERS
        assert 'project_phase_completion' in REFLECTION_TRIGGERS

    def test_categories_count(self) -> None:
        assert len(REFLECTION_CATEGORIES) == 9

    def test_category_values(self) -> None:
        assert 'behavioral' in REFLECTION_CATEGORIES
        assert 'meta_cognitive' in REFLECTION_CATEGORIES

    def test_intensity_levels_count(self) -> None:
        assert len(REFLECTION_INTENSITY_LEVELS) == 4

    def test_intensity_levels_values(self) -> None:
        assert 'gentle' in REFLECTION_INTENSITY_LEVELS
        assert 'deep_cognitive_intervention' in REFLECTION_INTENSITY_LEVELS

    def test_trigger_to_category_map(self) -> None:
        assert len(TRIGGER_TO_CATEGORY) == 9
        assert TRIGGER_TO_CATEGORY['recurring_behavioral_pattern'] == 'behavioral'
        assert TRIGGER_TO_CATEGORY['reality_distortion'] == 'reality_calibration'

    def test_opportunity_identifier_frozen(self) -> None:
        oi = OpportunityIdentifier(id='test-id')
        with pytest.raises(AttributeError):
            oi.id = 'other'  # type: ignore[misc]

    def test_detected_pattern_defaults(self) -> None:
        dp = DetectedPattern()
        assert dp.pattern_type == ''
        assert dp.strength == 0.0

    def test_reflection_evidence_defaults(self) -> None:
        re = ReflectionEvidence()
        assert re.evidence_type == ''
        assert re.strength == 0.0

    def test_estimated_readiness_defaults(self) -> None:
        er = EstimatedReadiness()
        assert er.overall_readiness == 0.5

    def test_estimated_benefit_defaults(self) -> None:
        eb = EstimatedBenefit()
        assert eb.overall_benefit == 0.0

    def test_estimated_risk_defaults(self) -> None:
        er = EstimatedRisk()
        assert er.overall_risk == 0.0

    def test_reflection_opportunity_frozen(self) -> None:
        ro = ReflectionOpportunity()
        with pytest.raises(AttributeError):
            ro.urgency = 0.9  # type: ignore[misc]

    def test_intensity_gentle(self) -> None:
        i = ReflectionIntensity.gentle()
        assert i.level == 1
        assert i.label == 'gentle'
        assert i.follow_up_required is False

    def test_intensity_exploratory(self) -> None:
        i = ReflectionIntensity.exploratory()
        assert i.level == 2
        assert i.follow_up_required is True

    def test_intensity_pattern_proposal(self) -> None:
        i = ReflectionIntensity.pattern_proposal()
        assert i.level == 3

    def test_intensity_deep(self) -> None:
        i = ReflectionIntensity.deep_cognitive_intervention()
        assert i.level == 4
        assert i.max_depth == 4


# ---------------------------------------------------------------------------
# Trigger detector tests
# ---------------------------------------------------------------------------


class TestReflectionTriggerDetector:
    def test_detect_empty_context(self, detector: ReflectionTriggerDetector) -> None:
        patterns = detector.detect({})
        assert isinstance(patterns, list)

    def test_detect_none_context(self, detector: ReflectionTriggerDetector) -> None:
        patterns = detector.detect(None)
        assert isinstance(patterns, list)

    def test_detect_behavioral_pattern(self, detector: ReflectionTriggerDetector) -> None:
        ctx = {
            'behavioral_patterns': [
                {'description': 'Procrastination', 'frequency': 5},
            ],
        }
        patterns = detector.detect(ctx)
        types = [p.pattern_type for p in patterns]
        assert 'recurring_behavioral_pattern' in types

    def test_detect_behavioral_low_freq(self, detector: ReflectionTriggerDetector) -> None:
        ctx = {
            'behavioral_patterns': [
                {'description': 'Rare behavior', 'frequency': 1},
            ],
        }
        patterns = detector.detect(ctx)
        behavioral = [p for p in patterns if p.pattern_type == 'recurring_behavioral_pattern']
        assert len(behavioral) == 0

    def test_detect_narrative_repetition(self, detector: ReflectionTriggerDetector) -> None:
        ctx = {
            'narratives': [
                {'text': 'I always fail at things'},
                {'text': 'I always fail at things'},
            ],
        }
        patterns = detector.detect(ctx)
        types = [p.pattern_type for p in patterns]
        assert 'repeated_narrative' in types

    def test_detect_identity_contradiction(self, detector: ReflectionTriggerDetector) -> None:
        ctx = {
            'identity_signals': [
                {'type': 'ambition'},
                {'type': 'ambition'},
            ],
        }
        patterns = detector.detect(ctx)
        types = [p.pattern_type for p in patterns]
        assert 'identity_contradiction' in types

    def test_detect_reality_distortion(self, detector: ReflectionTriggerDetector) -> None:
        ctx = {
            'reality_distortions': [
                {'severity': 0.8, 'description': 'Overestimating abilities'},
            ],
        }
        patterns = detector.detect(ctx)
        types = [p.pattern_type for p in patterns]
        assert 'reality_distortion' in types

    def test_detect_reality_distortion_low(self, detector: ReflectionTriggerDetector) -> None:
        ctx = {
            'reality_distortions': [
                {'severity': 0.2, 'description': 'Minor issue'},
            ],
        }
        patterns = detector.detect(ctx)
        distortions = [p for p in patterns if p.pattern_type == 'reality_distortion']
        assert len(distortions) == 0

    def test_detect_developmental_transition(self, detector: ReflectionTriggerDetector) -> None:
        ctx = {
            'developmental_signals': [
                {'is_transition': True, 'description': 'Career change', 'strength': 0.8},
            ],
        }
        patterns = detector.detect(ctx)
        types = [p.pattern_type for p in patterns]
        assert 'major_developmental_transition' in types

    def test_detect_multiple_patterns(self, detector: ReflectionTriggerDetector) -> None:
        ctx = {
            'behavioral_patterns': [
                {'description': 'Pattern A', 'frequency': 5},
            ],
            'narratives': [
                {'text': 'Same story'},
                {'text': 'Same story'},
            ],
        }
        patterns = detector.detect(ctx)
        assert len(patterns) >= 2


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestReflectionTimingEngine:
    def test_process_returns_none_or_opportunity(
        self, engine: ReflectionTimingEngine,
    ) -> None:
        result = engine.process({})
        assert result is None or isinstance(result, ReflectionOpportunity)

    def test_process_empty_context(self, engine: ReflectionTimingEngine) -> None:
        result = engine.process({})
        assert result is None

    def test_process_with_dict_context(self, engine: ReflectionTimingEngine) -> None:
        result = engine.process({'depth': 3, 'engagement_level': 0.8})
        assert result is None or isinstance(result, ReflectionOpportunity)

    def test_process_with_patterns(self, engine: ReflectionTimingEngine) -> None:
        patterns = [{'type': 'recurring_behavioral_pattern', 'description': 'Test', 'strength': 0.8}]
        result = engine.process({}, behavioral_patterns=patterns)
        assert isinstance(result, ReflectionOpportunity)

    def test_process_low_strength_pattern(self, engine: ReflectionTimingEngine) -> None:
        patterns = [{'type': 'recurring_behavioral_pattern', 'description': 'Weak', 'strength': 0.1}]
        result = engine.process({}, behavioral_patterns=patterns)
        assert result is None

    def test_process_with_history(self, engine: ReflectionTimingEngine) -> None:
        result = engine.process({}, conversation_history=['msg1', 'msg2'])
        assert result is None or isinstance(result, ReflectionOpportunity)

    def test_process_with_behavioral_patterns(self, engine: ReflectionTimingEngine) -> None:
        bp = [{'type': 'behavioral', 'description': 'Pattern', 'frequency': 5}]
        result = engine.process({}, behavioral_patterns=bp)
        assert isinstance(result, ReflectionOpportunity)
        assert result.urgency > 0.0

    def test_process_readiness_estimation(self, engine: ReflectionTimingEngine) -> None:
        patterns = [{'type': 'recurring_behavioral_pattern', 'description': 'X', 'strength': 0.9}]
        result = engine.process(
            {'engagement_level': 0.9, 'emotional_valence': 0.1},
            behavioral_patterns=patterns,
        )
        if result is not None:
            assert result.estimated_readiness.overall_readiness > 0.0
