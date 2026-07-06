"""INT-05 System Governance — 8-phase pipeline engine."""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog

from ayeneh.int.governance.types import (
    APPROVAL_STATUSES,
    AUDIT_OUTCOMES,
    GOVERNANCE_DOMAINS,
    LIFECYCLE_STAGES,
    AuditRecord,
    ConstraintEvaluation,
    EnforcementAction,
    ExplainabilityMetadata,
    GovernanceObject,
    GovernanceResult,
    LifecycleDecision,
    PolicyReference,
)

logger = structlog.get_logger(__name__)


class GovernanceEngine:
    """Manages system governance through an 8-phase pipeline.

    Phases:
        1. ArchitectureState       — assess current architecture state
        2. PolicyEvaluation        — evaluate applicable policies
        3. ConstraintValidation    — validate constraints
        4. LifecycleDecision       — determine lifecycle transitions
        5. GovernanceEnforcement   — enforce governance decisions
        6. AuditLogging            — log audit records
        7. SystemUpdate            — update governance state
        8. GovernanceArchive       — archive completed governance items
    """

    def __init__(self) -> None:
        self._policies: dict[str, PolicyReference] = {}
        self._governance_history: list[GovernanceObject] = []

    def register_policy(self, policy: PolicyReference) -> None:
        self._policies[policy.policy_id] = policy

    def process(
        self,
        context: dict[str, Any] | None = None,
        session_id: str = '',
    ) -> GovernanceResult:
        start = time.monotonic()
        ctx = context or {}
        errors: list[str] = []
        phases: list[str] = []

        logger.info(
            "governance_pipeline_started",
            session_id=session_id,
        )

        # Phase 1: ArchitectureState
        arch_state = self._phase_architecture_state(ctx, errors)
        phases.append('ArchitectureState')

        # Phase 2: PolicyEvaluation
        policies = self._phase_policy_evaluation(ctx, arch_state, errors)
        phases.append('PolicyEvaluation')

        # Phase 3: ConstraintValidation
        constraints = self._phase_constraint_validation(ctx, policies, errors)
        phases.append('ConstraintValidation')

        # Phase 4: LifecycleDecision
        lifecycle_decisions = self._phase_lifecycle_decision(
            ctx, arch_state, constraints, errors,
        )
        phases.append('LifecycleDecision')

        # Phase 5: GovernanceEnforcement
        enforcement_actions = self._phase_governance_enforcement(
            policies, lifecycle_decisions, errors,
        )
        phases.append('GovernanceEnforcement')

        # Phase 6: AuditLogging
        audit_records = self._phase_audit_logging(
            policies, lifecycle_decisions, enforcement_actions, errors,
        )
        phases.append('AuditLogging')

        # Phase 7: SystemUpdate
        governance_id = str(uuid.uuid4())
        governance_obj = self._phase_system_update(
            governance_id, ctx, policies, lifecycle_decisions,
            enforcement_actions, audit_records, errors,
        )
        phases.append('SystemUpdate')

        # Phase 8: GovernanceArchive
        self._phase_governance_archive(governance_obj, errors)
        phases.append('GovernanceArchive')

        duration_ms = (time.monotonic() - start) * 1000

        # Compute confidence
        if policies:
            confidence = sum(
                1.0 if p.status == 'active' else 0.5
                for p in policies
            ) / len(policies)
        else:
            confidence = 0.5

        logger.info(
            "governance_pipeline_completed",
            governance_id=governance_id,
            policies=len(policies),
            enforcement=len(enforcement_actions),
            audits=len(audit_records),
            duration_ms=duration_ms,
        )

        return GovernanceResult(
            governance_id=governance_id,
            governance_object=governance_obj,
            lifecycle_decisions=tuple(lifecycle_decisions),
            enforcement_actions=tuple(enforcement_actions),
            audit_records=tuple(audit_records),
            policy_references=tuple(policies),
            constraint_evaluations=tuple(constraints),
            confidence=confidence,
            duration_ms=duration_ms,
            errors=tuple(errors),
            pipeline_phases_completed=tuple(phases),
        )

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    def _phase_architecture_state(
        self,
        ctx: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        """Phase 1: Assess current architecture state."""
        try:
            state = {
                'active_modules': ctx.get('active_modules', []),
                'current_stage': ctx.get('current_stage', 'normal_operation'),
                'health_score': ctx.get('health_score', 1.0),
                'resource_utilization': ctx.get('resource_utilization', {}),
                'recent_events': ctx.get('recent_events', []),
                'domain': ctx.get('domain', 'architectural'),
            }
            if state['domain'] not in GOVERNANCE_DOMAINS:
                state['domain'] = 'architectural'
            logger.debug("phase_architecture_state_completed")
            return state
        except Exception as exc:
            errors.append(f"Phase 1 (ArchitectureState) error: {exc}")
            return {'active_modules': [], 'current_stage': 'normal_operation', 'health_score': 1.0}

    def _phase_policy_evaluation(
        self,
        ctx: dict[str, Any],
        arch_state: dict[str, Any],
        errors: list[str],
    ) -> list[PolicyReference]:
        """Phase 2: Evaluate applicable policies."""
        try:
            policies: list[PolicyReference] = []

            # Include registered policies
            for policy in self._policies.values():
                policies.append(policy)

            # Include policies from context
            for p_data in ctx.get('policies', []):
                if isinstance(p_data, dict):
                    policies.append(PolicyReference(
                        policy_id=p_data.get('policy_id', str(uuid.uuid4())),
                        policy_name=p_data.get('policy_name', ''),
                        policy_version=p_data.get('policy_version', '1.0'),
                        domain=p_data.get('domain', arch_state.get('domain', 'architectural')),
                        status=p_data.get('status', 'active'),
                    ))
                elif isinstance(p_data, PolicyReference):
                    policies.append(p_data)

            # Ensure at least one default policy
            if not policies:
                policies.append(PolicyReference(
                    policy_id='default_policy',
                    policy_name='Default Governance Policy',
                    domain=arch_state.get('domain', 'architectural'),
                    status='active',
                ))

            logger.debug("phase_policy_evaluation_completed", count=len(policies))
            return policies
        except Exception as exc:
            errors.append(f"Phase 2 (PolicyEvaluation) error: {exc}")
            return [PolicyReference(policy_id='fallback', policy_name='Fallback')]

    def _phase_constraint_validation(
        self,
        ctx: dict[str, Any],
        policies: list[PolicyReference],
        errors: list[str],
    ) -> list[ConstraintEvaluation]:
        """Phase 3: Validate constraints."""
        try:
            constraints: list[ConstraintEvaluation] = []

            for policy in policies:
                constraints.append(ConstraintEvaluation(
                    constraint_id=f"constraint_{policy.policy_id}",
                    constraint_type='hard',
                    satisfied=policy.status in ('active', 'enforced'),
                    deviation=0.0,
                    justification=f"Policy {policy.policy_name} is {policy.status}",
                ))

            # Check context-defined constraints
            for c_data in ctx.get('constraints', []):
                if isinstance(c_data, dict):
                    constraints.append(ConstraintEvaluation(
                        constraint_id=c_data.get('constraint_id', str(uuid.uuid4())),
                        constraint_type=c_data.get('type', 'soft'),
                        satisfied=c_data.get('satisfied', True),
                        deviation=c_data.get('deviation', 0.0),
                        justification=c_data.get('justification', ''),
                    ))

            logger.debug("phase_constraint_validation_completed", count=len(constraints))
            return constraints
        except Exception as exc:
            errors.append(f"Phase 3 (ConstraintValidation) error: {exc}")
            return []

    def _phase_lifecycle_decision(
        self,
        ctx: dict[str, Any],
        arch_state: dict[str, Any],
        constraints: list[ConstraintEvaluation],
        errors: list[str],
    ) -> list[LifecycleDecision]:
        """Phase 4: Determine lifecycle transitions."""
        try:
            decisions: list[LifecycleDecision] = []
            current_stage = ctx.get('current_stage', 'normal_operation')

            if current_stage not in LIFECYCLE_STAGES:
                current_stage = 'normal_operation'

            # Determine target stage based on conditions
            target_stage = current_stage
            trigger = 'no_change'
            reasoning = 'System operating normally'

            health = arch_state.get('health_score', 1.0)
            unsatisfied = [c for c in constraints if not c.satisfied]

            if health < 0.3:
                target_stage = 'recovery'
                trigger = 'low_health'
                reasoning = f'Health score {health:.2f} below critical threshold'
            elif health < 0.6:
                target_stage = 'maintenance'
                trigger = 'degraded_health'
                reasoning = f'Health score {health:.2f} in degraded range'
            elif unsatisfied:
                target_stage = 'configuration'
                trigger = 'constraint_violation'
                reasoning = f'{len(unsatisfied)} constraint(s) not satisfied'

            if target_stage != current_stage:
                decisions.append(LifecycleDecision(
                    decision_id=str(uuid.uuid4()),
                    current_stage=current_stage,
                    target_stage=target_stage,
                    trigger=trigger,
                    reasoning=reasoning,
                    confidence=0.8,
                ))

            logger.debug("phase_lifecycle_decision_completed", decisions=len(decisions))
            return decisions
        except Exception as exc:
            errors.append(f"Phase 4 (LifecycleDecision) error: {exc}")
            return []

    def _phase_governance_enforcement(
        self,
        policies: list[PolicyReference],
        lifecycle_decisions: list[LifecycleDecision],
        errors: list[str],
    ) -> list[EnforcementAction]:
        """Phase 5: Enforce governance decisions."""
        try:
            actions: list[EnforcementAction] = []

            for decision in lifecycle_decisions:
                if decision.target_stage in ('recovery', 'maintenance'):
                    actions.append(EnforcementAction(
                        action_id=str(uuid.uuid4()),
                        policy_id='lifecycle_policy',
                        action_type='escalate',
                        target_module='architecture_manager',
                        description=f"Escalate to {decision.target_stage}: {decision.reasoning}",
                        executed=True,
                    ))

            # Enforce policy compliance
            for policy in policies:
                if policy.status not in ('active', 'enforced'):
                    actions.append(EnforcementAction(
                        action_id=str(uuid.uuid4()),
                        policy_id=policy.policy_id,
                        action_type='warn',
                        target_module='policy_manager',
                        description=f"Policy {policy.policy_name} is {policy.status}",
                        executed=True,
                    ))

            logger.debug("phase_governance_enforcement_completed", actions=len(actions))
            return actions
        except Exception as exc:
            errors.append(f"Phase 5 (GovernanceEnforcement) error: {exc}")
            return []

    def _phase_audit_logging(
        self,
        policies: list[PolicyReference],
        lifecycle_decisions: list[LifecycleDecision],
        enforcement_actions: list[EnforcementAction],
        errors: list[str],
    ) -> list[AuditRecord]:
        """Phase 6: Log audit records."""
        try:
            records: list[AuditRecord] = []

            # Audit each lifecycle decision
            for decision in lifecycle_decisions:
                outcome = 'compliant' if decision.confidence > 0.5 else 'under_review'
                records.append(AuditRecord(
                    audit_id=str(uuid.uuid4()),
                    decision=f"Lifecycle: {decision.current_stage} → {decision.target_stage}",
                    evidence=(decision.reasoning,),
                    responsible_modules=('governance_engine',),
                    affected_resources=(),
                    outcome=outcome,
                ))

            # Audit each enforcement action
            for action in enforcement_actions:
                records.append(AuditRecord(
                    audit_id=str(uuid.uuid4()),
                    decision=f"Enforcement: {action.action_type} on {action.target_module}",
                    evidence=(action.description,),
                    responsible_modules=(action.target_module,),
                    affected_resources=(),
                    outcome='compliant',
                ))

            # Audit policy status
            for policy in policies:
                if policy.status not in ('active', 'enforced'):
                    records.append(AuditRecord(
                        audit_id=str(uuid.uuid4()),
                        decision=f"Policy status: {policy.policy_name} is {policy.status}",
                        evidence=(f"Policy {policy.policy_id} status check",),
                        responsible_modules=('policy_manager',),
                        affected_resources=(policy.policy_id,),
                        outcome='under_review',
                    ))

            logger.debug("phase_audit_logging_completed", records=len(records))
            return records
        except Exception as exc:
            errors.append(f"Phase 6 (AuditLogging) error: {exc}")
            return []

    def _phase_system_update(
        self,
        governance_id: str,
        ctx: dict[str, Any],
        policies: list[PolicyReference],
        lifecycle_decisions: list[LifecycleDecision],
        enforcement_actions: list[EnforcementAction],
        audit_records: list[AuditRecord],
        errors: list[str],
    ) -> GovernanceObject:
        """Phase 7: Update governance state."""
        try:
            affected_modules = tuple(ctx.get('active_modules', ()))
            current_stage = ctx.get('current_stage', 'normal_operation')

            # Determine approval status
            approval_status = 'approved'
            if enforcement_actions:
                approval_status = 'conditionally_approved'
            if any(a.action_type == 'block' for a in enforcement_actions):
                approval_status = 'rejected'

            explainability = ExplainabilityMetadata(
                reasoning_chain=(
                    f"Evaluated {len(policies)} policies",
                    f"Made {len(lifecycle_decisions)} lifecycle decisions",
                    f"Executed {len(enforcement_actions)} enforcement actions",
                    f"Logged {len(audit_records)} audit records",
                ),
                contributing_factors=tuple(
                    {'policy': p.policy_name, 'status': p.status}
                    for p in policies
                ),
            )

            obj = GovernanceObject(
                governance_id=governance_id,
                policy_reference=policies[0].policy_id if policies else '',
                affected_modules=affected_modules,
                lifecycle_stage=current_stage,
                decision=f"Governance cycle completed with {len(audit_records)} audit records",
                supporting_evidence=tuple(a.decision for a in audit_records),
                constraint_evaluation={
                    'policies_evaluated': len(policies),
                    'decisions_made': len(lifecycle_decisions),
                    'enforcements': len(enforcement_actions),
                },
                approval_status=approval_status,
                audit_trail=tuple(
                    {'audit_id': a.audit_id, 'decision': a.decision, 'outcome': a.outcome}
                    for a in audit_records
                ),
                explainability_metadata={
                    'reasoning_chain': explainability.reasoning_chain,
                    'contributing_factors': explainability.contributing_factors,
                },
            )

            self._governance_history.append(obj)
            logger.debug("phase_system_update_completed", governance_id=governance_id)
            return obj
        except Exception as exc:
            errors.append(f"Phase 7 (SystemUpdate) error: {exc}")
            return GovernanceObject(
                governance_id=governance_id,
                approval_status='rejected',
                decision=f"System update failed: {exc}",
            )

    def _phase_governance_archive(
        self,
        governance_obj: GovernanceObject,
        errors: list[str],
    ) -> None:
        """Phase 8: Archive completed governance items."""
        try:
            # Archive old governance objects (keep last 100)
            if len(self._governance_history) > 100:
                self._governance_history = self._governance_history[-100:]

            logger.debug(
                "phase_governance_archive_completed",
                history_size=len(self._governance_history),
            )
        except Exception as exc:
            errors.append(f"Phase 8 (GovernanceArchive) error: {exc}")
