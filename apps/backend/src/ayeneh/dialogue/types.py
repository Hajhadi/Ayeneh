"""Dialogue types — core domain objects for contemplative dialogue decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DialogueIntervention(StrEnum):
    """Types of intervention the dialogue engine can select.

    These are interventions, NOT responses. They determine
    what kind of move the system makes.
    """

    REFLECTIVE_QUESTION = "reflective_question"
    CLARIFICATION = "clarification"
    REFRAMING = "reframing"
    PERSPECTIVE_EXPANSION = "perspective_expansion"
    OBSERVATION_MIRROR = "observation_mirror"
    PATTERN_REFLECTION = "pattern_reflection"
    EVIDENCE_PRESENTATION = "evidence_presentation"
    KNOWLEDGE_EXPLANATION = "knowledge_explanation"
    MULTIPLE_FRAMEWORK_COMPARISON = "multiple_framework_comparison"
    GOAL_REMINDER = "goal_reminder"
    SUMMARY = "summary"
    SILENCE = "silence"
    UNCERTAINTY_STATEMENT = "uncertainty_statement"
    CHALLENGE_ASSUMPTION = "challenge_assumption"
    OPEN_EXPLORATION = "open_exploration"
    NO_INTERVENTION = "no_intervention"


class DialogueState(StrEnum):
    """Conversation stage."""

    OPENING = "opening"
    EXPLORING = "exploring"
    DEEPENING = "deepening"
    REFLECTING = "reflecting"
    INTEGRATING = "integrating"
    CLOSING = "closing"


class DialogueNeed(StrEnum):
    """Detected user needs."""

    CERTAINTY = "certainty"
    EXPLORATION = "exploration"
    CLARIFICATION = "clarification"
    REFLECTION = "reflection"
    ACTION = "action"
    KNOWLEDGE = "knowledge"
    SILENCE = "silence"
    CHALLENGE = "challenge"
    VALIDATION = "validation"
    SUPPORT = "support"


class DialogueSignal(StrEnum):
    """Signals detected in user input."""

    EMOTIONAL_PRESSURE = "emotional_pressure"
    DEPENDENCY_SEEKING = "dependency_seeking"
    RUMINATION = "rumination"
    CONFIRMATION_SEEKING = "confirmation_seeking"
    URGENCY = "urgency"
    AVOIDANCE = "avoidance"
    AWARENESS = "awareness"
    CURIOSITY = "curiosity"
    RESISTANCE = "resistance"
    OPENNESS = "openness"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DialogueNeedResult:
    """A detected need with confidence."""

    need: DialogueNeed
    confidence: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class DialogueSignalResult:
    """A detected signal with confidence."""

    signal: DialogueSignal
    confidence: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class DialogueAnalysis:
    """Complete analysis of the dialogue state.

    This is produced by the DialogueIntentionEngine
    and consumed by all downstream systems.
    """

    # Conversation metadata
    message_count: int = 0
    conversation_stage: DialogueState = DialogueState.OPENING

    # Intentions
    user_intention: str = ""
    intention_confidence: float = 0.5

    # Detected needs (sorted by confidence)
    detected_needs: list[DialogueNeedResult] = field(default_factory=list)

    # Detected signals
    detected_signals: list[DialogueSignalResult] = field(default_factory=list)

    # Emotional state
    emotional_pressure: float = 0.0
    urgency: float = 0.0
    ambiguity: float = 0.5

    # Dependency indicators
    dependency_risk: float = 0.0
    seeking_certainty: bool = False
    outsourcing_decisions: bool = False
    reassurance_seeking: bool = False

    # Avoidance indicators
    avoidance_indicators: list[str] = field(default_factory=list)

    # Rumination indicators
    rumination_indicators: list[str] = field(default_factory=list)

    # Confirmation seeking
    confirmation_seeking: bool = False

    # Confidence
    confidence: float = 0.5

    # Explanation
    reasoning: list[str] = field(default_factory=list)


@dataclass
class DialogueReasoning:
    """Structured reasoning for the dialogue decision."""

    why_selected: list[str] = field(default_factory=list)
    why_rejected: dict[str, list[str]] = field(default_factory=dict)
    dependency_considerations: list[str] = field(default_factory=list)
    policy_considerations: list[str] = field(default_factory=list)


@dataclass
class DialogueDecision:
    """Complete decision from the dialogue engine.

    This flows through Retrieval → Reasoning → PromptComposer → LLM.
    """

    # Selected intervention
    selected_intervention: DialogueIntervention = DialogueIntervention.NO_INTERVENTION

    # Alternatives considered
    alternative_interventions: list[DialogueIntervention] = field(default_factory=list)

    # Reasoning
    reasoning: DialogueReasoning = field(default_factory=DialogueReasoning)

    # Risk assessments
    dependency_risk: float = 0.0
    epistemic_risk: float = 0.0

    # Confidence
    confidence: float = 0.5

    # Expected outcome
    expected_outcome: str = ""

    # Analysis used
    analysis: DialogueAnalysis = field(default_factory=DialogueAnalysis)


@dataclass
class DialogueMetadata:
    """Metadata about the dialogue decision for observability."""

    decision_latency_ms: float = 0.0
    policies_applied: list[str] = field(default_factory=list)
    intervention_distribution: dict[str, int] = field(default_factory=dict)
    dependency_risk_history: list[float] = field(default_factory=list)
    confidence_history: list[float] = field(default_factory=list)
