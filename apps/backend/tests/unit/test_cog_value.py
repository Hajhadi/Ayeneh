"""Tests for the COG-07 Value Modeling pipeline."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.cog.value.types import (
    DECLARED_VS_OBSERVED,
    VALUE_CATEGORIES,
    ValueObject,
)
from ayeneh.cog.value.modeling import ValueModelingEngine, ValueModelingResult
from ayeneh.cog.value.authenticity import AuthenticityEstimator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def value_engine():
    return ValueModelingEngine()


@pytest.fixture
def authenticity_estimator():
    return AuthenticityEstimator()


@pytest.fixture
def sample_evidence():
    return [
        {'identifier': 'ev-1', 'type': 'self_report', 'text': 'I value honesty above all.'},
        {'identifier': 'ev-2', 'type': 'behavioral_report', 'text': 'I always tell the truth.'},
        {'identifier': 'ev-3', 'type': 'self_report', 'text': 'What matters is family.'},
        {'identifier': 'ev-4', 'type': 'observation', 'text': 'Growth is important.'},
    ]


@pytest.fixture
def sample_value():
    return ValueObject(
        identifier='val-1',
        value_statement='Honesty is important',
        category='authenticity',
        confidence=0.8,
        stability=0.7,
        priority=0.9,
        influence=0.8,
    )


# ---------------------------------------------------------------------------
# ValueObject tests
# ---------------------------------------------------------------------------


class TestValueObject:
    def test_creation(self):
        v = ValueObject(
            identifier='v1',
            value_statement='Honesty matters',
            category='authenticity',
        )
        assert v.identifier == 'v1'
        assert v.value_statement == 'Honesty matters'
        assert v.category == 'authenticity'

    def test_defaults(self):
        v = ValueObject(identifier='v2', value_statement='test', category='growth')
        assert v.confidence == 0.0
        assert v.stability == 0.0
        assert v.priority == 0.0
        assert v.influence == 0.0
        assert v.declared_vs_observed == 'unknown'
        assert v.lifecycle_state == 'candidate'
        assert v.specification_version == '1.0.0'

    def test_frozen(self):
        v = ValueObject(identifier='v3', value_statement='test', category='growth')
        with pytest.raises(AttributeError):
            v.confidence = 0.5  # type: ignore[misc]

    def test_evidence_tuples(self):
        v = ValueObject(
            identifier='v4',
            value_statement='test',
            category='growth',
            supporting_evidence=('ev-1',),
            behavioural_evidence=('ev-2', 'ev-3'),
            contradictory_evidence=('ev-4',),
        )
        assert len(v.supporting_evidence) == 1
        assert len(v.behavioural_evidence) == 2
        assert len(v.contradictory_evidence) == 1

    def test_cross_module_associations(self):
        v = ValueObject(
            identifier='v5',
            value_statement='test',
            category='growth',
            associated_beliefs=('b1',),
            associated_goals=('g1',),
            associated_narratives=('n1',),
        )
        assert 'b1' in v.associated_beliefs
        assert 'g1' in v.associated_goals
        assert 'n1' in v.associated_narratives

    def test_categories_contain_expected_values(self):
        assert 'relationship' in VALUE_CATEGORIES
        assert 'creativity' in VALUE_CATEGORIES
        assert 'spirituality' in VALUE_CATEGORIES
        assert len(VALUE_CATEGORIES) == 15

    def test_declared_vs_observed_options(self):
        assert 'unknown' in DECLARED_VS_OBSERVED
        assert 'aligned' in DECLARED_VS_OBSERVED
        assert 'misaligned' in DECLARED_VS_OBSERVED


# ---------------------------------------------------------------------------
# ValueModelingEngine tests
# ---------------------------------------------------------------------------


class TestValueModelingEngine:
    def test_process_returns_result(self, value_engine, sample_evidence):
        result = value_engine.process(sample_evidence)
        assert isinstance(result, ValueModelingResult)

    def test_extracts_values(self, value_engine, sample_evidence):
        result = value_engine.process(sample_evidence)
        assert result.total_extracted > 0

    def test_values_have_identifiers(self, value_engine, sample_evidence):
        result = value_engine.process(sample_evidence)
        for v in result.values:
            assert v.identifier
            assert isinstance(v.identifier, str)

    def test_values_have_valid_categories(self, value_engine, sample_evidence):
        result = value_engine.process(sample_evidence)
        for v in result.values:
            assert v.category in VALUE_CATEGORIES

    def test_values_are_provisional(self, value_engine, sample_evidence):
        result = value_engine.process(sample_evidence)
        for v in result.values:
            assert v.lifecycle_state == 'provisional'

    def test_metrics_computed(self, value_engine, sample_evidence):
        result = value_engine.process(sample_evidence)
        for v in result.values:
            assert 0.0 <= v.confidence <= 1.0
            assert 0.0 <= v.stability <= 1.0
            assert 0.0 <= v.priority <= 1.0
            assert 0.0 <= v.influence <= 1.0

    def test_by_category(self, value_engine, sample_evidence):
        result = value_engine.process(sample_evidence)
        assert isinstance(result.by_category, dict)
        total = sum(result.by_category.values())
        assert total == result.total_extracted

    def test_with_beliefs(self, value_engine, sample_evidence):
        beliefs = [{'identifier': 'b1', 'statement': 'I value knowledge.'}]
        result = value_engine.process(sample_evidence, beliefs=beliefs)
        assert result.total_extracted > 0

    def test_empty_evidence(self, value_engine):
        result = value_engine.process([])
        assert result.total_extracted == 0

    def test_determinism(self, value_engine, sample_evidence):
        """Same input → same output."""
        r1 = value_engine.process(sample_evidence)
        r2 = value_engine.process(sample_evidence)
        assert r1.total_extracted == r2.total_extracted
        for v1, v2 in zip(r1.values, r2.values):
            assert v1.value_statement == v2.value_statement

    def test_no_value_keywords_filtered(self, value_engine):
        evidence = [
            {'identifier': 'ev-1', 'type': 'observation', 'text': 'The sky is blue.'},
        ]
        result = value_engine.process(evidence)
        assert result.total_extracted == 0


# ---------------------------------------------------------------------------
# AuthenticityEstimator tests
# ---------------------------------------------------------------------------


class TestAuthenticityEstimator:
    def test_aligned_values(self, authenticity_estimator):
        value = ValueObject(
            identifier='v1',
            value_statement='honesty is important',
            category='authenticity',
        )
        evidence = [
            {'type': 'self_report', 'text': 'I value honesty in my life.'},
            {'type': 'behavioral_report', 'text': 'I always practice honesty with others.'},
        ]
        result = authenticity_estimator.estimate(value, evidence)
        assert result['declared_count'] == 1
        assert result['behavioural_count'] == 1
        assert result['classification'] == 'aligned'

    def test_misaligned_values(self, authenticity_estimator):
        value = ValueObject(
            identifier='v2',
            value_statement='honesty is important',
            category='authenticity',
        )
        evidence = [
            {'type': 'self_report', 'text': 'I believe in something completely different.'},
            {'type': 'behavioral_report', 'text': 'Unrelated behavior.'},
        ]
        result = authenticity_estimator.estimate(value, evidence)
        assert result['classification'] in ('misaligned', 'partial')

    def test_no_evidence(self, authenticity_estimator):
        value = ValueObject(
            identifier='v3',
            value_statement='test',
            category='growth',
        )
        result = authenticity_estimator.estimate(value, [])
        assert result['declared_count'] == 0
        assert result['behavioural_count'] == 0
        assert result['classification'] == 'partial'

    def test_only_declared(self, authenticity_estimator):
        value = ValueObject(
            identifier='v4',
            value_statement='growth is important',
            category='growth',
        )
        evidence = [
            {'type': 'self_report', 'text': 'I value growth.'},
        ]
        result = authenticity_estimator.estimate(value, evidence)
        assert result['declared_count'] == 1
        assert result['behavioural_count'] == 0

    def test_only_behavioural(self, authenticity_estimator):
        value = ValueObject(
            identifier='v5',
            value_statement='growth is important',
            category='growth',
        )
        evidence = [
            {'type': 'behavioral_report', 'text': 'I keep growing every day.'},
        ]
        result = authenticity_estimator.estimate(value, evidence)
        assert result['declared_count'] == 0
        assert result['behavioural_count'] == 1

    def test_dict_value_input(self, authenticity_estimator):
        value = {'value_statement': 'freedom matters'}
        evidence = [
            {'type': 'self_report', 'text': 'I value freedom.'},
        ]
        result = authenticity_estimator.estimate(value, evidence)
        assert 'alignment_score' in result
