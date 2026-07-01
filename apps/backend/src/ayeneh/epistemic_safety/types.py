"""Epistemic Safety types — core domain objects for epistemic validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class StatementClassification(StrEnum):
    """Classification of statement types."""

    OBSERVATION = "observation"
    INTERPRETATION = "interpretation"
    HYPOTHESIS = "hypothesis"
    INFERENCE = "inference"
    ADVICE = "advice"
    QUESTION = "question"
    UNKNOWN = "unknown"


class EvidenceStatus(StrEnum):
    """Status of evidence supporting a claim."""

    SUPPORTED = "supported"
    SUPPORTED_INDIRECTLY = "supported_indirectly"
    SPECULATIVE = "speculative"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"


class FrameworkAttribution(StrEnum):
    """Framework attribution for claims."""

    NEUROSCIENCE = "neuroscience"
    ACT = "act"
    ANALYTICAL_PHILOSOPHY = "analytical_philosophy"
    ZEN = "zen"
    KHORASAN_MYSTICISM = "khorasan_mysticism"
    HISTORICAL_SOURCE = "historical_source"
    COMPARATIVE_INTERPRETATION = "comparative_interpretation"
    UNKNOWN = "unknown"


class UncertaintyLevel(StrEnum):
    """Levels of uncertainty."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class DependencyRisk(StrEnum):
    """Risk levels for dependency creation."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AuthorityRisk(StrEnum):
    """Risk levels for unauthorized authority claims."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SafetyRecommendation(str):
    """Recommendations for response safety."""

    PASS = "PASS"
    REVISE = "REVISE"
    BLOCK = "BLOCK"


# ---------------------------------------------------------------------------
# Validation Results
# ---------------------------------------------------------------------------


@dataclass
class StatementValidation:
    """Validation result for a single statement."""

    text: str = ""
    classification: str = StatementClassification.UNKNOWN
    evidence_status: str = EvidenceStatus.UNSUPPORTED
    framework: str = FrameworkAttribution.UNKNOWN
    scope_valid: bool = True
    scope_violation_reason: str = ""
    uncertainty_level: str = UncertaintyLevel.MEDIUM


@dataclass
class DependencyCheck:
    """Result of dependency risk check."""

    detected: bool = False
    risk_level: str = DependencyRisk.NONE
    patterns_found: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class AuthorityCheck:
    """Result of authority safety check."""

    detected: bool = False
    risk_level: str = AuthorityRisk.NONE
    violations: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class Revision:
    """A revision made to the response."""

    original: str = ""
    revised: str = ""
    reason: str = ""
    revision_type: str = ""  # "hedging" | "dependency" | "authority" | "scope"


# ---------------------------------------------------------------------------
# Safety Provenance
# ---------------------------------------------------------------------------


@dataclass
class SafetyProvenance:
    """Traceable origin for every safety intervention.

    Every automatic revision must record what changed, why it changed,
    and which safety rule triggered it.
    """

    rule_id: str = ""
    rule_name: str = ""
    reason: str = ""
    before_text: str = ""
    after_text: str = ""
    affected_statement: str = ""
    validation_stage: str = ""
    timestamp: str = ""
    confidence: float = 1.0
    severity: str = "low"  # "low" | "medium" | "high" | "critical"
    is_automatic: bool = True


# ---------------------------------------------------------------------------
# Epistemic Safety Policy
# ---------------------------------------------------------------------------


@dataclass
class EpistemicSafetyPolicy:
    """Product-specific safety policy.

    Each ProductProfile owns its own policy.
    No hardcoded behavior.
    """

    # Policy identity
    policy_id: str = ""
    product_id: str = ""

    # Thresholds
    dependency_threshold: str = DependencyRisk.MEDIUM
    authority_threshold: str = AuthorityRisk.MEDIUM
    uncertainty_disclosure_threshold: str = UncertaintyLevel.MEDIUM

    # Behavior flags
    allow_recommendations: bool = False
    allow_strong_conclusions: bool = False
    require_evidence_citations: bool = True
    require_uncertainty_disclosure: bool = True
    require_framework_attribution: bool = True
    require_scope_validation: bool = True
    prefer_reflective_dialogue: bool = True
    minimal_advice: bool = True

    # Intervention thresholds
    intervention_threshold: float = 0.7
    block_threshold: float = 0.3

    # Revision rules
    auto_revise_hedging: bool = True
    auto_revise_dependency: bool = True
    auto_revise_authority: bool = True
    auto_revise_scope: bool = True


# ---------------------------------------------------------------------------
# Safety Result
# ---------------------------------------------------------------------------


@dataclass
class EpistemicSafetyResult:
    """Complete result of epistemic safety validation."""

    # Overall assessment
    overall_safety_score: float = 1.0
    recommendation: str = SafetyRecommendation.PASS

    # Statement analysis
    statement_count: int = 0
    observation_count: int = 0
    interpretation_count: int = 0
    hypothesis_count: int = 0
    unsupported_claims: int = 0

    # Validation details
    scope_violations: list[str] = field(default_factory=list)
    framework_violations: list[str] = field(default_factory=list)
    unsupported_claim_texts: list[str] = field(default_factory=list)

    # Risk assessments
    dependency_risk: str = DependencyRisk.NONE
    dependency_check: DependencyCheck | None = None
    authority_risk: str = AuthorityRisk.NONE
    authority_check: AuthorityCheck | None = None

    # Uncertainty
    uncertainty_level: str = UncertaintyLevel.MEDIUM

    # Revisions
    revisions_performed: list[Revision] = field(default_factory=list)
    revised_response: str = ""

    # Provenance (traceable interventions)
    provenance: list[SafetyProvenance] = field(default_factory=list)
    revision_history: list[Revision] = field(default_factory=list)
    triggered_rules: list[str] = field(default_factory=list)
    blocked_rules: list[str] = field(default_factory=list)

    # Metadata
    validation_duration_ms: float = 0.0
    stages_completed: list[str] = field(default_factory=list)
    policy_applied: str = ""
