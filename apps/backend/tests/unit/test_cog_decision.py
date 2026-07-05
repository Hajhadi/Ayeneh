"""Tests for the COG-10 Decision Architecture Engine."""

from __future__ import annotations

import pytest

from ayeneh.cog.decision.architecture import DecisionArchitectureEngine
from ayeneh.cog.decision.learning import (
    DecisionLearner,
    OutcomeAnalysis,
    DecisionLearningObject,
    RegretObject,
)
from ayeneh.cog.decision.types import (
    DECISION_LIFECYCLE_STATES,
    DECISION_TYPES,
    OUTCOME_CATEGORIES,
    DecisionObject,
    DecisionPattern,
    DecisionResult,
    TradeOff,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return DecisionArchitectureEngine()


@pytest.fixture
def learner():
    return DecisionLearner()


@pytest.fixture
def sample_evidence():
    return [
        {'id': 'ev-1', 'text': 'I decided to quit my job and start a business', 'category': 'decision_report'},
        {'id': 'ev-2', 'text': 'I chose to study engineering rather than medicine', 'category': 'decision_report'},
        {'id': 'ev-3', 'text': 'I believe hard work always pays off', 'category': 'self_report'},
        {'id': 'ev-4', 'text': 'I value financial independence', 'category': 'identity_statement'},
        {'id': 'ev-5', 'text': 'I will move to a new city next month', 'category': 'intention'},
    ]


@pytest.fixture
def sample_decision():
    return DecisionObject(
        identifier='dec-1',
        decision_statement='I decided to quit my job',
        context='career',
        alternatives=('keep job', 'quit job', 'transition slowly'),
        chosen_alternative='quit job',
        rejected_alternatives=('keep job', 'transition slowly'),
        supporting_evidence=('ev-1',),
        activated_narratives=('narr-1',),
        activated_beliefs=('belief-1',),
        activated_values=('value-1', 'value-2'),
        activated_goals=('goal-1',),
        activated_identity_components=('id-1',),
        confidence=0.7,
        uncertainty=0.3,
        decision_inertia=0.5,
        lifecycle_state='validated',
    )


# ---------------------------------------------------------------------------
# DecisionObject tests
# ---------------------------------------------------------------------------


class TestDecisionObject:
    def test_creation(self, sample_decision):
        assert sample_decision.identifier == 'dec-1'
        assert sample_decision.decision_statement == 'I decided to quit my job'
        assert sample_decision.chosen_alternative == 'quit job'

    def test_defaults(self):
        dec = DecisionObject(identifier='d1', decision_statement='test', context='ctx')
        assert dec.alternatives == ()
        assert dec.chosen_alternative == ''
        assert dec.confidence == 0.0
        assert dec.uncertainty == 0.0
        assert dec.decision_inertia == 0.0
        assert dec.lifecycle_state == 'candidate'
        assert dec.specification_version == '1.0.0'

    def test_frozen(self, sample_decision):
        with pytest.raises(AttributeError):
            sample_decision.confidence = 0.5  # type: ignore[misc]

    def test_frozen_decision_statement(self, sample_decision):
        with pytest.raises(AttributeError):
            sample_decision.decision_statement = 'other'  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DecisionPattern tests
# ---------------------------------------------------------------------------


class TestDecisionPattern:
    def test_creation(self):
        pattern = DecisionPattern(
            pattern_id='p1',
            description='Safety-first pattern',
            frequency=5,
            confidence=0.8,
            decision_ids=('d1', 'd2', 'd3'),
        )
        assert pattern.pattern_id == 'p1'
        assert pattern.frequency == 5

    def test_defaults(self):
        pattern = DecisionPattern(pattern_id='p1', description='test')
        assert pattern.frequency == 0
        assert pattern.confidence == 0.0
        assert pattern.decision_ids == ()

    def test_frozen(self):
        pattern = DecisionPattern(pattern_id='p1', description='test')
        with pytest.raises(AttributeError):
            pattern.frequency = 10  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TradeOff tests
# ---------------------------------------------------------------------------


class TestTradeOff:
    def test_creation(self):
        to = TradeOff(
            decision_id='d1',
            value_a='safety',
            value_b='growth',
            chosen='safety',
            rejected='growth',
            opportunity_cost=0.6,
        )
        assert to.decision_id == 'd1'
        assert to.chosen == 'safety'

    def test_frozen(self):
        to = TradeOff(
            decision_id='d1', value_a='a', value_b='b',
            chosen='a', rejected='b',
        )
        with pytest.raises(AttributeError):
            to.chosen = 'c'  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DecisionArchitectureEngine tests
# ---------------------------------------------------------------------------


class TestDecisionArchitectureEngine:
    def test_process_returns_result(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert isinstance(result, DecisionResult)

    def test_decisions_extracted(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert result.total_extracted > 0

    def test_all_decisions_have_identifiers(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        for dec in result.decisions.values():
            assert dec.identifier
            assert isinstance(dec.identifier, str)

    def test_decisions_have_statement(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        for dec in result.decisions.values():
            assert dec.decision_statement

    def test_confidence_in_range(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        for dec in result.decisions.values():
            assert 0.0 <= dec.confidence <= 1.0

    def test_determinism(self, engine, sample_evidence):
        """Same input → same output (deterministic pipeline)."""
        r1 = engine.process(sample_evidence)
        r2 = engine.process(sample_evidence)
        assert r1.total_extracted == r2.total_extracted

    def test_empty_evidence(self, engine):
        result = engine.process([])
        assert result.total_extracted == 0

    def test_with_beliefs_values_goals(self, engine, sample_evidence):
        result = engine.process(
            sample_evidence,
            beliefs=['belief-1', 'hard work'],
            values=['financial independence', 'growth'],
            goals=['start business'],
            narratives=['entrepreneur narrative'],
            identity=['entrepreneur identity'],
        )
        assert result.total_extracted > 0

    def test_patterns_detected(self, engine, sample_evidence):
        result = engine.process(
            sample_evidence,
            beliefs=['belief-1'],
            values=['value-1'],
        )
        assert isinstance(result.patterns, dict)

    def test_lifecycle_summary(self, engine, sample_evidence):
        result = engine.process(sample_evidence)
        assert isinstance(result.lifecycle_summary, dict)
        total = sum(result.lifecycle_summary.values())
        assert total == result.total_extracted

    def test_trade_offs(self, engine, sample_evidence):
        result = engine.process(
            sample_evidence,
            values=['safety', 'growth'],
        )
        assert isinstance(result.trade_offs, tuple)

    def test_with_structures_activates(self, engine):
        evidence = [
            {'id': 'ev-1', 'text': 'I decided to study hard rather than relax', 'category': 'decision_report'},
        ]
        result = engine.process(
            evidence,
            beliefs=['studying is important'],
            values=['academic excellence'],
            goals=['graduate with honors'],
        )
        assert result.total_extracted > 0


# ---------------------------------------------------------------------------
# DecisionLearner tests
# ---------------------------------------------------------------------------


class TestDecisionLearner:
    def test_analyze_outcome_returns_result(self, learner, sample_decision):
        result = learner.analyze_outcome(sample_decision, 'The business succeeded')
        assert isinstance(result, OutcomeAnalysis)

    def test_positive_outcome(self, learner, sample_decision):
        result = learner.analyze_outcome(sample_decision, 'success and positive growth')
        assert result.outcome_category == 'positive'

    def test_negative_outcome(self, learner, sample_decision):
        result = learner.analyze_outcome(sample_decision, 'The business was a failure and loss')
        assert result.outcome_category == 'negative'

    def test_mixed_outcome(self, learner, sample_decision):
        result = learner.analyze_outcome(sample_decision, 'success but with some loss')
        assert result.outcome_category == 'mixed'

    def test_neutral_outcome(self, learner, sample_decision):
        result = learner.analyze_outcome(sample_decision, 'nothing special happened')
        assert result.outcome_category == 'neutral'

    def test_empty_outcome(self, learner, sample_decision):
        result = learner.analyze_outcome(sample_decision, '')
        assert result.outcome_category == 'pending'

    def test_regret_detection(self, learner):
        decision = DecisionObject(
            identifier='d1',
            decision_statement='test',
            context='ctx',
            alternatives=('a', 'b'),
            chosen_alternative='a',
            rejected_alternatives=('b',),
        )
        result = learner.analyze_outcome(decision, 'I regret choosing a, it was a mistake')
        assert result.regret is not None
        assert result.regret.regret_level > 0.0

    def test_no_regret_positive(self, learner, sample_decision):
        result = learner.analyze_outcome(sample_decision, 'Great success, positive outcome')
        assert result.regret is None

    def test_learning_extracted(self, learner, sample_decision):
        result = learner.analyze_outcome(sample_decision, 'success')
        assert result.learning is not None
        assert result.learning.decision_id == 'dec-1'

    def test_adjustments_for_negative(self, learner, sample_decision):
        result = learner.analyze_outcome(sample_decision, 'failure and negative result')
        assert len(result.adjustments) > 0

    def test_adjustments_for_positive(self, learner, sample_decision):
        result = learner.analyze_outcome(sample_decision, 'success and positive growth')
        assert 'reinforce_decision_pattern' in result.adjustments

    def test_frozen_outcome_analysis(self, learner, sample_decision):
        result = learner.analyze_outcome(sample_decision, 'success')
        with pytest.raises(AttributeError):
            result.outcome_category = 'other'  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Catalogue tests
# ---------------------------------------------------------------------------


class TestCatalogues:
    def test_decision_lifecycle_states(self):
        assert 'candidate' in DECISION_LIFECYCLE_STATES
        assert 'canonical' in DECISION_LIFECYCLE_STATES
        assert len(DECISION_LIFECYCLE_STATES) > 4

    def test_decision_types(self):
        assert 'deliberate' in DECISION_TYPES
        assert 'intuitive' in DECISION_TYPES
        assert len(DECISION_TYPES) > 4

    def test_outcome_categories(self):
        assert 'positive' in OUTCOME_CATEGORIES
        assert 'negative' in OUTCOME_CATEGORIES
        assert len(OUTCOME_CATEGORIES) > 3
