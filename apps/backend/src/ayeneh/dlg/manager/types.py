"""DLG-01 Dialogue Manager types.

Defines DialogueObject, DialogueObjectives, IntentRecognition, DialogueModes,
DialogueGranularity, DialoguePlan, and supporting structures for the dialogue
management pipeline.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

class DialogueObjective(StrEnum):
    """Explicit objectives that every response shall optimize."""

    ANSWER_QUESTION = "answer_question"
    CLARIFY_AMBIGUITY = "clarify_ambiguity"
    SUPPORT_REFLECTION = "support_reflection"
    CHALLENGE_NARRATIVE = "challenge_narrative"
    CALIBRATE_REALITY = "calibrate_reality"
    SUMMARIZE_KNOWLEDGE = "summarize_knowledge"
    EXPLORE_UNCERTAINTY = "explore_uncertainty"
    GENERATE_INSIGHT = "generate_insight"
    PLAN_ACTION = "plan_action"
    ASK_DIAGNOSTIC_QUESTION = "ask_diagnostic_question"


class IntentType(StrEnum):
    """Conversational intent classifications."""

    INFORMATION_SEEKING = "information_seeking"
    REFLECTION = "reflection"
    PLANNING = "planning"
    DEBUGGING = "debugging"
    DECISION_SUPPORT = "decision_support"
    LEARNING = "learning"
    EMOTIONAL_PROCESSING = "emotional_processing"
    NARRATIVE_EXPLORATION = "narrative_exploration"
    IDENTITY_EXPLORATION = "identity_exploration"
    REALITY_CALIBRATION = "reality_calibration"
    META_COGNITIVE_OBSERVATION = "meta_cognitive_observation"


class DialogueMode(StrEnum):
    """Dialogue modes that influence communication style."""

    TEACHER = "teacher"
    RESEARCH_PARTNER = "research_partner"
    TECHNICAL_ARCHITECT = "technical_architect"
    REFLECTIVE_MIRROR = "reflective_mirror"
    SOCRATIC_GUIDE = "socratic_guide"
    PROJECT_PLANNER = "project_planner"
    ANALYTICAL_REVIEWER = "analytical_reviewer"
    REALITY_CALIBRATION_ASSISTANT = "reality_calibration_assistant"
    SILENT_OBSERVER = "silent_observer"


class DialogueGranularity(StrEnum):
    """Response granularity levels adjusted by user intent and context."""

    BRIEF = "brief"
    STRUCTURED = "structured"
    DEEP_ANALYSIS = "deep_analysis"
    LONGITUDINAL_REFLECTION = "longitudinal_reflection"
    ARCHITECTURAL_REVIEW = "architectural_review"
    SCIENTIFIC_DISCUSSION = "scientific_discussion"


# ---------------------------------------------------------------------------
# Catalogue lists
# ---------------------------------------------------------------------------

COGNITIVE_FOCUS_TYPES: list[str] = [
    'factual_recall',
    'pattern_recognition',
    'causal_reasoning',
    'counterfactual_analysis',
    'narrative_construction',
    'reality_calibration',
    'identity_exploration',
    'meta_cognitive_observation',
    'strategic_planning',
    'emotional_processing',
]

RESPONSE_STRATEGY_TYPES: list[str] = [
    'direct_answer',
    'reflective_question',
    'evidence_presentation',
    'narrative_mirror',
    'reality_check',
    'progressive_disclosure',
    'socratic_inquiry',
    'challenge_assumption',
    'silence',
    'clarification_request',
]

INFORMATION_BUDGET_LEVELS: list[str] = [
    'minimal',
    'focused',
    'moderate',
    'comprehensive',
    'exhaustive',
]

MEMORY_TYPES: list[str] = [
    'episodic',
    'semantic',
    'procedural',
    'narrative',
    'identity',
    'belief',
]

EVIDENCE_TYPES: list[str] = [
    'observed_event',
    'reported_experience',
    'behavioral_pattern',
    'narrative_consistency',
    'temporal_correlation',
    'causal_chain',
    'expert_knowledge',
    'empirical_data',
]


# ---------------------------------------------------------------------------
# Identifier value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DialogueIdentifier:
    """Unique identifier for a dialogue interaction."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1


@dataclass(frozen=True)
class ConversationIdentifier:
    """Reference to the parent conversation."""

    conversation_id: str = ''
    session_id: str = ''
    user_id: str = ''
    turn_number: int = 0


# ---------------------------------------------------------------------------
# Intent and focus
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DetectedIntent:
    """Classified intent from user input."""

    intent_type: str = ''
    confidence: float = 0.0
    description: str = ''
    parameters: dict[str, str] = field(default_factory=dict)
    secondary_intents: tuple[str, ...] = ()
    intent_evolution: tuple[str, ...] = ()


@dataclass(frozen=True)
class CurrentCognitiveFocus:
    """Primary cognitive focus for the current turn."""

    focus_type: str = ''
    target_entities: tuple[str, ...] = ()
    attention_weight: float = 0.5
    reasoning_mode: str = 'default'
    depth_level: int = 0
    cross_domain_connections: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Working memory
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActiveWorkingMemory:
    """Active working memory for the current dialogue turn."""

    active_entities: tuple[str, ...] = ()
    active_relations: tuple[str, ...] = ()
    recent_facts: tuple[str, ...] = ()
    active_goals: tuple[str, ...] = ()
    emotional_state: str = ''
    capacity_used: float = 0.0
    salient_patterns: tuple[str, ...] = ()
    pending_inferences: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Objective and strategy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrimaryObjective:
    """Primary dialogue objective for the current response."""

    objective_type: str = ''
    description: str = ''
    priority: float = 0.5
    expected_outcome: str = ''
    success_criteria: tuple[str, ...] = ()
    alternative_objectives: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResponseStrategy:
    """Selected response strategy."""

    strategy_type: str = ''
    granularity: str = 'structured'
    mode: str = 'teacher'
    information_budget: str = 'moderate'
    clarification_threshold: float = 0.3
    intervention_level: float = 0.5
    ethical_constraints: tuple[str, ...] = ()
    adaptation_factors: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Confidence and uncertainty
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Confidence:
    """Multi-dimensional confidence assessment."""

    overall: float = 0.0
    intent_confidence: float = 0.0
    evidence_confidence: float = 0.0
    strategy_confidence: float = 0.0
    reasoning_confidence: float = 0.0
    prediction_confidence: float = 0.0


