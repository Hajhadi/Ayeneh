"""Comprehensive tests for INF-05 Hypothesis Engine."""

from __future__ import annotations

import pytest

from ayeneh.inf.hypothesis.bayesian import BayesianUpdater
from ayeneh.inf.hypothesis.engine import HypothesisEngine
from ayeneh.inf.hypothesis.experiments import (
    CognitiveExperiment,
    ExperimentPlanner,
    ExperimentResult,
)
from ayeneh.inf.hypothesis.types import (
    EVIDENCE_QUALITY_DIMENSIONS,
    HYPOTHESIS_SOURCES,
    HYPOTHESIS_STATUSES,
    HYPOTHESIS_TYPES,
    EvidenceGap,
    EvidenceQuality,
    HypothesisFamily,
    HypothesisObject,
    HypothesisResult,
    PredictedObservation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> HypothesisEngine:
    return HypothesisEngine()


@pytest.fixture
def bayesian() -> BayesianUpdater:
    return BayesianUpdater()


@pytest.fixture
def planner() -> ExperimentPlanner:
    return ExperimentPlanner()


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestHypothesisTypes:
    def test_statuses_populated(self) -> None:
        assert len(HYPOTHESIS_STATUSES) == 6
        assert 'active' in HYPOTHESIS_STATUSES
        assert 'archived' in HYPOTHESIS_STATUSES

    def test_sources_populated(self) -> None:
        assert len(HYPOTHESIS_SOURCES) == 8
        assert 'contradiction' in HYPOTHESIS_SOURCES
        assert 'missing_explanation' in HYPOTHESIS_SOURCES

    def test_hypothesis_types(self) -> None:
        assert len(HYPOTHESIS_TYPES) == 6
        assert 'causal' in HYPOTHESIS_TYPES

    def test_evidence_quality_dimensions(self) -> None:
        assert len(EVIDENCE_QUALITY_DIMENSIONS) == 5

    def test_hypothesis_object_frozen(self) -> None:
        h = HypothesisObject(hypothesis_id='h1')
        with pytest.raises(AttributeError):
            h.hypothesis_id = 'h2'  # type: ignore[misc]

    def test_hypothesis_object_defaults(self) -> None:
        h = HypothesisObject(hypothesis_id='h1')
        assert h.confidence == 0.0
        assert h.current_status == 'active'

    def test_hypothesis_family_frozen(self) -> None:
        f = HypothesisFamily(family_id='f1')
        with pytest.raises(AttributeError):
            f.family_id = 'f2'  # type: ignore[misc]

    def test_hypothesis_result_defaults(self) -> None:
        r = HypothesisResult()
        assert r.overall_confidence == 0.0
        assert len(r.hypotheses) == 0

    def test_evidence_quality_overall(self) -> None:
        q = EvidenceQuality(directness=1.0, specificity=1.0, temporal_proximity=1.0,
                            consistency=1.0, source_reliability=1.0)
        assert q.overall() == pytest.approx(1.0)

    def test_evidence_quality_zero(self) -> None:
        q = EvidenceQuality(directness=0.0, specificity=0.0, temporal_proximity=0.0,
                            consistency=0.0, source_reliability=0.0)
        assert q.overall() == pytest.approx(0.0)

    def test_predicted_observation_defaults(self) -> None:
        p = PredictedObservation()
        assert p.required is True

    def test_evidence_gap_defaults(self) -> None:
        g = EvidenceGap()
        assert g.importance == 0.0

    def test_hypothesis_revision_defaults(self) -> None:
        from ayeneh.inf.hypothesis.types import HypothesisRevision
        r = HypothesisRevision(revision_id='r1')
        assert r.old_confidence == 0.0


# ---------------------------------------------------------------------------
# Bayesian updater tests
# ---------------------------------------------------------------------------


class TestBayesianUpdater:
    def test_update_basic(self, bayesian: BayesianUpdater) -> None:
        result = bayesian.update(prior=0.5, evidence_quality=0.8, likelihood_ratio=2.0)
        assert 0.0 < result < 1.0
        assert result > 0.5

    def test_update_prior_boundary_zero(self, bayesian: BayesianUpdater) -> None:
        result = bayesian.update(prior=0.0, evidence_quality=0.8, likelihood_ratio=2.0)
        assert result == 0.0

    def test_update_prior_boundary_one(self, bayesian: BayesianUpdater) -> None:
        result = bayesian.update(prior=1.0, evidence_quality=0.8, likelihood_ratio=2.0)
        assert result == 1.0

    def test_update_negative_lr(self, bayesian: BayesianUpdater) -> None:
        result = bayesian.update(prior=0.5, evidence_quality=0.8, likelihood_ratio=-1.0)
        assert result == 0.5

    def test_update_zero_lr(self, bayesian: BayesianUpdater) -> None:
        result = bayesian.update(prior=0.5, evidence_quality=0.0, likelihood_ratio=0.0)
        assert result == 0.5

    def test_update_clamped(self, bayesian: BayesianUpdater) -> None:
        result = bayesian.update(prior=0.5, evidence_quality=1.0, likelihood_ratio=100.0)
        assert 0.0 <= result <= 1.0

    def test_batch_update(self, bayesian: BayesianUpdater) -> None:
        evidence = [(0.7, 1.5), (0.8, 2.0), (0.6, 1.2)]
        result = bayesian.batch_update(0.5, evidence)
        assert 0.0 <= result <= 1.0

    def test_batch_update_empty(self, bayesian: BayesianUpdater) -> None:
        result = bayesian.batch_update(0.5, [])
        assert result == 0.5

    def test_odds_update(self, bayesian: BayesianUpdater) -> None:
        result = bayesian.odds_update(1.0, 2.0)
        assert result == 2.0

    def test_probability_to_odds(self, bayesian: BayesianUpdater) -> None:
        assert BayesianUpdater.probability_to_odds(0.5) == pytest.approx(1.0)
        assert BayesianUpdater.probability_to_odds(0.0) == 0.0
        assert BayesianUpdater.probability_to_odds(1.0) == float('inf')

    def test_odds_to_probability(self, bayesian: BayesianUpdater) -> None:
        assert BayesianUpdater.odds_to_probability(1.0) == pytest.approx(0.5)
        assert BayesianUpdater.odds_to_probability(0.0) == 0.0
        assert BayesianUpdater.odds_to_probability(float('inf')) == 1.0


# ---------------------------------------------------------------------------
# Experiment tests
# ---------------------------------------------------------------------------


class TestCognitiveExperiment:
    def test_experiment_frozen(self) -> None:
        e = CognitiveExperiment(experiment_id='e1', hypothesis_id='h1')
        with pytest.raises(AttributeError):
            e.experiment_id = 'e2'  # type: ignore[misc]

    def test_experiment_defaults(self) -> None:
        e = CognitiveExperiment(experiment_id='e1', hypothesis_id='h1')
        assert e.safety_check == 'safe'
        assert e.status == 'planned'


class TestExperimentResult:
    def test_result_frozen(self) -> None:
        r = ExperimentResult(experiment_id='e1')
        with pytest.raises(AttributeError):
            r.experiment_id = 'e2'  # type: ignore[misc]

    def test_result_defaults(self) -> None:
        r = ExperimentResult(experiment_id='e1')
        assert r.supports_hypothesis is False
        assert r.confidence_change == 0.0


class TestExperimentPlanner:
    def test_plan_experiment(self, planner: ExperimentPlanner) -> None:
        exp = planner.plan_experiment('h1', 'X causes Y', ('Y increases',))
        assert exp.hypothesis_id == 'h1'
        assert exp.status == 'planned'
        assert 'X causes Y' in exp.description

    def test_evaluate_result_supports(self, planner: ExperimentPlanner) -> None:
        exp = CognitiveExperiment(experiment_id='e1', hypothesis_id='h1')
        result = planner.evaluate_result(exp, 'Y increased', supports=True)
        assert result.supports_hypothesis is True
        assert result.confidence_change > 0

    def test_evaluate_result_rejects(self, planner: ExperimentPlanner) -> None:
        exp = CognitiveExperiment(experiment_id='e1', hypothesis_id='h1')
        result = planner.evaluate_result(exp, 'Y decreased', supports=False)
        assert result.supports_hypothesis is False
        assert result.confidence_change < 0

    def test_is_safe(self, planner: ExperimentPlanner) -> None:
        exp = CognitiveExperiment(experiment_id='e1', hypothesis_id='h1', safety_check='safe')
        assert planner.is_safe(exp) is True

    def test_is_caution(self, planner: ExperimentPlanner) -> None:
        exp = CognitiveExperiment(experiment_id='e1', hypothesis_id='h1', safety_check='caution')
        assert planner.is_safe(exp) is True

    def test_is_unsafe(self, planner: ExperimentPlanner) -> None:
        exp = CognitiveExperiment(experiment_id='e1', hypothesis_id='h1', safety_check='unsafe')
        assert planner.is_safe(exp) is False


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestHypothesisEngine:
    def test_process_returns_result(self, engine: HypothesisEngine) -> None:
        result = engine.process([])
        assert isinstance(result, HypothesisResult)

    def test_process_empty_evidence(self, engine: HypothesisEngine) -> None:
        result = engine.process([])
        assert result.overall_confidence >= 0.0

    def test_process_with_dict_evidence(self, engine: HypothesisEngine) -> None:
        evidence = [
            {'id': 'e1', 'type': 'behavioral', 'quality': 0.8, 'content': 'observed X'},
            {'id': 'e2', 'type': 'behavioral', 'quality': 0.7, 'content': 'observed X again'},
        ]
        result = engine.process(evidence)
        assert isinstance(result, HypothesisResult)
        assert len(result.hypotheses) >= 1

    def test_process_with_context(self, engine: HypothesisEngine) -> None:
        result = engine.process([], context={'session_id': 's1'})
        assert result.processing_metadata.get('session_id') == 's1'

    def test_process_with_graph(self, engine: HypothesisEngine) -> None:
        evidence = [{'id': 'e1', 'type': 'behavioral', 'quality': 0.8}]
        result = engine.process(evidence, graph={'nodes': []})
        assert isinstance(result, HypothesisResult)

    def test_competing_hypotheses_populated(self, engine: HypothesisEngine) -> None:
        evidence = [
            {'id': 'e1', 'type': 'belief', 'quality': 0.8},
            {'id': 'e2', 'type': 'belief', 'quality': 0.7},
            {'id': 'e3', 'type': 'belief', 'quality': 0.6},
        ]
        result = engine.process(evidence)
        for hyp in result.hypotheses:
            if len(result.hypotheses) > 1:
                assert len(hyp.competing_hypotheses) > 0

    def test_families_grouped(self, engine: HypothesisEngine) -> None:
        evidence = [
            {'id': 'e1', 'type': 'behavioral', 'quality': 0.8},
            {'id': 'e2', 'type': 'behavioral', 'quality': 0.7},
        ]
        result = engine.process(evidence)
        assert len(result.families) >= 1

    def test_predictions_populated(self, engine: HypothesisEngine) -> None:
        evidence = [{'id': 'e1', 'type': 'behavioral', 'quality': 0.8}]
        result = engine.process(evidence)
        # Single evidence → hypothesis stays active → predictions generated
        if result.hypotheses and result.hypotheses[0].current_status in ('active', 'strengthening'):
            assert len(result.predictions) >= 1
        else:
            assert len(result.predictions) == 0

    def test_evidence_gaps_populated(self, engine: HypothesisEngine) -> None:
        evidence = [{'id': 'e1', 'type': 'behavioral', 'quality': 0.8}]
        result = engine.process(evidence)
        assert isinstance(result.evidence_gaps, tuple)

    def test_strongest_hypothesis(self, engine: HypothesisEngine) -> None:
        evidence = [
            {'id': 'e1', 'type': 'behavioral', 'quality': 0.8},
            {'id': 'e2', 'type': 'behavioral', 'quality': 0.7},
        ]
        result = engine.process(evidence)
        if result.hypotheses:
            assert result.strongest_hypothesis != ''

    def test_process_object_evidence(self, engine: HypothesisEngine) -> None:
        class _FakeEvidence:
            def __init__(self) -> None:
                self.evidence_id = 'fe1'
                self.evidence_type = 'behavioral'
                self.quality = 0.8
                self.content = 'observed something'
        result = engine.process([_FakeEvidence()])
        assert isinstance(result, HypothesisResult)
