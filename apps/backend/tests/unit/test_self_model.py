"""Tests for SELF-01 Self-Model Engine."""

from __future__ import annotations

import time

import pytest

from ayeneh.self_arch.self_model.engine import SelfModelEngine
from ayeneh.self_arch.self_model.types import (
    ConstraintDescriptor,
    ExplainabilityMetadata,
    ModuleStatusEntry,
    ResourceAvailability,
    RevisionEntry,
    SelfModelConfidence,
    SelfModelIdentifier,
    SelfModelObject,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> SelfModelEngine:
    return SelfModelEngine()


# ---------------------------------------------------------------------------
# Type construction tests
# ---------------------------------------------------------------------------


class TestSelfModelTypes:
    def test_self_model_identifier_defaults(self) -> None:
        ident = SelfModelIdentifier()
        assert ident.id == 'self_model_001'
        assert ident.version == 1
        assert ident.created_at is not None

    def test_module_status_entry_defaults(self) -> None:
        entry = ModuleStatusEntry()
        assert entry.module_name == ''
        assert entry.status == 'unknown'
        assert entry.health_score == 0.0

    def test_capability_descriptor_defaults(self) -> None:
        from ayeneh.self_arch.self_model.types import CapabilityDescriptor
        cap = CapabilityDescriptor()
        assert cap.capability_name == ''
        assert cap.confidence == 0.0

    def test_constraint_descriptor_defaults(self) -> None:
        cd = ConstraintDescriptor()
        assert cd.constraint_type == ''
        assert cd.is_active is True
        assert cd.severity == 'medium'

    def test_resource_availability_defaults(self) -> None:
        ra = ResourceAvailability()
        assert ra.resource_type == ''
        assert ra.current_level == 0.0
        assert ra.is_critical is False

    def test_revision_entry_defaults(self) -> None:
        re = RevisionEntry()
        assert re.version == ''
        assert re.change_description == ''
        assert re.confidence_before == 0.0

    def test_self_model_confidence_defaults(self) -> None:
        sc = SelfModelConfidence()
        assert sc.architecture_confidence == 0.0
        assert sc.overall == 0.0

    def test_explainability_metadata_defaults(self) -> None:
        em = ExplainabilityMetadata()
        assert em.reasoning_chain == ()
        assert em.is_explainable is True

    def test_self_model_object_defaults(self) -> None:
        obj = SelfModelObject()
        assert obj.model_id == ''
        assert obj.architecture_version == ''
        assert obj.available_modules == ()
        assert obj.module_status == {}
        assert obj.capabilities == ()
        assert obj.known_limitations == ()
        assert obj.active_constraints == ()
        assert obj.available_resources == {}
        assert obj.confidence == 0.0
        assert obj.revision_history == ()
        assert obj.version_metadata == {}
        assert obj.creation_timestamp is not None
        assert obj.explainability_metadata == {}

    def test_self_model_object_frozen(self) -> None:
        obj = SelfModelObject()
        with pytest.raises(AttributeError):
            obj.confidence = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Engine pipeline tests
# ---------------------------------------------------------------------------


class TestSelfModelEnginePipeline:
    def test_build_returns_self_model_object(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert isinstance(result, SelfModelObject)

    def test_build_populates_model_id(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert result.model_id != ''

    def test_build_sets_architecture_version(self, engine: SelfModelEngine) -> None:
        result = engine.build(architecture_version='2.0.0')
        assert result.architecture_version == '2.0.0'

    def test_build_discovers_default_modules(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert 'dlg' in result.available_modules
        assert 'inf' in result.available_modules
        assert 'cog' in result.available_modules
        assert 'self_arch' in result.available_modules

    def test_build_respects_custom_modules(self, engine: SelfModelEngine) -> None:
        custom = ('custom_a', 'custom_b')
        result = engine.build(available_modules=custom)
        assert result.available_modules == ('custom_a', 'custom_b')

    def test_build_populates_module_status(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert 'dlg' in result.module_status
        assert result.module_status['dlg'] == 'active'

    def test_build_custom_module_status(self, engine: SelfModelEngine) -> None:
        status = {'mod_a': 'active', 'mod_b': 'inactive'}
        result = engine.build(
            available_modules=('mod_a', 'mod_b'),
            module_status=status,
        )
        assert result.module_status['mod_b'] == 'inactive'

    def test_build_populates_capabilities(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert len(result.capabilities) > 0
        assert any(c.get('name') == 'dialogue_management' for c in result.capabilities)

    def test_build_populates_limitations(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert len(result.known_limitations) > 0

    def test_build_populates_constraints(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert len(result.active_constraints) > 0

    def test_build_populates_resources(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert 'compute_capacity' in result.available_resources
        assert 'memory_capacity' in result.available_resources

    def test_build_computes_positive_confidence(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert 0.0 <= result.confidence <= 1.0
        assert result.confidence > 0.0

    def test_build_records_revision_history(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert len(result.revision_history) == 1
        assert result.revision_history[0]['change_type'] == 'initial'

    def test_build_populates_version_metadata(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert 'schema_version' in result.version_metadata
        assert 'engine_version' in result.version_metadata

    def test_build_populates_explainability(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert 'reasoning_chain' in result.explainability_metadata
        assert 'evidence_summary' in result.explainability_metadata

    def test_build_sets_creation_timestamp(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        assert result.creation_timestamp is not None

    def test_build_output_is_frozen(self, engine: SelfModelEngine) -> None:
        result = engine.build()
        with pytest.raises(AttributeError):
            result.confidence = 1.0  # type: ignore[misc]

    def test_build_multiple_times_increments_revision(
        self, engine: SelfModelEngine,
    ) -> None:
        engine.build()
        result = engine.build()
        assert result.revision_history[-1]['version'] == '1.0.2'

    def test_revision_count_property(self, engine: SelfModelEngine) -> None:
        assert engine.revision_count == 0
        engine.build()
        assert engine.revision_count == 1

    def test_current_model_property(self, engine: SelfModelEngine) -> None:
        assert engine.current_model is None
        result = engine.build()
        assert engine.current_model is result

    def test_build_without_modules_has_lower_confidence(
        self, engine: SelfModelEngine,
    ) -> None:
        result_empty = engine.build(available_modules=())
        engine2 = SelfModelEngine()
        result_full = engine2.build()
        assert result_empty.confidence < result_full.confidence


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestSelfModelPerformance:
    def test_single_build_latency(self, engine: SelfModelEngine) -> None:
        start = time.monotonic()
        engine.build()
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 100

    def test_multiple_builds_latency(self, engine: SelfModelEngine) -> None:
        start = time.monotonic()
        for _ in range(10):
            engine.build()
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 500
