"""Tests for INT-05 System Governance."""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from ayeneh.int.governance.types import (
    APPROVAL_STATUSES,
    AUDIT_OUTCOMES,
    GOVERNANCE_DOMAINS,
    LIFECYCLE_STAGES,
    POLICY_STATUSES,
    AuditRecord,
    ConstraintEvaluation,
    EnforcementAction,
    ExplainabilityMetadata,
    GovernanceObject,
    GovernanceResult,
    LifecycleDecision,
    PolicyReference,
)
from ayeneh.int.governance.engine import GovernanceEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return GovernanceEngine()


@pytest.fixture
def sample_context():
    return {
        'domain': 'architectural',
        'current_stage': 'normal_operation',
        'active_modules': ['cog', 'inf', 'dlg'],
        'health_score': 0.9,
        'policies': [
            {'policy_id': 'pol-1', 'policy_name': 'Security Policy', 'domain': 'security', 'status': 'active'},
        ],
        'constraints': [
            {'constraint_id': 'con-1', 'type': 'hard', 'satisfied': True},
        ],
    }


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestGovernanceTypes:
    """Tests for INT-05 type definitions."""

    def test_governance_domains_count(self):
        assert len(GOVERNANCE_DOMAINS) == 8

    def test_governance_domains_include_expected(self):
        expected = {
            'architectural', 'knowledge', 'memory', 'workflow',
            'resource', 'evolution', 'ethical', 'security',
        }
        assert set(GOVERNANCE_DOMAINS) == expected

    def test_lifecycle_stages_count(self):
        assert len(LIFECYCLE_STAGES) == 8

    def test_lifecycle_stages_include_expected(self):
        expected = {
            'initialization', 'configuration', 'normal_operation',
            'adaptive_learning', 'architectural_revision', 'maintenance',
            'recovery', 'archival',
        }
        assert set(LIFECYCLE_STAGES) == expected

    def test_policy_statuses_count(self):
        assert len(POLICY_STATUSES) == 6

    def test_approval_statuses_count(self):
        assert len(APPROVAL_STATUSES) == 6

    def test_audit_outcomes_count(self):
        assert len(AUDIT_OUTCOMES) == 5