@dataclass(frozen=True)
class Uncertainty:
    """Identified uncertainties in the current response."""

    identified_gaps: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    conflicting_evidence: tuple[str, ...] = ()
    confidence_intervals: dict[str, tuple[float, float]] = field(
        default_factory=dict,
    )
    ambiguity_sources: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferencedMemories:
    """Memories referenced in building the response."""

    memory_ids: tuple[str, ...] = ()
    memory_types: tuple[str, ...] = ()
    relevance_scores: tuple[float, ...] = ()
    retrieval_reasons: tuple[str, ...] = ()
    temporal_distances: tuple[float, ...] = ()
    emotional_resonances: tuple[float, ...] = ()


@dataclass(frozen=True)
class ReferencedEvidence:
    """Evidence supporting the response."""

    evidence_ids: tuple[str, ...] = ()
    evidence_types: tuple[str, ...] = ()
    strength_scores: tuple[float, ...] = ()
    source_references: tuple[str, ...] = ()
    counter_evidence: tuple[str, ...] = ()
    evidence_quality_notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Follow-up
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FollowUpOpportunity:
    """A potential follow-up question or direction."""

    description: str = ''
    cognitive_purpose: str = ''
    priority_score: float = 0.0
    target_state: str = ''
    prerequisites: tuple[str, ...] = ()
    expected_benefit: str = ''


@dataclass(frozen=True)
class FollowUpOpportunities:
    """Collection of follow-up opportunities."""

    opportunities: tuple[FollowUpOpportunity, ...] = ()
    overall_priority: float = 0.0
    recommended_next: str = ''


# ---------------------------------------------------------------------------
# Version metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VersionMetadata:
    """Version tracking metadata."""

    schema_version: str = '1.0.0'
    engine_version: str = '1.0.0'
    build_number: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    specification_id: str = 'DLG-01'


# ---------------------------------------------------------------------------
# Dialogue Plan
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DialoguePlan:
    """Explicit dialogue plan constructed before response generation."""

    primary_objective: str = ''
    secondary_objectives: tuple[str, ...] = ()
    required_memories: tuple[str, ...] = ()
    required_reasoning: tuple[str, ...] = ()
    required_evidence: tuple[str, ...] = ()
    expected_user_benefit: str = ''
    potential_misunderstandings: tuple[str, ...] = ()
    follow_up_opportunities: tuple[str, ...] = ()
    cognitive_load_estimate: float = 0.0
    estimated_response_length: str = 'moderate'
    ethical_review_notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DialogueResponse:
    """Constructed response before self-evaluation."""

    content: str = ''
    response_type: str = 'text'
    granularity: str = 'structured'
    emotional_tone: str = 'neutral'
    explicit_uncertainty_markers: tuple[str, ...] = ()
    evidence_citations: tuple[str, ...] = ()
    questions_raised: tuple[str, ...] = ()
    action_suggestions: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Self-evaluation result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvaluationResult:
    """Result of self-evaluation on a response."""

    overall_quality: float = 0.0
    accuracy: float = 0.0
    evidence_support: float = 0.0
    explainability: float = 0.0
    relevance: float = 0.0
    cognitive_usefulness: float = 0.0
    uncertainty_communication: float = 0.0
    narrative_neutrality: float = 0.0
    passes_threshold: bool = True
    revision_needed: bool = False
    revision_notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Core type: DialogueObject
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DialogueObject:
    """Complete dialogue object produced by the Dialogue Manager pipeline.

    Every dialogue interaction shall preserve all fields listed in DLG-01 §4.
    """

    dialogue_identifier: DialogueIdentifier = field(
        default_factory=DialogueIdentifier,
    )
    conversation_identifier: ConversationIdentifier = field(
        default_factory=ConversationIdentifier,
    )
    detected_intent: DetectedIntent = field(default_factory=DetectedIntent)
    current_cognitive_focus: CurrentCognitiveFocus = field(
        default_factory=CurrentCognitiveFocus,
    )
    active_working_memory: ActiveWorkingMemory = field(
        default_factory=ActiveWorkingMemory,
    )
    primary_objective: PrimaryObjective = field(
        default_factory=PrimaryObjective,
    )
    response_strategy: ResponseStrategy = field(
        default_factory=ResponseStrategy,
    )
    confidence: Confidence = field(default_factory=Confidence)
    uncertainty: Uncertainty = field(default_factory=Uncertainty)
    referenced_memories: ReferencedMemories = field(
        default_factory=ReferencedMemories,
    )
    referenced_evidence: ReferencedEvidence = field(
        default_factory=ReferencedEvidence,
    )
    follow_up_opportunities: FollowUpOpportunities = field(
        default_factory=FollowUpOpportunities,
    )
    version_metadata: VersionMetadata = field(default_factory=VersionMetadata)
