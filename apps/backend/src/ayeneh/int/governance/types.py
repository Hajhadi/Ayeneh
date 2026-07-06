"""INT-05 System Governance — domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


GOVERNANCE_DOMAINS = [
    'architectural',
    'knowledge',
    'memory',
    'workflow',
    'resource',
    'evolution',
    'ethical',
    'security',
]

LIFECYCLE_STAGES = [
    'initialization',
    'configuration',
    'normal_operation',
    'adaptive_learning',
    'architectural_revision',
    'maintenance',
    'recovery',
    'archival',
]

POLICY_STATUSES = [
    'pending',
    'active',
    'enforced',
    'suspended',
    'revoked',
    'archived',
]

APPROVAL_STATUSES = [
    'pending',
    'approved',
    'rejected',
    'conditionally_approved',
    'deferred',
    'expired',
]

AUDIT_OUTCOMES = [
    'compliant',
    'non_compliant',
    'partial',
    'exempt',
    'under_review',
]


@dataclass(frozen=True)
class PolicyReference:
    """Reference to a governance policy."""

    policy_id: str = ''
    policy_name: str = ''
    policy_version: str = ''
    domain: str = ''
    status: str = 'pending'
    effective_date: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.domain and self.domain not in GOVERNANCE_DOMAINS:
            raise ValueError(
                f"Invalid domain: {self.domain!r}. "
                f"Must be one of {GOVERNANCE_DOMAINS}"
            )


@dataclass(frozen=True)
class ConstraintEvaluation:
    """Result of evaluating a constraint against a governance decision."""

    constraint_id: str = ''
    constraint_type: str = ''  # 'hard', 'soft', 'advisory'
    satisfied: bool = True
    deviation: float = 0.0
    justification: str = ''


@dataclass(frozen=True)
class AuditRecord:
    """Immutable record of a governance audit event."""

    audit_id: str = ''
    decision: str = ''
    evidence: tuple[str, ...] = ()
    responsible_modules: tuple[str, ...] = ()
    affected_resources: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    outcome: str = ''


@dataclass(frozen=True)
class LifecycleDecision:
    """Decision made during lifecycle management."""

    decision_id: str = ''
    current_stage: str = ''
    target_stage: str = ''
    trigger: str = ''
    reasoning: str = ''
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class EnforcementAction:
    """Action taken to enforce a governance policy."""

    action_id: str = ''
    policy_id: str = ''
    action_type: str = ''  # 'block', 'warn', 'modify', 'escalate'
    target_module: str = ''
    description: str = ''
    executed: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ExplainabilityMetadata:
    """Metadata supporting explanation of governance decisions."""

    reasoning_chain: tuple[str, ...] = ()
    contributing_factors: tuple[dict[str, Any], ...] = ()
    confidence_decomposition: dict[str, float] = field(default_factory=dict)
    decision_points: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class GovernanceObject:
    """Core domain object representing a governance decision."""

    governance_id: str
    policy_reference: str = ''
    affected_modules: tuple[str, ...] = ()
    lifecycle_stage: str = 'normal_operation'
    decision: str = ''
    supporting_evidence: tuple[str, ...] = ()
    constraint_evaluation: dict[str, Any] = field(default_factory=dict)
    approval_status: str = 'pending'
    audit_trail: tuple[dict[str, Any], ...] = ()
    version_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernanceResult:
    """Complete result from the GovernanceEngine pipeline."""

    governance_id: str = ''
    governance_object: GovernanceObject | None = None
    lifecycle_decisions: tuple[LifecycleDecision, ...] = ()
    enforcement_actions: tuple[EnforcementAction, ...] = ()
    audit_records: tuple[AuditRecord, ...] = ()
    policy_references: tuple[PolicyReference, ...] = ()
    constraint_evaluations: tuple[ConstraintEvaluation, ...] = ()
    confidence: float = 0.0
    duration_ms: float = 0.0
    errors: tuple[str, ...] = ()
    pipeline_phases_completed: tuple[str, ...] = ()

    @property
    def has_enforcement_actions(self) -> bool:
        return len(self.enforcement_actions) > 0

    @property
    def audit_count(self) -> int:
        return len(self.audit_records)
