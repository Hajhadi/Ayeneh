"""Unit tests for SELF integration: DB models, API endpoints, and pipeline integration."""

from __future__ import annotations

import pytest

from ayeneh.infrastructure.persistence.models.self_model import SelfModelModel
from ayeneh.infrastructure.persistence.models.self_identity import SelfIdentityModel
from ayeneh.infrastructure.persistence.models.self_knowledge import SelfKnowledgeModel
from ayeneh.infrastructure.persistence.models.self_consistency import SelfConsistencyModel
from ayeneh.infrastructure.persistence.models.self_evolution import SelfEvolutionModel


# ---------------------------------------------------------------------------
# DB Model tests
# ---------------------------------------------------------------------------


class TestSelfModelModel:
    def test_table_name(self) -> None:
        assert SelfModelModel.__tablename__ == "self_models"

    def test_has_required_columns(self) -> None:
        columns = {c.name for c in SelfModelModel.__table__.columns}
        assert 'model_id' in columns
        assert 'architecture_version' in columns
        assert 'available_modules' in columns
        assert 'module_status' in columns
        assert 'capabilities' in columns
        assert 'confidence' in columns
        assert 'user_id' in columns


class TestSelfIdentityModel:
    def test_table_name(self) -> None:
        assert SelfIdentityModel.__tablename__ == "self_identities"

    def test_has_required_columns(self) -> None:
        columns = {c.name for c in SelfIdentityModel.__table__.columns}
        assert 'identity_id' in columns
        assert 'identity_version' in columns
        assert 'core_principles' in columns
        assert 'confidence' in columns
        assert 'user_id' in columns


class TestSelfKnowledgeModel:
    def test_table_name(self) -> None:
        assert SelfKnowledgeModel.__tablename__ == "self_knowledge"

    def test_has_required_columns(self) -> None:
        columns = {c.name for c in SelfKnowledgeModel.__table__.columns}
        assert 'knowledge_id' in columns
        assert 'statement' in columns
        assert 'evidence_sources' in columns
        assert 'confidence' in columns
        assert 'verification_status' in columns
        assert 'user_id' in columns


class TestSelfConsistencyModel:
    def test_table_name(self) -> None:
        assert SelfConsistencyModel.__tablename__ == "self_consistency"

    def test_has_required_columns(self) -> None:
        columns = {c.name for c in SelfConsistencyModel.__table__.columns}
        assert 'consistency_id' in columns
        assert 'affected_modules' in columns
        assert 'consistency_type' in columns
        assert 'detected_conflicts' in columns
        assert 'resolution_status' in columns
        assert 'confidence' in columns
        assert 'architectural_impact' in columns
        assert 'user_id' in columns


class TestSelfEvolutionModel:
    def test_table_name(self) -> None:
        assert SelfEvolutionModel.__tablename__ == "self_evolution"

    def test_has_required_columns(self) -> None:
        columns = {c.name for c in SelfEvolutionModel.__table__.columns}
        assert 'evolution_id' in columns
        assert 'architecture_version' in columns
        assert 'proposal' in columns
        assert 'motivation' in columns
        assert 'affected_modules' in columns
        assert 'approval_status' in columns
        assert 'user_id' in columns


# ---------------------------------------------------------------------------
# Cross-module integration tests
# ---------------------------------------------------------------------------


class TestCrossModuleIntegration:
    """Tests that verify SELF modules work together correctly."""

    def test_consistency_feeds_evolution(self) -> None:
        """Consistency check results can inform evolution decisions."""
        from ayeneh.self_arch.self_consistency.engine import SelfConsistencyEngine
        from ayeneh.self_arch.self_evolution.engine import SelfEvolutionEngine

        consistency_engine = SelfConsistencyEngine()
        consistency_result = consistency_engine.check()

        # Feed consistency result into evolution
        evolution_engine = SelfEvolutionEngine()
        evolution_result = evolution_engine.evolve(
            context={
                'consistency_result': {
                    'confidence': consistency_result.confidence,
                    'conflicts': len(consistency_result.conflicts),
                },
            },
        )

        assert evolution_result.evolution_id
        assert evolution_result.confidence >= 0.0

    def test_evolution_version_increments(self) -> None:
        """Evolution engine properly increments version numbers."""
        from ayeneh.self_arch.self_evolution.engine import SelfEvolutionEngine

        engine = SelfEvolutionEngine(architecture_version='1.0.0')
        result = engine.evolve()

        if result.version_updates:
            assert result.version_updates[0].new_version != '1.0.0'

    def test_consistency_modules_match_architecture(self) -> None:
        """Consistency engine checks all expected architecture modules."""
        from ayeneh.self_arch.self_consistency.engine import SelfConsistencyEngine

        engine = SelfConsistencyEngine()
        result = engine.check()

        module_names = [s.module_name for s in result.module_statuses]
        expected = {'cog', 'inf', 'dlg', 'dec', 'act', 'int', 'memo', 'self'}
        assert expected.issubset(set(module_names))

    def test_consistency_health_indicators_comprehensive(self) -> None:
        """Consistency engine produces all expected health indicators."""
        from ayeneh.self_arch.self_consistency.engine import SelfConsistencyEngine

        engine = SelfConsistencyEngine()
        result = engine.check()

        indicator_names = {h.indicator_name for h in result.health_indicators}
        expected = {'module_health', 'conflict_health', 'resolution_health', 'integrity_health'}
        assert expected.issubset(indicator_names)

    def test_both_engines_produce_explainability(self) -> None:
        """Both consistency and evolution engines produce explainability metadata."""
        from ayeneh.self_arch.self_consistency.engine import SelfConsistencyEngine
        from ayeneh.self_arch.self_evolution.engine import SelfEvolutionEngine

        cons_result = SelfConsistencyEngine().check()
        evo_result = SelfEvolutionEngine().evolve()

        cons_meta = cons_result.consistency_object.explainability_metadata
        evo_meta = evo_result.evolution_object.explainability_metadata

        assert 'reasoning_chain' in cons_meta
        assert 'reasoning_chain' in evo_meta
        assert len(cons_meta['reasoning_chain']) > 0
        assert len(evo_meta['reasoning_chain']) > 0

    def test_api_imports_work(self) -> None:
        """API endpoint module can be imported without errors."""
        from ayeneh.api.v1.endpoints.self_arch import router
        assert router is not None

    def test_pipeline_self_analysis_field(self) -> None:
        """PipelineResult has the self_analysis field."""
        from ayeneh.runtime.pipeline import PipelineResult
        result = PipelineResult()
        assert hasattr(result, 'self_analysis')
        assert result.self_analysis is None

    def test_models_init_includes_self_models(self) -> None:
        """Models __init__ includes all self_* models."""
        import ayeneh.infrastructure.persistence.models as models
        assert hasattr(models, 'SelfModelModel')
        assert hasattr(models, 'SelfIdentityModel')
        assert hasattr(models, 'SelfKnowledgeModel')
        assert hasattr(models, 'SelfConsistencyModel')
        assert hasattr(models, 'SelfEvolutionModel')
