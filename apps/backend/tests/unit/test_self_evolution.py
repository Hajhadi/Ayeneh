"""Unit tests for SELF-05 Self-Evolution types and engine."""

from __future__ import annotations

import pytest

from ayeneh.self_arch.self_evolution.types import (
    APPROVAL_STATUSES,
    EVOLUTION_CATEGORIES,
    EVOLUTION_PHASES,
    IMPACT_CATEGORIES,
    RISK_LEVELS,
    CapabilityOpportunity,
    EvolutionConfidence,
    EvolutionIdentifier,
    EvolutionObject,
    EvolutionProposal,
    EvolutionResult,
    ExplainabilityMetadata,
    OperationalRecord,
    RiskAssessment,
    TrendAnalysis,
    VersionUpdate,
)
from ayeneh.self_arch.self_evolution.engine import SelfEvolutionEngine


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestEvolutionIdentifier:
    def test_default_creation(self) -> None:
        ident = EvolutionIdentifier(id='e1')
        assert ident.id == 'e1'
        assert ident.version == 1

    def test_frozen(self) -> None:
        ident = EvolutionIdentifier(id='e1')
        with pytest.raises(AttributeError):
            ident.id = 'e2'  # type: ignore[misc]


class TestOperationalRecord:
    def test_default_creation(self) -> None:
        record = OperationalRecord(record_id='r1', module='cog', metric_name='quality')
        assert record.record_id == 'r1'
        assert record.module == 'cog'
        assert record.metric_value == 0.0


class TestTrendAnalysis:
    def test_default_creation(self) -> None:
        trend = TrendAnalysis(trend_id='t1', metric_name='performance')
        assert trend.trend_id == 't1'
        assert trend.direction == 'stable'
        assert trend.magnitude == 0.0

    def test_frozen(self) -> None:
        trend = TrendAnalysis(trend_id='t1')
        with pytest.raises(AttributeError):
            trend.direction = 'improving'  # type: ignore[misc]


class TestCapabilityOpportunity:
    def test_default_creation(self) -> None:
        opp = CapabilityOpportunity(opportunity_id='o1')
        assert opp.opportunity_id == 'o1'
        assert opp.priority == 0.5


class TestEvolutionProposal:
    def test_default_creation(self) -> None:
        proposal = EvolutionProposal(proposal_id='p1', title='Test')
        assert proposal.proposal_id == 'p1'
        assert proposal.title == 'Test'
        assert proposal.priority == 0.5


class TestRiskAssessment:
    def test_default_creation(self) -> None:
        risk = RiskAssessment(risk_id='r1')
        assert risk.risk_id == 'r1'
        assert risk.risk_level == 'medium'
        assert risk.probability == 0.5


class TestVersionUpdate:
    def test_default_creation(self) -> None:
        update = VersionUpdate(update_id='u1', previous_version='1.0.0', new_version='1.1.0')
        assert update.previous_version == '1.0.0'
        assert update.new_version == '1.1.0'
        assert update.is_rollback is False


class TestEvolutionObject:
    def test_default_creation(self) -> None:
        obj = EvolutionObject(evolution_id='e1')
        assert obj.evolution_id == 'e1'
        assert obj.approval_status == 'proposed'

    def test_frozen(self) -> None:
        obj = EvolutionObject(evolution_id='e1')
        with pytest.raises(AttributeError):
            obj.evolution_id = 'e2'  # type: ignore[misc]


class TestEvolutionResult:
    def test_default_creation(self) -> None:
        result = EvolutionResult()
        assert result.evolution_id == ''
        assert result.confidence == 0.0
        assert result.duration_ms == 0.0
        assert len(result.errors) == 0

    def test_with_errors(self) -> None:
        result = EvolutionResult(errors=('err1',))
        assert len(result.errors) == 1


class TestConstants:
    def test_evolution_categories(self) -> None:
        assert 'capability_expansion' in EVOLUTION_CATEGORIES
        assert 'safety_enhancement' in EVOLUTION_CATEGORIES
        assert len(EVOLUTION_CATEGORIES) == 8

    def test_evolution_phases(self) -> None:
        assert 'operational_history' in EVOLUTION_PHASES
        assert 'architecture_version_update' in EVOLUTION_PHASES
        assert len(EVOLUTION_PHASES) == 8

    def test_approval_statuses(self) -> None:
        assert 'proposed' in APPROVAL_STATUSES
        assert 'approved' in APPROVAL_STATUSES
        assert 'implemented' in APPROVAL_STATUSES

    def test_risk_levels(self) -> None:
        assert 'negligible' in RISK_LEVELS
        assert 'critical' in RISK_LEVELS

    def test_impact_categories(self) -> None:
        assert 'performance' in IMPACT_CATEGORIES
        assert 'security' in IMPACT_CATEGORIES


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestSelfEvolutionEngine:
    def setup_method(self) -> None:
        self.engine = SelfEvolutionEngine()

    def test_default_evolve(self) -> None:
        result = self.engine.evolve()
        assert result.evolution_id
        assert result.evolution_object is not None
        assert result.duration_ms >= 0

    def test_evolve_with_context(self) -> None:
        result = self.engine.evolve(
            context={'architecture_version': '2.0.0'},
            session_id='test-session',
        )
        assert result.evolution_id
        assert result.evolution_object.approval_status in (
            'proposed', 'approved',
        )

    def test_evolve_gathers_records(self) -> None:
        result = self.engine.evolve()
        assert len(result.operational_records) > 0

    def test_evolve_identifies_trends(self) -> None:
        result = self.engine.evolve()
        assert len(result.trends) > 0

    def test_evolve_finds_opportunities(self) -> None:
        result = self.engine.evolve()
        assert len(result.opportunities) > 0

    def test_evolve_generates_proposals(self) -> None:
        result = self.engine.evolve()
        assert len(result.proposals) > 0

    def test_evolve_performs_risk_assessment(self) -> None:
        result = self.engine.evolve()
        assert len(result.risk_assessments) > 0

    def test_evolve_computes_version_update(self) -> None:
        result = self.engine.evolve()
        if result.version_updates:
            update = result.version_updates[0]
            assert update.new_version != '1.0.0'

    def test_evolve_with_custom_modules(self) -> None:
        engine = SelfEvolutionEngine(modules=['cog', 'dec'])
        result = engine.evolve()
        assert result.evolution_id

    def test_evolve_with_operational_records(self) -> None:
        result = self.engine.evolve(
            context={
                'operational_records': [
                    {'module': 'cog', 'metric': 'quality', 'value': 0.9},
                    {'module': 'cog', 'metric': 'quality', 'value': 0.7},
                ],
            },
        )
        assert len(result.trends) > 0

    def test_evolve_confidence_range(self) -> None:
        result = self.engine.evolve()
        assert 0.0 <= result.confidence <= 1.0

    def test_evolve_result_is_frozen(self) -> None:
        result = self.engine.evolve()
        with pytest.raises(AttributeError):
            result.evolution_id = 'changed'  # type: ignore[misc]

    def test_evolve_explainability_metadata(self) -> None:
        result = self.engine.evolve()
        meta = result.evolution_object.explainability_metadata
        assert 'reasoning_chain' in meta
        assert len(meta['reasoning_chain']) > 0

    def test_evolve_version_bumps(self) -> None:
        engine = SelfEvolutionEngine(architecture_version='1.0.0')
        result = engine.evolve()
        if result.version_updates:
            new_ver = result.version_updates[0].new_version
            assert new_ver.startswith('1.')
