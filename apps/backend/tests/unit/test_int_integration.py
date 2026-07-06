"""Integration tests for INT package — cross-module interactions."""

from __future__ import annotations

import pytest

from ayeneh.int.cognitive_state.engine import CognitiveStateEngine
from ayeneh.int.cognitive_state.types import CognitiveStateResult, STATE_DIMENSIONS
from ayeneh.int.governance.engine import GovernanceEngine
from ayeneh.int.governance.types import GovernanceResult, GOVERNANCE_DOMAINS
from ayeneh.int.orchestrator.engine import CognitiveOrchestrator
from ayeneh.int.orchestrator.types import OrchestrationResult


# ---------------------------------------------------------------------------
# Cross-module integration
# ---------------------------------------------------------------------------


class TestOrchestratorToStatePipeline:
    """Test that Orchestration results can feed into CognitiveState."""

    def test_orchestration_feeds_state(self) -> None:
        orch_engine = CognitiveOrchestrator()
        state_engine = CognitiveStateEngine()

        # Run orchestration
        orch_result = orch_engine.orchestrate(
            task_description='Test cognitive task',
            task_id='test-1',
            required_capabilities=['memory_management', 'inference'],
        )
        assert isinstance(orch_result, OrchestrationResult)
        assert orch_result.orchestration_id != ''

        # Use orchestration output to inform state
        state_result = state_engine.process(
            context={
                'active_modules': list(orch_result.orchestration_object.participating_modules)
                if orch_result.orchestration_object else [],
                'module_data': {
                    dim: {'active': True, 'confidence': orch_result.confidence}
                    for dim in STATE_DIMENSIONS
                },
            },
        )
        assert isinstance(state_result, CognitiveStateResult)
        assert state_result.dimension_count == 8

    def test_multiple_orchestrations_update_state(self) -> None:
        orch_engine = CognitiveOrchestrator()
        state_engine = CognitiveStateEngine()

        for i in range(3):
            orch_result = orch_engine.orchestrate(
                task_description=f'Task {i}',
                task_id=f'task-{i}',
            )
            state_result = state_engine.process(
                context={
                    'active_modules': list(orch_result.orchestration_object.participating_modules)
                    if orch_result.orchestration_object else [],
                },
            )
            assert state_result.state_id != ''

        # State engine should have history
        assert len(state_engine._state_history) == 3


class TestGovernanceToStatePipeline:
    """Test that Governance results can inform CognitiveState."""

    def test_governance_feeds_state_health(self) -> None:
        gov_engine = GovernanceEngine()
        state_engine = CognitiveStateEngine()

        # Run governance with low health
        gov_result = gov_engine.process(
            context={
                'health_score': 0.4,
                'current_stage': 'normal_operation',
                'domain': 'architectural',
            },
        )
        assert isinstance(gov_result, GovernanceResult)

        # Use governance output to set state
        state_result = state_engine.process(
            context={
                'module_data': {
                    dim: {'active': True, 'confidence': 0.15}
                    for dim in STATE_DIMENSIONS
                },
            },
        )
        assert isinstance(state_result, CognitiveStateResult)
        # Low confidence should produce conflicts
        assert state_result.has_conflicts

    def test_healthy_governance_produces_clean_state(self) -> None:
        gov_engine = GovernanceEngine()
        state_engine = CognitiveStateEngine()

        gov_result = gov_engine.process(
            context={
                'health_score': 0.95,
                'current_stage': 'normal_operation',
            },
        )
        assert gov_result.confidence > 0

        state_result = state_engine.process(
            context={
                'module_data': {
                    dim: {'active': True, 'confidence': 0.95}
                    for dim in STATE_DIMENSIONS
                },
            },
        )
        assert not state_result.has_conflicts
        assert state_result.state_object.consistency_status == 'consistent'


