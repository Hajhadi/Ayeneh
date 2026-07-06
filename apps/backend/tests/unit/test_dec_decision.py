"""Tests for the DEC-01 Decision Support Engine."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.dec.decision_support.types import (
    DECISION_CATEGORIES,
    EVIDENCE_QUALITY_LEVELS,
    REVERSIBILITY_LEVELS,
    DecisionContext,
    DecisionObject,
    DecisionResult,
    MultiCriteriaScore,
    OpportunityAssessment,
    RiskAssessment,
    ScenarioOutcome,
    TradeOff,
)
from ayeneh.dec.decision_support.engine import DecisionSupportEngine
from ayeneh.dec.decision_support.multicriteria import (
    DEFAULT_CRITERIA_WEIGHTS,
    MultiCriteriaAnalyzer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return DecisionSupportEngine()


@pytest.fixture
def sample_question():
    return 'Should I switch careers to AI research?'


@pytest.fixture
def sample_context():
    return {
        'relevant_projects': ['project-alpha'],
        'identity_considerations': ['values innovation'],
        'available_resources': ['savings', 'free time evenings'],
        'environmental_constraints': ['family obligations'],
        'time_constraints': ['6 month transition window'],
    }


@pytest.fixture
def sample_goals():
    return [
        {
            'description': 'Career growth in AI',
            'category': 'career',
            'priority': 0.8,
        },
        {
            'description': 'Financial stability',
            'category': 'financial',
            'priority': 0.7,
        },
    ]


@pytest.fixture
def sample_memories():
    return [
        {
            'id': 'mem-1',
            'content': 'Experience in software engineering for 5 years',
            'confidence': 0.9,
            'category': 'behavior',
        },
        {
            'id': 'mem-2',
            'content': 'Completed online ML course with distinction',
            'confidence': 0.8,
            'category': 'observation',
        },
    ]


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestDecisionTypes:
    """Tests for DEC-01 type definitions."""

    def test_reversibility_levels_count(self):
        assert len(REVERSIBILITY_LEVELS) == 4

    def test_decision_categories_count(self):
        assert len(DECISION_CATEGORIES) == 10

    def test_evidence_quality_levels_count(self):
        assert len(EVIDENCE_QUALITY_LEVELS) == 5

    def test_decision_object_creation(self):
        obj = DecisionObject(decision_id='dec-1')
        assert obj.decision_id == 'dec-1'
        assert obj.confidence == 0.0
        assert obj.creation_timestamp is not None

    def test_decision_object_frozen(self):
        obj = DecisionObject(decision_id='dec-1')
        with pytest.raises(AttributeError):
            obj.decision_id = 'changed'  # type: ignore[misc]

    def test_decision_context_defaults(self):
        ctx = DecisionContext()
        assert ctx.current_goals == ()
        assert ctx.available_resources == ()

    def test_trade_off_creation(self):
        to = TradeOff(
            trade_off_id='to-1',
            option_a='A',
            option_b='B',
            dimension='cost',
            weight_a=0.6,
            weight_b=0.4,
        )
        assert to.trade_off_id == 'to-1'
        assert to.weight_a == 0.6

    def test_multi_criteria_score_defaults(self):
        score = MultiCriteriaScore()
        assert score.option == ''
        assert score.overall == 0.0

    def test_scenario_outcome_creation(self):
        s = ScenarioOutcome(
            scenario_id='sc-1',
            description='Best case',
            probability=0.7,
            impact=0.9,
        )
        assert s.probability == 0.7

    def test_risk_assessment_creation(self):
        r = RiskAssessment(
            risk_id='r-1',
            description='Market downturn',
            probability=0.3,
            severity=0.8,
        )
        assert r.severity == 0.8

    def test_opportunity_assessment_creation(self):
        o = OpportunityAssessment(
            opportunity_id='o-1',
            description='New funding',
            probability=0.5,
            potential_value=0.9,
        )
        assert o.potential_value == 0.9

    def test_decision_result_defaults(self):
        result = DecisionResult()
        assert result.decision.decision_id == ''
        assert result.overall_confidence == 0.0


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestDecisionSupportEngine:
    """Tests for the DEC-01 DecisionSupportEngine."""

    def test_engine_initialization(self):
        engine = DecisionSupportEngine()
        assert engine._decisions == {}

    def test_engine_with_ai_router(self):
        router = {'provider': 'test'}
        engine = DecisionSupportEngine(ai_router=router)
        assert engine._ai_router == router

    def test_process_basic(self, engine, sample_question):
        result = engine.process(sample_question)
        assert isinstance(result, DecisionResult)
        assert result.decision.question == sample_question

    def test_process_with_context(
        self, engine, sample_question, sample_context,
    ):
        result = engine.process(sample_question, context=sample_context)
        assert isinstance(result, DecisionResult)
        assert len(result.decision.options) > 0

    def test_process_with_goals(
        self, engine, sample_question, sample_goals,
    ):
        result = engine.process(sample_question, existing_goals=sample_goals)
        assert isinstance(result, DecisionResult)
        assert len(result.decision.goals) > 0

    def test_process_with_memories(
        self, engine, sample_question, sample_memories,
    ):
        result = engine.process(sample_question, memories=sample_memories)
        assert isinstance(result, DecisionResult)
        assert len(result.decision.supporting_evidence) > 0

    def test_process_full(
        self, engine, sample_question, sample_context,
        sample_goals, sample_memories,
    ):
        result = engine.process(
            sample_question,
            context=sample_context,
            existing_goals=sample_goals,
            memories=sample_memories,
        )
        assert isinstance(result, DecisionResult)
        assert len(result.decision.options) >= 2
        assert len(result.scenarios) > 0
        assert len(result.risks) > 0
        assert len(result.opportunities) > 0

    def test_process_confidence_range(
        self, engine, sample_question, sample_memories,
    ):
        result = engine.process(sample_question, memories=sample_memories)
        assert 0.0 <= result.overall_confidence <= 1.0

    def test_process_produces_options(
        self, engine, sample_question,
    ):
        result = engine.process(sample_question)
        assert len(result.decision.options) >= 2
        for opt in result.decision.options:
            assert 'name' in opt

    def test_process_produces_trade_offs(
        self, engine, sample_question,
    ):
        result = engine.process(sample_question)
        assert isinstance(result.trade_offs, tuple)
        assert len(result.trade_offs) >= 1

    def test_process_produces_multi_criteria_scores(
        self, engine, sample_question,
    ):
        result = engine.process(sample_question)
        assert len(result.multi_criteria_scores) > 0
        for score in result.multi_criteria_scores:
            assert isinstance(score, MultiCriteriaScore)

    def test_process_produces_dialogue_prompt(
        self, engine, sample_question,
    ):
        result = engine.process(sample_question)
        assert result.dialogue_prompt != ''
        assert sample_question in result.dialogue_prompt

    def test_process_produces_processing_metadata(
        self, engine, sample_question,
    ):
        result = engine.process(sample_question)
        assert 'option_count' in result.processing_metadata
        assert 'scenario_count' in result.processing_metadata

    def test_get_decision(self, engine, sample_question):
        result = engine.process(sample_question)
        decision_id = result.decision.decision_id
        retrieved = engine.get_decision(decision_id)
        assert retrieved is not None
        assert retrieved.decision_id == decision_id

    def test_get_decision_not_found(self, engine):
        assert engine.get_decision('nonexistent') is None

    def test_get_all_decisions(self, engine, sample_question):
        engine.process(sample_question)
        all_decisions = engine.get_all_decisions()
        assert len(all_decisions) >= 1

    def test_process_empty_question(self, engine):
        result = engine.process('')
        assert isinstance(result, DecisionResult)

    def test_process_deterministic(self, engine, sample_question):
        r1 = engine.process(sample_question)
        r2 = engine.process(sample_question)
        assert r1.decision.question == r2.decision.question
        assert r1.overall_confidence == r2.overall_confidence


# ---------------------------------------------------------------------------
# Multi-criteria tests
# ---------------------------------------------------------------------------


class TestMultiCriteriaAnalyzer:
    """Tests for the DEC-01 MultiCriteriaAnalyzer."""

    def test_analyzer_defaults(self):
        analyzer = MultiCriteriaAnalyzer()
        assert analyzer._weights == DEFAULT_CRITERIA_WEIGHTS

    def test_evaluate_single_option(self):
        analyzer = MultiCriteriaAnalyzer()
        options = ({'name': 'Option A'},)
        scores = analyzer.evaluate(options)
        assert len(scores) == 1
        assert scores[0].option == 'Option A'
        assert 0.0 <= scores[0].overall <= 1.0

    def test_evaluate_multiple_options(self):
        analyzer = MultiCriteriaAnalyzer()
        options = (
            {'name': 'Option A'},
            {'name': 'Option B'},
            {'name': 'Option C'},
        )
        scores = analyzer.evaluate(options)
        assert len(scores) == 3

    def test_evaluate_ranked(self):
        analyzer = MultiCriteriaAnalyzer()
        options = ({'name': 'A'}, {'name': 'B'})
        criteria = {
            'A': {'goal_alignment': 0.9, 'risk': 0.2},
            'B': {'goal_alignment': 0.3, 'risk': 0.8},
        }
        scores = analyzer.evaluate(options, criteria_inputs=criteria)
        assert scores[0].option == 'A'
        assert scores[0].overall >= scores[1].overall

    def test_get_top_option(self):
        analyzer = MultiCriteriaAnalyzer()
        options = ({'name': 'A'}, {'name': 'B'})
        scores = analyzer.evaluate(options)
        top = analyzer.get_top_option(scores)
        assert top is not None
        assert isinstance(top, MultiCriteriaScore)

    def test_get_top_option_empty(self):
        analyzer = MultiCriteriaAnalyzer()
        assert analyzer.get_top_option(()) is None

    def test_compare_options(self):
        analyzer = MultiCriteriaAnalyzer()
        options = ({'name': 'A'}, {'name': 'B'})
        scores = analyzer.evaluate(options)
        result = analyzer.compare(scores[0], scores[1])
        assert 'winner' in result
        assert 'differences' in result
        assert 'overall_difference' in result

    def test_custom_weights(self):
        weights = dict(DEFAULT_CRITERIA_WEIGHTS)
        weights['ethical'] = 0.5
        analyzer = MultiCriteriaAnalyzer(weights=weights)
        options = ({'name': 'A'},)
        scores = analyzer.evaluate(options)
        assert len(scores) == 1