class TestGovernanceDataclasses:
    """Tests for INT-05 frozen dataclasses."""

    def test_policy_reference_creation(self):
        pr = PolicyReference(
            policy_id='p-1',
            policy_name='Test Policy',
            domain='architectural',
            status='active',
        )
        assert pr.policy_id == 'p-1'
        assert pr.domain == 'architectural'
        assert pr.status == 'active'

    def test_policy_reference_invalid_domain(self):
        with pytest.raises(ValueError, match="Invalid domain"):
            PolicyReference(domain='nonexistent')

    def test_policy_reference_valid_domains(self):
        for domain in GOVERNANCE_DOMAINS:
            pr = PolicyReference(domain=domain)
            assert pr.domain == domain

    def test_policy_reference_immutability(self):
        pr = PolicyReference(policy_id='p-1')
        with pytest.raises(AttributeError):
            pr.policy_id = 'p-2'  # type: ignore[misc]

    def test_constraint_evaluation_creation(self):
        ce = ConstraintEvaluation(
            constraint_id='c-1',
            constraint_type='hard',
            satisfied=True,
            deviation=0.0,
        )
        assert ce.constraint_id == 'c-1'
        assert ce.satisfied is True

    def test_audit_record_creation(self):
        ar = AuditRecord(
            audit_id='a-1',
            decision='Enforce policy',
            evidence=('evidence-1', 'evidence-2'),
            responsible_modules=('module_a',),
            affected_resources=('resource_1',),
            outcome='compliant',
        )
        assert ar.audit_id == 'a-1'
        assert ar.outcome == 'compliant'
        assert len(ar.evidence) == 2

    def test_audit_record_immutability(self):
        ar = AuditRecord(audit_id='a-1')
        with pytest.raises(AttributeError):
            ar.audit_id = 'a-2'  # type: ignore[misc]

    def test_lifecycle_decision_creation(self):
        ld = LifecycleDecision(
            decision_id='ld-1',
            current_stage='normal_operation',
            target_stage='maintenance',
            trigger='low_health',
            reasoning='Health dropped',
            confidence=0.8,
        )
        assert ld.decision_id == 'ld-1'
        assert ld.current_stage == 'normal_operation'
        assert ld.target_stage == 'maintenance'

    def test_enforcement_action_creation(self):
        ea = EnforcementAction(
            action_id='ea-1',
            policy_id='p-1',
            action_type='block',
            target_module='module_a',
            description='Block module',
            executed=True,
        )
        assert ea.action_id == 'ea-1'
        assert ea.executed is True

    def test_governance_object_creation(self):
        go = GovernanceObject(governance_id='gov-1')
        assert go.governance_id == 'gov-1'
        assert go.policy_reference == ''
        assert go.affected_modules == ()
        assert go.lifecycle_stage == 'normal_operation'
        assert go.decision == ''
        assert go.supporting_evidence == ()
        assert go.constraint_evaluation == {}
        assert go.approval_status == 'pending'
        assert go.audit_trail == ()
        assert go.version_history == ()
        assert isinstance(go.creation_timestamp, datetime)
        assert go.explainability_metadata == {}

    def test_governance_object_immutability(self):
        go = GovernanceObject(governance_id='gov-1')
        with pytest.raises(AttributeError):
            go.governance_id = 'gov-2'  # type: ignore[misc]

    def test_governance_result_creation(self):
        gr = GovernanceResult(governance_id='gr-1')
        assert gr.governance_id == 'gr-1'
        assert gr.governance_object is None
        assert gr.lifecycle_decisions == ()
        assert gr.enforcement_actions == ()
        assert gr.audit_records == ()
        assert gr.policy_references == ()
        assert gr.constraint_evaluations == ()
        assert gr.confidence == 0.0
        assert gr.duration_ms == 0.0
        assert gr.errors == ()
        assert gr.pipeline_phases_completed == ()

    def test_governance_result_has_enforcement_actions_false(self):
        gr = GovernanceResult()
        assert gr.has_enforcement_actions is False

    def test_governance_result_has_enforcement_actions_true(self):
        gr = GovernanceResult(
            enforcement_actions=(EnforcementAction(action_id='ea-1'),),
        )
        assert gr.has_enforcement_actions is True

    def test_governance_result_audit_count(self):
        gr = GovernanceResult(
            audit_records=(AuditRecord(audit_id='a-1'), AuditRecord(audit_id='a-2')),
        )
        assert gr.audit_count == 2


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestGovernanceEngine:
    """Tests for INT-05 GovernanceEngine."""

    def test_process_empty_request(self, engine):
        result = engine.process()
        assert isinstance(result, GovernanceResult)
        assert len(result.pipeline_phases_completed) == 8
        assert result.governance_id != ''

    def test_process_phases_order(self, engine):
        result = engine.process()
        expected_phases = (
            'ArchitectureState',
            'PolicyEvaluation',
            'ConstraintValidation',
            'LifecycleDecision',
            'GovernanceEnforcement',
            'AuditLogging',
            'SystemUpdate',
            'GovernanceArchive',
        )
        assert result.pipeline_phases_completed == expected_phases

    def test_process_default_policy(self, engine):
        result = engine.process()
        assert len(result.policy_references) >= 1

    def test_process_with_context(self, engine, sample_context):
        result = engine.process(context=sample_context)
        assert result.governance_id != ''
        assert len(result.policy_references) >= 1

    def test_process_confidence_range(self, engine):
        result = engine.process()
        assert 0.0 <= result.confidence <= 1.0

    def test_process_governance_object_created(self, engine):
        result = engine.process()
        assert result.governance_object is not None
        assert result.governance_object.governance_id == result.governance_id

    def test_process_approval_status(self, engine):
        result = engine.process()
        assert result.governance_object is not None
        assert result.governance_object.approval_status in APPROVAL_STATUSES

    def test_process_low_health_triggers_recovery(self, engine):
        ctx = {
            'health_score': 0.2,
            'current_stage': 'normal_operation',
        }
        result = engine.process(context=ctx)
        assert result.governance_object is not None
        assert len(result.lifecycle_decisions) >= 1
        assert result.lifecycle_decisions[0].target_stage == 'recovery'

    def test_process_moderate_health_triggers_maintenance(self, engine):
        ctx = {
            'health_score': 0.5,
            'current_stage': 'normal_operation',
        }
        result = engine.process(context=ctx)
        assert result.governance_object is not None
        if result.lifecycle_decisions:
            assert result.lifecycle_decisions[0].target_stage == 'maintenance'

    def test_register_policy(self, engine):
        policy = PolicyReference(
            policy_id='custom-policy',
            policy_name='Custom Policy',
            domain='security',
            status='active',
        )
        engine.register_policy(policy)
        result = engine.process()
        policy_ids = [p.policy_id for p in result.policy_references]
        assert 'custom-policy' in policy_ids

    def test_process_audit_records_generated(self, engine):
        result = engine.process()
        # At least default policy audit
        assert isinstance(result.audit_records, tuple)

    def test_process_enforcement_actions_for_inactive_policy(self, engine):
        ctx = {
            'policies': [
                {'policy_id': 'inactive', 'policy_name': 'Inactive', 'status': 'suspended'},
            ],
        }
        result = engine.process(context=ctx)
        assert len(result.enforcement_actions) >= 1

    def test_process_constraint_validation(self, engine):
        ctx = {
            'constraints': [
                {'constraint_id': 'c-1', 'type': 'hard', 'satisfied': True},
                {'constraint_id': 'c-2', 'type': 'soft', 'satisfied': False, 'justification': 'test'},
            ],
        }
        result = engine.process(context=ctx)
        assert len(result.constraint_evaluations) >= 2

    def test_process_governance_history(self, engine):
        engine.process()
        engine.process()
        assert len(engine._governance_history) == 2

    def test_process_no_errors(self, engine):
        result = engine.process()
        assert len(result.errors) == 0

    def test_process_duration_positive(self, engine):
        result = engine.process()
        assert result.duration_ms >= 0

    def test_process_with_invalid_domain_defaults(self, engine):
        ctx = {'domain': 'invalid_domain'}
        result = engine.process(context=ctx)
        assert result.governance_id != ''

    def test_archive_limits_history(self, engine):
        for _ in range(110):
            engine.process()
        assert len(engine._governance_history) <= 100
