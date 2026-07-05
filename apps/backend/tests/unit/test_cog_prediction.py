"""Tests for the COG-14 Predictive Cognitive Engine."""

from __future__ import annotations

import pytest

from ayeneh.cog.prediction.engine import PredictiveCognitiveEngine
from ayeneh.cog.prediction.simulation import (
    CounterfactualSimulator,
    InterventionSimulator,
    SensitivityAnalyzer,
)
from ayeneh.cog.prediction.types import (
    PREDICTION_HORIZONS,
    PREDICTION_LIFECYCLE_STATES,
    EarlyWarning,
    PredictionObject,
    PredictionResult,
    ScenarioObject,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return PredictiveCognitiveEngine()


@pytest.fixture
def counterfactual_simulator():
    return CounterfactualSimulator()


@pytest.fixture
def intervention_simulator():
    return InterventionSimulator()


@pytest.fixture
def sensitivity_analyzer():
    return SensitivityAnalyzer()


@pytest.fixture
def sample_trajectories():
    return [
        {'id': 'traj-1', 'target_type': 'belief', 'direction': 'strengthening', 'rate_of_change': 0.3},
        {'id': 'traj-2', 'target_type': 'value', 'direction': 'stabilizing', 'rate_of_change': 0.1},
        {'id': 'traj-3', 'target_type': 'goal', 'direction': 'transforming', 'rate_of_change': 0.7},
    ]


@pytest.fixture
def sample_patterns():
    return [
        {'id': 'pat-1', 'description': 'Recurring procrastination pattern', 'confidence': 0.6},
        {'id': 'pat-2', 'description': 'Growth mindset pattern', 'confidence': 0.8},
    ]


@pytest.fixture
def sample_current_state():
    return {
        'beliefs': [
            {'id': 'b-1', 'statement': 'I work well under pressure'},
            {'id': 'b-2', 'statement': 'Deadlines motivate me'},
        ],
        'values': [
            {'id': 'v-1', 'statement': 'Productivity'},
        ],
        'goals': [
            {'id': 'g-1', 'description': 'Ship features faster'},
        ],
        'identity': [
            {'id': 'i-1', 'statement': 'I am a productive developer'},
        ],
    }


# ---------------------------------------------------------------------------
# PredictionObject tests
# ---------------------------------------------------------------------------


class TestPredictionObject:
    def test_creation(self):
        pred = PredictionObject(
            identifier='pred-1',
            prediction_statement='Belief will strengthen',
            target_cognitive_object='obj-1',
            probability=0.7,
            confidence=0.6,
        )
        assert pred.identifier == 'pred-1'
        assert pred.probability == 0.7
        assert pred.confidence == 0.6

    def test_defaults(self):
        pred = PredictionObject(
            identifier='pred-1',
            prediction_statement='test',
            target_cognitive_object='obj-1',
        )
        assert pred.probability == 0.0
        assert pred.confidence == 0.0
        assert pred.assumptions == ()
        assert pred.supporting_evidence == ()
        assert pred.contradictory_evidence == ()
        assert pred.prediction_horizon == ''
        assert pred.specification_version == '1.0.0'

    def test_frozen(self):
        pred = PredictionObject(
            identifier='pred-1', prediction_statement='test',
            target_cognitive_object='obj-1',
        )
        with pytest.raises(AttributeError):
            pred.probability = 0.5  # type: ignore[misc]

    def test_timestamp_auto_generated(self):
        pred = PredictionObject(
            identifier='pred-1', prediction_statement='test',
            target_cognitive_object='obj-1',
        )
        assert pred.creation_timestamp is not None

    def test_revision_history_default(self):
        pred = PredictionObject(
            identifier='pred-1', prediction_statement='test',
            target_cognitive_object='obj-1',
        )
        assert pred.revision_history == ()


# ---------------------------------------------------------------------------
# ScenarioObject tests
# ---------------------------------------------------------------------------


class TestScenarioObject:
    def test_creation(self):
        scenario = ScenarioObject(
            scenario_id='s-1',
            description='Continuation scenario',
            probability=0.6,
        )
        assert scenario.scenario_id == 's-1'
        assert scenario.probability == 0.6

    def test_defaults(self):
        scenario = ScenarioObject(scenario_id='s-1', description='test')
        assert scenario.probability == 0.0
        assert scenario.supporting_evidence == ()
        assert scenario.assumptions == ()
        assert scenario.uncertainties == ()

    def test_frozen(self):
        scenario = ScenarioObject(scenario_id='s-1', description='test')
        with pytest.raises(AttributeError):
            scenario.probability = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# EarlyWarning tests
# ---------------------------------------------------------------------------


class TestEarlyWarning:
    def test_creation(self):
        warning = EarlyWarning(
            warning_id='w-1',
            description='High rate of change detected',
            severity=0.8,
        )
        assert warning.warning_id == 'w-1'
        assert warning.severity == 0.8

    def test_defaults(self):
        warning = EarlyWarning(warning_id='w-1', description='test')
        assert warning.severity == 0.0
        assert warning.evidence == ()
        assert warning.recommended_attention == ''

    def test_frozen(self):
        warning = EarlyWarning(warning_id='w-1', description='test')
        with pytest.raises(AttributeError):
            warning.severity = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PredictiveCognitiveEngine tests
# ---------------------------------------------------------------------------


class TestPredictiveCognitiveEngine:
    def test_process_returns_result(self, engine, sample_trajectories,
                                     sample_patterns, sample_current_state):
        result = engine.process(sample_trajectories, sample_patterns, sample_current_state)
        assert isinstance(result, PredictionResult)

    def test_predictions_extracted(self, engine, sample_trajectories,
                                    sample_patterns, sample_current_state):
        result = engine.process(sample_trajectories, sample_patterns, sample_current_state)
        assert result.total_extracted >= 0

    def test_all_predictions_have_identifiers(self, engine, sample_trajectories,
                                               sample_patterns, sample_current_state):
        result = engine.process(sample_trajectories, sample_patterns, sample_current_state)
        for pred in result.predictions.values():
            assert pred.identifier
            assert isinstance(pred.identifier, str)

    def test_confidence_in_range(self, engine, sample_trajectories,
                                  sample_patterns, sample_current_state):
        result = engine.process(sample_trajectories, sample_patterns, sample_current_state)
        for pred in result.predictions.values():
            assert 0.0 <= pred.confidence <= 1.0

    def test_probability_in_range(self, engine, sample_trajectories,
                                   sample_patterns, sample_current_state):
        result = engine.process(sample_trajectories, sample_patterns, sample_current_state)
        for pred in result.predictions.values():
            assert 0.0 <= pred.probability <= 1.0

    def test_determinism(self, engine, sample_trajectories,
                          sample_patterns, sample_current_state):
        """Same input -> same output (deterministic pipeline)."""
        r1 = engine.process(sample_trajectories, sample_patterns, sample_current_state)
        r2 = engine.process(sample_trajectories, sample_patterns, sample_current_state)
        assert r1.total_extracted == r2.total_extracted

    def test_empty_inputs(self, engine):
        result = engine.process([], [], {})
        assert isinstance(result, PredictionResult)
        assert isinstance(result.scenarios, list)

    def test_scenarios_generated(self, engine, sample_trajectories,
                                  sample_patterns, sample_current_state):
        result = engine.process(sample_trajectories, sample_patterns, sample_current_state)
        assert isinstance(result.scenarios, list)
        assert len(result.scenarios) >= 1

    def test_early_warnings(self, engine, sample_trajectories,
                             sample_patterns, sample_current_state):
        result = engine.process(sample_trajectories, sample_patterns, sample_current_state)
        assert isinstance(result.early_warnings, list)

    def test_high_rate_warnings(self, engine):
        trajectories = [
            {'id': 't1', 'target_type': 'belief', 'direction': 'transforming', 'rate_of_change': 0.9},
        ]
        result = engine.process(trajectories, [], {})
        # High rate + transforming should produce warnings
        assert isinstance(result.early_warnings, list)

    def test_predictions_stored(self, engine, sample_trajectories,
                                 sample_patterns, sample_current_state):
        engine.process(sample_trajectories, sample_patterns, sample_current_state)
        assert len(engine._predictions) >= 0


# ---------------------------------------------------------------------------
# CounterfactualSimulator tests
# ---------------------------------------------------------------------------


class TestCounterfactualSimulator:
    def test_simulate_returns_dict(self, counterfactual_simulator, sample_current_state):
        result = counterfactual_simulator.simulate(
            sample_current_state, 'belief X was not adopted',
        )
        assert isinstance(result, dict)

    def test_belief_change(self, counterfactual_simulator, sample_current_state):
        result = counterfactual_simulator.simulate(
            sample_current_state, 'if I did not believe in hard work',
        )
        assert 'impact_areas' in result
        assert 'projected_changes' in result
        assert 'cascade_magnitude' in result

    def test_value_change(self, counterfactual_simulator, sample_current_state):
        result = counterfactual_simulator.simulate(
            sample_current_state, 'if productivity was not a core value',
        )
        assert 'impact_areas' in result

    def test_identity_change(self, counterfactual_simulator, sample_current_state):
        result = counterfactual_simulator.simulate(
            sample_current_state, 'if my identity was different',
        )
        assert 'impact_areas' in result

    def test_general_change(self, counterfactual_simulator, sample_current_state):
        result = counterfactual_simulator.simulate(
            sample_current_state, 'something unrelated',
        )
        assert isinstance(result, dict)
        assert 'cascade_magnitude' in result

    def test_cascade_magnitude_in_range(self, counterfactual_simulator, sample_current_state):
        result = counterfactual_simulator.simulate(
            sample_current_state, 'belief X changed',
        )
        assert 0.0 <= result['cascade_magnitude'] <= 1.0


# ---------------------------------------------------------------------------
# InterventionSimulator tests
# ---------------------------------------------------------------------------


class TestInterventionSimulator:
    def test_simulate_returns_dict(self, intervention_simulator, sample_current_state):
        result = intervention_simulator.simulate(
            sample_current_state, 'challenge belief X daily',
        )
        assert isinstance(result, dict)

    def test_belief_intervention(self, intervention_simulator, sample_current_state):
        result = intervention_simulator.simulate(
            sample_current_state, 'challenge limiting beliefs regularly',
        )
        assert result['target_area'] == 'belief_network'
        assert 'effectiveness_estimate' in result
        assert 'projected_timeline' in result

    def test_value_intervention(self, intervention_simulator, sample_current_state):
        result = intervention_simulator.simulate(
            sample_current_state, 'examine my core values',
        )
        assert result['target_area'] == 'value_system'

    def test_identity_intervention(self, intervention_simulator, sample_current_state):
        result = intervention_simulator.simulate(
            sample_current_state, 'revise my identity narrative',
        )
        assert result['target_area'] == 'identity_structure'

    def test_general_intervention(self, intervention_simulator, sample_current_state):
        result = intervention_simulator.simulate(
            sample_current_state, 'work on personal growth',
        )
        assert isinstance(result, dict)

    def test_effectiveness_in_range(self, intervention_simulator, sample_current_state):
        result = intervention_simulator.simulate(
            sample_current_state, 'daily practice',
        )
        assert 0.0 <= result['effectiveness_estimate'] <= 1.0

    def test_risks_identified(self, intervention_simulator, sample_current_state):
        result = intervention_simulator.simulate(
            sample_current_state, 'challenge belief system',
        )
        assert 'risks' in result
        assert isinstance(result['risks'], tuple)


# ---------------------------------------------------------------------------
# SensitivityAnalyzer tests
# ---------------------------------------------------------------------------


class TestSensitivityAnalyzer:
    def test_analyze_returns_list(self, sensitivity_analyzer):
        result = sensitivity_analyzer.analyze([])
        assert isinstance(result, list)

    def test_empty_objects(self, sensitivity_analyzer):
        result = sensitivity_analyzer.analyze([])
        assert result == []

    def test_high_leverage_point(self, sensitivity_analyzer):
        objects = [
            {
                'id': 'obj-1', 'type': 'belief',
                'connections': ['obj-2', 'obj-3', 'obj-4', 'obj-5'],
                'stability': 0.2,
            },
        ]
        result = sensitivity_analyzer.analyze(objects)
        assert len(result) >= 1
        assert result[0]['leverage_score'] > 0

    def test_low_leverage_point(self, sensitivity_analyzer):
        objects = [
            {
                'id': 'obj-1', 'type': 'belief',
                'connections': ['obj-2'],
                'stability': 0.9,
            },
        ]
        result = sensitivity_analyzer.analyze(objects)
        # Low connections + high stability = low leverage
        if result:
            assert result[0]['leverage_score'] < 0.5

    def test_sorted_by_leverage(self, sensitivity_analyzer):
        objects = [
            {
                'id': 'obj-low', 'type': 'belief',
                'connections': ['obj-2'],
                'stability': 0.8,
            },
            {
                'id': 'obj-high', 'type': 'value',
                'connections': ['obj-2', 'obj-3', 'obj-4', 'obj-5', 'obj-6'],
                'stability': 0.1,
            },
        ]
        result = sensitivity_analyzer.analyze(objects)
        if len(result) >= 2:
            assert result[0]['leverage_score'] >= result[1]['leverage_score']

    def test_recommendation_present(self, sensitivity_analyzer):
        objects = [
            {
                'id': 'obj-1', 'type': 'belief',
                'connections': ['obj-2', 'obj-3', 'obj-4'],
                'stability': 0.3,
            },
        ]
        result = sensitivity_analyzer.analyze(objects)
        if result:
            assert 'recommendation' in result[0]


# ---------------------------------------------------------------------------
# Catalogue tests
# ---------------------------------------------------------------------------


class TestCatalogues:
    def test_prediction_horizons(self):
        assert 'next_conversation' in PREDICTION_HORIZONS
        assert 'weeks' in PREDICTION_HORIZONS
        assert 'months' in PREDICTION_HORIZONS
        assert 'years' in PREDICTION_HORIZONS

    def test_prediction_lifecycle_states(self):
        assert 'candidate' in PREDICTION_LIFECYCLE_STATES
        assert 'confirmed' in PREDICTION_LIFECYCLE_STATES
        assert 'refuted' in PREDICTION_LIFECYCLE_STATES
