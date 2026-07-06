"""DEC-01 Decision Support types.

Defines DecisionObject, DecisionContext, TradeOff, MultiCriteriaScore,
DecisionResult, and supporting value objects for the decision support pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

REVERSIBILITY_LEVELS: list[str] = [
    'fully_reversible',
    'partially_reversible',
    'difficult_to_reverse',
    'irreversible',
]

DECISION_CATEGORIES: list[str] = [
    'strategic',
    'tactical',
    'operational',
    'ethical',
    'resource_allocation',
    'relationship',
    'career',
    'creative',
    'research',
    'personal',
]

EVIDENCE_QUALITY_LEVELS: list[str] = [
    'anecdotal',
    'observational',
    'empirical',
    'expert_consensus',
    'rigorous_research',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TradeOff:
    """Represents a trade-off between two options along a dimension."""

    trade_off_id: str
    option_a: str = ''
    option_b: str = ''
    dimension: str = ''
    weight_a: float = 0.0
    weight_b: float = 0.0


@dataclass(frozen=True)
class MultiCriteriaScore:
    """Multi-criteria evaluation score for a decision option."""

    option: str = ''
    goal_alignment: float = 0.0
    evidence_quality: float = 0.0
    risk: float = 0.0
    opportunity: float = 0.0
    ethical: float = 0.0
    sustainability: float = 0.0
    resource_requirement: float = 0.0
    reversibility: float = 0.0
    learning_potential: float = 0.0
    overall: float = 0.0


@dataclass(frozen=True)
class ScenarioOutcome:
    """A predicted outcome from scenario simulation."""

    scenario_id: str
    description: str = ''
    probability: float = 0.0
    impact: float = 0.0
    affected_goals: tuple[str, ...] = ()
    mitigation_strategies: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskAssessment:
    """Assessment of a specific risk associated with a decision."""

    risk_id: str
    description: str = ''
    probability: float = 0.0
    severity: float = 0.0
    mitigations: tuple[str, ...] = ()
    residual_risk: float = 0.0


@dataclass(frozen=True)
class OpportunityAssessment:
    """Assessment of a specific opportunity associated with a decision."""

    opportunity_id: str
    description: str = ''
    probability: float = 0.0
    potential_value: float = 0.0
    requirements: tuple[str, ...] = ()
    time_sensitivity: float = 0.0


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DecisionObject:
    """A single decision produced by the decision support engine (DEC-01)."""

    decision_id: str
    context: str = ''
    question: str = ''
    options: tuple[dict[str, Any], ...] = ()
    goals: tuple[str, ...] = ()
    constraints: tuple[dict[str, Any], ...] = ()
    supporting_evidence: tuple[str, ...] = ()
    competing_hypotheses: tuple[str, ...] = ()
    predicted_outcomes: tuple[dict[str, Any], ...] = ()
    risks: tuple[dict[str, Any], ...] = ()
    opportunities: tuple[dict[str, Any], ...] = ()
    confidence: float = 0.0
    remaining_uncertainty: float = 0.0
    version_history: tuple[dict[str, Any], ...] = ()
    creation_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explainability_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecisionContext:
    """Contextual information surrounding a decision."""

    current_goals: tuple[str, ...] = ()
    relevant_projects: tuple[str, ...] = ()
    identity_considerations: tuple[str, ...] = ()
    behavioral_history: tuple[str, ...] = ()
    available_resources: tuple[str, ...] = ()
    environmental_constraints: tuple[str, ...] = ()
    time_constraints: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecisionResult:
    """Complete result of the decision support pipeline."""

    decision: DecisionObject = field(default_factory=lambda: DecisionObject(decision_id=''))
    context: DecisionContext = field(default_factory=DecisionContext)
    trade_offs: tuple[TradeOff, ...] = ()
    multi_criteria_scores: tuple[MultiCriteriaScore, ...] = ()
    scenarios: tuple[ScenarioOutcome, ...] = ()
    risks: tuple[RiskAssessment, ...] = ()
    opportunities: tuple[OpportunityAssessment, ...] = ()
    dialogue_prompt: str = ''
    overall_confidence: float = 0.0
    processing_metadata: dict[str, Any] = field(default_factory=dict)