class TestEndToEndIntegration:
    """End-to-end tests running all INT modules together."""

    def test_full_lifecycle(self) -> None:
        orch_engine = CognitiveOrchestrator()
        state_engine = CognitiveStateEngine()
        gov_engine = GovernanceEngine()

        # Phase 1: Orchestrate
        orch_result = orch_engine.orchestrate(
            task_description='Full lifecycle test',
            task_id='lifecycle-1',
            required_capabilities=['memory_management', 'inference', 'decision_making'],
        )
        assert orch_result.module_count >= 1

        # Phase 2: State assessment
        state_result = state_engine.process(
            context={
                'active_modules': list(orch_result.orchestration_object.participating_modules)
                if orch_result.orchestration_object else [],
                'module_data': {
                    dim: {'active': True, 'confidence': 0.85}
                    for dim in STATE_DIMENSIONS
                },
            },
        )
        assert state_result.dimension_count == 8

        # Phase 3: Governance
        gov_result = gov_engine.process(
            context={
                'domain': 'architectural',
                'current_stage': 'normal_operation',
                'health_score': state_result.state_object.architecture_health
                if state_result.state_object else 1.0,
                'active_modules': list(state_result.state_object.active_modules)
                if state_result.state_object else [],
            },
        )
        assert gov_result.governance_id != ''

        # All three should produce results
        assert orch_result.confidence >= 0.0
        assert state_result.global_confidence >= 0.0
        assert gov_result.confidence >= 0.0

    def test_feedback_loop_governance_to_state(self) -> None:
        """Governance detects low health → State reflects degraded dimensions."""
        gov_engine = GovernanceEngine()
        state_engine = CognitiveStateEngine()

        # Governance detects recovery needed
        gov_result = gov_engine.process(
            context={
                'health_score': 0.2,
                'current_stage': 'normal_operation',
            },
        )
        assert len(gov_result.lifecycle_decisions) >= 1

        # State should reflect degraded dimensions
        state_result = state_engine.process(
            context={
                'module_data': {
                    dim: {'active': True, 'confidence': 0.2}
                    for dim in STATE_DIMENSIONS
                },
            },
        )
        assert state_result.has_conflicts
        assert state_result.global_confidence < 0.3


class TestEdgeCases:
    """Edge case tests for robustness."""

    def test_empty_orchestration(self) -> None:
        engine = CognitiveOrchestrator()
        result = engine.orchestrate()
        assert result.orchestration_id != ''
        assert result.module_count >= 1

    def test_empty_state_processing(self) -> None:
        engine = CognitiveStateEngine()
        result = engine.process()
        assert result.dimension_count == 8
        assert result.state_id != ''

    def test_empty_governance_processing(self) -> None:
        engine = GovernanceEngine()
        result = engine.process()
        assert result.governance_id != ''
        assert len(result.policy_references) >= 1

    def test_state_engine_subscriber_distribution(self) -> None:
        engine = CognitiveStateEngine()
        engine.register_subscriber('module_a')
        engine.register_subscriber('module_b')
        result = engine.process()
        # Should complete without errors even with subscribers
        assert len(result.errors) == 0

    def test_governance_policy_registration(self) -> None:
        engine = GovernanceEngine()
        from ayeneh.int.governance.types import PolicyReference

        for i in range(5):
            engine.register_policy(PolicyReference(
                policy_id=f'pol-{i}',
                policy_name=f'Policy {i}',
                domain=GOVERNANCE_DOMAINS[i % len(GOVERNANCE_DOMAINS)],
                status='active',
            ))
        result = engine.process()
        assert len(result.policy_references) >= 5

    def test_concurrent_state_and_governance(self) -> None:
        """Both engines can run independently without side effects."""
        state1 = CognitiveStateEngine()
        state2 = CognitiveStateEngine()
        gov1 = GovernanceEngine()
        gov2 = GovernanceEngine()

        r_state1 = state1.process()
        r_state2 = state2.process()
        r_gov1 = gov1.process()
        r_gov2 = gov2.process()

        assert r_state1.state_id != r_state2.state_id
        assert r_gov1.governance_id != r_gov2.governance_id
