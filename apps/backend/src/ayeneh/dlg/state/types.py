"""DLG-02 Conversation State Machine types.

Defines ConversationStateObject, PrimaryConversationStates, and supporting
structures for conversation state management.

Specification: DLG-02 Conversation State Machine.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

class ConversationState(StrEnum):
    """Primary conversation states.

    The state taxonomy remains extensible.
    """

    GREETING = "greeting"
    INFORMATION_GATHERING = "information_gathering"
    PROBLEM_DEFINITION = "problem_definition"
    EXPLORATION = "exploration"
    REFLECTION = "reflection"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    DECISION_SUPPORT = "decision_support"
    REALITY_CALIBRATION = "reality_calibration"
    NARRATIVE_INVESTIGATION = "narrative_investigation"
    IDENTITY_EXPLORATION = "identity_exploration"
    META_COGNITIVE_REFLECTION = "meta_cognitive_reflection"
    PROJECT_DESIGN = "project_design"
    REVIEW = "review"
    CLOSURE = "closure"


class TransitionType(StrEnum):
    """Types of state transitions."""

    MAINTAIN = "maintain"
    DEEPEN = "deepen"
    TRANSITION = "transition"
    RESOLVE = "resolve"
    SUSPEND = "suspend"
    RESUME = "resume"
    NEST = "nest"
    PARALLEL = "parallel"


class StatePriority(StrEnum):
    """Priority levels for competing states."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


# ---------------------------------------------------------------------------
# Catalogue lists
# ---------------------------------------------------------------------------

EXIT_CONDITION_TYPES: list[str] = [
    'question_answered',
    'problem_resolved',
    'new_uncertainty_introduced',
    'goal_achieved',
    'context_shifted',
    'dialogue_redirected',
    'user_initiated_exit',
    'timeout',
    'natural_conclusion',
]

STATE_PERSISTENCE_TYPES: list[str] = [
    'ephemeral',
    'session_scoped',
    'cross_session',
    'long_term',
    'persistent',
]

CONVERSATION_HEALTH_INDICATORS: list[str] = [
    'goal_progress',
    'topic_coherence',
    'reasoning_continuity',
    'cognitive_overload',
    'unresolved_ambiguity',
    'engagement_level',
    'emotional_safety',
]

MILESTONE_TYPES: list[str] = [
    'major_insight',
    'important_decision',
    'architecture_completion',
    'narrative_revision',
    'reality_calibration_breakthrough',
    'identity_transition',
    'pattern_recognition',
    'breakthrough_moment',
]


# ---------------------------------------------------------------------------
# Identifier value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateIdentifier:
    """Unique identifier for a conversation state."""

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
# State type and entry time
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CurrentStateType:
    """Current conversation state classification."""

    state_type: str = 'greeting'
    state_name: str = ''
    description: str = ''
    persistence_type: str = 'session_scoped'
    is_initial: bool = True
    depth_level: int = 0


@dataclass(frozen=True)
class EntryTime:
    """When the current state was entered."""

    entry_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    duration_seconds: float = 0.0
    turn_count: int = 0
    expected_duration_seconds: float = 0.0
    is_overdue: bool = False


# ---------------------------------------------------------------------------
# Objective and focus
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExpectedObjective:
    """Expected objective for the current state."""

    objective_type: str = ''
    description: str = ''
    priority: float = 0.5
    expected_outcome: str = ''
    success_criteria: tuple[str, ...] = ()
    progress: float = 0.0


@dataclass(frozen=True)
class CurrentCognitiveFocus:
    """Cognitive focus of the current state."""

    focus_type: str = ''
    target_entities: tuple[str, ...] = ()
    attention_weight: float = 0.5
    reasoning_mode: str = 'default'
    depth_level: int = 0
    domain: str = ''


# ---------------------------------------------------------------------------
# Working memory and associations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssociatedWorkingMemory:
    """Working memory associated with the current state."""

    active_entities: tuple[str, ...] = ()
    active_relations: tuple[str, ...] = ()
    recent_facts: tuple[str, ...] = ()
    active_goals: tuple[str, ...] = ()
    emotional_state: str = ''
    capacity_used: float = 0.0
    pending_inferences: tuple[str, ...] = ()
    intermediate_conclusions: tuple[str, ...] = ()


@dataclass(frozen=True)
class AssociatedEpisodes:
    """Episodes associated with the current state."""

    episode_ids: tuple[str, ...] = ()
    episode_summaries: tuple[str, ...] = ()
    relevance_scores: tuple[float, ...] = ()
    temporal_distances: tuple[float, ...] = ()
    emotional_resonances: tuple[float, ...] = ()


@dataclass(frozen=True)
class AssociatedGoals:
    """Goals associated with the current state."""

    goal_ids: tuple[str, ...] = ()
    goal_descriptions: tuple[str, ...] = ()
    priority_levels: tuple[float, ...] = ()
    progress_levels: tuple[float, ...] = ()
    blocked: tuple[bool, ...] = ()


@dataclass(frozen=True)
class AssociatedNarratives:
    """Narratives associated with the current state."""

    narrative_ids: tuple[str, ...] = ()
    narrative_summaries: tuple[str, ...] = ()
    activation_levels: tuple[float, ...] = ()
    coherence_scores: tuple[float, ...] = ()
    tension_levels: tuple[float, ...] = ()


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateConfidence:
    """Multi-dimensional confidence for the current state."""

    overall: float = 0.0
    state_confidence: float = 0.0
    transition_confidence: float = 0.0
    prediction_confidence: float = 0.0
    evidence_confidence: float = 0.0


