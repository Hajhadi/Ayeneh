"""Unit tests for INT-01 Cognitive Orchestrator types and engine."""

from __future__ import annotations

import pytest

from ayeneh.int.orchestrator.types import (
    CoordinationMessage,
    DependencyEdge,
    ExecutionStep,
    ExplainabilityMetadata,
    IntegrationResult,
    ModuleSelection,
    ORCHESTRATION_STATUSES,
    MODULE_CAPABILITIES,
    EXECUTION_STRATEGIES,
    OrchestrationObject,
    OrchestrationResult,
)
from ayeneh.int.orchestrator.engine import CognitiveOrchestrator


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------


class TestModuleSelection:
    def test_default_creation(self) -> None:
        sel = ModuleSelection(module_id='m1', capability='memory_management')
        assert sel.module_id == 'm1'
        assert sel.capability == 'memory_management'
        assert sel.priority == 0.0

    def test_with_alternatives(self) -> None:
        sel = ModuleSelection(
            module_id='m1',
            capability='dialogue_processing',
            alternatives=('alt1', 'alt2'),
        )
        assert len(sel.alternatives) == 2


class TestDependencyEdge:
    def test_default_creation(self) -> None:
        edge = DependencyEdge(source='a', target='b')
        assert edge.source == 'a'
        assert edge.target == 'b'
        assert edge.is_critical is True

    def test_non_critical(self) -> None:
        edge = DependencyEdge(source='a', target='b', is_critical=False)
        assert edge.is_critical is False


class TestExecutionStep:
    def test_default_creation(self) -> None:
        step = ExecutionStep(step_id='s1', module_id='m1', action='process')
        assert step.step_id == 's1'
        assert step.status == 'pending'


class TestOrchestrationObject:
    def test_valid_status(self) -> None:
        obj = OrchestrationObject(orchestration_id='o1', current_status='pending')
        assert obj.orchestration_id == 'o1'
        assert obj.current_status == 'pending'

    def test_all_valid_statuses(self) -> None:
        for status in ORCHESTRATION_STATUSES:
            obj = OrchestrationObject(orchestration_id='o1', current_status=status)
            assert obj.current_status == status

    def test_invalid_status_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid status"):
            OrchestrationObject(orchestration_id='o1', current_status='invalid')

    def test_frozen(self) -> None:
        obj = OrchestrationObject(orchestration_id='o1')
        with pytest.raises(AttributeError):
            obj.orchestration_id = 'o2'  # type: ignore[misc]


class TestOrchestrationResult:
    def test_has_errors_false(self) -> None:
        result = OrchestrationResult()
        assert result.has_errors is False

    def test_has_errors_true(self) -> None:
        result = OrchestrationResult(errors=('err1',))
        assert result.has_errors is True

    def test_module_count(self) -> None:
        result = OrchestrationResult(
            selected_modules=(
                ModuleSelection(module_id='m1'),
                ModuleSelection(module_id='m2'),
            ),
        )
        assert result.module_count == 2


class TestConstants:
    def test_orchestration_statuses(self) -> None:
        assert 'pending' in ORCHESTRATION_STATUSES
        assert 'completed' in ORCHESTRATION_STATUSES
        assert 'failed' in ORCHESTRATION_STATUSES

    def test_module_capabilities(self) -> None:
        assert 'memory_management' in MODULE_CAPABILITIES
        assert 'dialogue_processing' in MODULE_CAPABILITIES

    def test_execution_strategies(self) -> None:
        assert 'sequential' in EXECUTION_STRATEGIES
        assert 'parallel' in EXECUTION_STRATEGIES


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestCognitiveOrchestrator:
    def setup_method(self) -> None:
        self.orchestrator = CognitiveOrchestrator()

    def test_default_orchestration(self) -> None:
        result = self.orchestrator.orchestrate(
            task_description='Test task',
            task_id='t1',
        )
        assert result.orchestration_id
        assert result.orchestration_object is not None
        assert result.duration_ms >= 0

    def test_orchestration_with_registered_modules(self) -> None:
        self.orchestrator.register_module('mem', ('memory_management',))
        self.orchestrator.register_module('dlg', ('dialogue_processing',))
        result = self.orchestrator.orchestrate(
            task_description='Multi-module task',
            required_capabilities=['memory_management', 'dialogue_processing'],
        )
        assert result.module_count >= 1

    def test_orchestration_completes_all_phases(self) -> None:
        result = self.orchestrator.orchestrate(
            task_description='Full pipeline test',
            task_id='t2',
        )
        assert result.orchestration_object is not None
        assert result.orchestration_object.current_status in ('completed', 'failed')
        assert len(result.execution_steps) > 0

    def test_orchestration_with_context(self) -> None:
        result = self.orchestrator.orchestrate(
            task_description='Context test',
            context={'priority': 0.9, 'complexity': 'high'},
        )
        assert result.orchestration_object is not None
        assert result.confidence >= 0.0

    def test_orchestration_result_is_frozen(self) -> None:
        result = self.orchestrator.orchestrate(task_description='Frozen test')
        with pytest.raises(AttributeError):
            result.orchestration_id = 'changed'  # type: ignore[misc]

    def test_orchestration_with_required_capabilities(self) -> None:
        result = self.orchestrator.orchestrate(
            task_description='Capability-specific',
            required_capabilities=['inference', 'knowledge_retrieval'],
        )
        assert result.module_count >= 1

    def test_empty_task(self) -> None:
        result = self.orchestrator.orchestrate()
        assert result.orchestration_id
        assert result.duration_ms >= 0

    def test_explainability_metadata(self) -> None:
        result = self.orchestrator.orchestrate(
            task_description='Explainability test',
        )
        meta = result.orchestration_object.explainability_metadata
        assert 'reasoning_chain' in meta
        assert len(meta['reasoning_chain']) > 0