# ---------------------------------------------------------------------------
# Open questions and exit conditions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OpenQuestion:
    """An unresolved question within the current state."""

    question: str = ''
    priority_score: float = 0.0
    associated_topic: str = ''
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    answer_progress: float = 0.0


@dataclass(frozen=True)
class OpenQuestions:
    """Collection of open questions."""

    questions: tuple[OpenQuestion, ...] = ()
    total_count: int = 0
    high_priority_count: int = 0


@dataclass(frozen=True)
class ExitCondition:
    """A condition that triggers state exit."""

    condition_type: str = ''
    description: str = ''
    trigger_probability: float = 0.0
    expected_next_state: str = ''
    prerequisites: tuple[str, ...] = ()
    is_met: bool = False


@dataclass(frozen=True)
class ExitConditions:
    """Collection of exit conditions for the current state."""

    conditions: tuple[ExitCondition, ...] = ()
    any_met: bool = False
    earliest_exit_turn: int = 0


# ---------------------------------------------------------------------------
# Version history
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VersionEntry:
    """A single version history entry."""

    version: int = 1
    change_description: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    state_snapshot: str = ''


@dataclass(frozen=True)
class VersionHistory:
    """Version tracking for state evolution."""

    versions: tuple[VersionEntry, ...] = ()
    current_version: int = 1
    total_changes: int = 0


# ---------------------------------------------------------------------------
# Transition record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransitionRecord:
    """Record of a state transition."""

    from_state: str = ''
    to_state: str = ''
    transition_type: str = 'transition'
    trigger_reason: str = ''
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    turn_number: int = 0


# ---------------------------------------------------------------------------
# Nested and parallel state support
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NestedState:
    """A nested sub-state within the current state."""

    state_type: str = ''
    state_name: str = ''
    depth_level: int = 0
    entry_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    objective: str = ''
    is_active: bool = True


@dataclass(frozen=True)
class ParallelState:
    """A parallel state active alongside the primary state."""

    state_type: str = ''
    state_name: str = ''
    priority: str = 'normal'
    attention_share: float = 0.0
    is_primary: bool = False
    entry_time: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Conversation health
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConversationHealthIndicators:
    """Health indicators for the current conversation."""

    goal_progress: float = 0.0
    topic_coherence: float = 0.0
    reasoning_continuity: float = 0.0
    cognitive_overload: float = 0.0
    unresolved_ambiguity: float = 0.0
    engagement_level: float = 0.5
    emotional_safety: float = 0.5
    overall_health: float = 0.5


# ---------------------------------------------------------------------------
# Conversational milestone
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConversationalMilestone:
    """A significant event in the conversation."""

    milestone_type: str = ''
    description: str = ''
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    turn_number: int = 0
    confidence: float = 0.0
    is_retrieval_anchor: bool = True


# ---------------------------------------------------------------------------
# Interrupted reasoning
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InterruptedReasoning:
    """Preserved state of an interrupted reasoning chain."""

    intermediate_conclusions: tuple[str, ...] = ()
    unresolved_hypotheses: tuple[str, ...] = ()
    pending_evidence: tuple[str, ...] = ()
    current_uncertainty: str = ''
    interruption_point: str = ''
    can_resume: bool = True


# ---------------------------------------------------------------------------
# Core type: ConversationStateObject
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConversationStateObject:
    """Complete conversation state object produced by the state machine.

    Every active state shall preserve all fields listed in DLG-02 §4.
    """

    state_identifier: StateIdentifier = field(default_factory=StateIdentifier)
    conversation_identifier: ConversationIdentifier = field(
        default_factory=ConversationIdentifier,
    )
    current_state_type: CurrentStateType = field(default_factory=CurrentStateType)
    entry_time: EntryTime = field(default_factory=EntryTime)
    expected_objective: ExpectedObjective = field(default_factory=ExpectedObjective)
    current_cognitive_focus: CurrentCognitiveFocus = field(
        default_factory=CurrentCognitiveFocus,
    )
    associated_working_memory: AssociatedWorkingMemory = field(
        default_factory=AssociatedWorkingMemory,
    )
    associated_episodes: AssociatedEpisodes = field(
        default_factory=AssociatedEpisodes,
    )
    associated_goals: AssociatedGoals = field(default_factory=AssociatedGoals)
    associated_narratives: AssociatedNarratives = field(
        default_factory=AssociatedNarratives,
    )
    confidence: StateConfidence = field(default_factory=StateConfidence)
    open_questions: OpenQuestions = field(default_factory=OpenQuestions)
    exit_conditions: ExitConditions = field(default_factory=ExitConditions)
    version_history: VersionHistory = field(default_factory=VersionHistory)


# ---------------------------------------------------------------------------
# State transition result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateTransitionResult:
    """Result of transition detection."""

    should_transition: bool = False
    target_state: str = ''
    transition_type: str = 'transition'
    confidence: float = 0.0
    reason: str = ''
    nested_states: tuple[NestedState, ...] = ()
    parallel_states: tuple[ParallelState, ...] = ()
    suspended_states: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Dialogue strategy for state
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateDialogueStrategy:
    """Dialogue strategy selected for the current state."""

    strategy_type: str = ''
    response_style: str = ''
    intervention_level: float = 0.5
    question_generation: bool = False
    reflection_timing: str = 'opportunistic'
    adaptation_notes: tuple[str, ...] = ()
