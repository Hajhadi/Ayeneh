"""DLG-03 Context Builder types.

Defines ContextObject, ContextLayers, ContextSelectionCriteria,
and ContextSubModels for the dialogue context pipeline.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


# ---------------------------------------------------------------------------
# Catalogue enumerations
# ---------------------------------------------------------------------------

CONTEXT_LAYERS: list[str] = [
    'immediate',
    'conversation',
    'episode',
    'project',
    'identity',
    'meta_cognitive',
]

CONTEXT_SELECTION_CRITERIA: list[str] = [
    'relevance',
    'importance',
    'confidence',
    'current_objective',
    'identity_significance',
    'behavioral_significance',
    'graph_centrality',
    'temporal_proximity',
    'evidence_quality',
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextIdentifier:
    """Unique identifier for a context object."""

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


@dataclass(frozen=True)
class CurrentIntent:
    """Detected intent from the user's input."""

    intent_type: str = ''
    confidence: float = 0.0
    description: str = ''
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CurrentDialogueState:
    """Current state of the dialogue flow."""

    phase: str = 'greeting'
    topic: str = ''
    depth: int = 0
    emotional_valence: float = 0.0
    engagement_level: float = 0.5
    pending_questions: tuple[str, ...] = ()
    unresolved_topics: tuple[str, ...] = ()


@dataclass(frozen=True)
class PrimaryCognitiveFocus:
    """Primary cognitive focus for the current turn."""

    focus_type: str = ''
    target_entities: tuple[str, ...] = ()
    attention_weight: float = 0.5
    reasoning_mode: str = 'default'


@dataclass(frozen=True)
class WorkingMemory:
    """Active working memory for the current conversation turn."""

    active_entities: tuple[str, ...] = ()
    active_relations: tuple[str, ...] = ()
    recent_facts: tuple[str, ...] = ()
    active_goals: tuple[str, ...] = ()
    emotional_state: str = ''
    capacity_used: float = 0.0


@dataclass(frozen=True)
class RelevantEpisodes:
    """Episodes recalled from episodic memory."""

    episode_ids: tuple[str, ...] = ()
    episode_summaries: tuple[str, ...] = ()
    relevance_scores: tuple[float, ...] = ()
    temporal_distances: tuple[float, ...] = ()
    emotional_resonances: tuple[float, ...] = ()


@dataclass(frozen=True)
class RelevantSemanticMemories:
    """Semantic memories recalled for context."""

    memory_ids: tuple[str, ...] = ()
    concepts: tuple[str, ...] = ()
    confidence_scores: tuple[float, ...] = ()
    source_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelevantBeliefs:
    """Beliefs relevant to the current context."""

    belief_ids: tuple[str, ...] = ()
    belief_statements: tuple[str, ...] = ()
    confidence_levels: tuple[float, ...] = ()
    supporting_evidence: tuple[str, ...] = ()
    contradicting_evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelevantNarratives:
    """Active narratives in the user's cognitive landscape."""

    narrative_ids: tuple[str, ...] = ()
    narrative_summaries: tuple[str, ...] = ()
    activation_levels: tuple[float, ...] = ()
    coherence_scores: tuple[float, ...] = ()


@dataclass(frozen=True)
class RelevantGoals:
    """Goals relevant to the current dialogue."""

    goal_ids: tuple[str, ...] = ()
    goal_descriptions: tuple[str, ...] = ()
    priority_levels: tuple[float, ...] = ()
    progress_levels: tuple[float, ...] = ()
    blocked: tuple[bool, ...] = ()


@dataclass(frozen=True)
class RelevantIdentityComponents:
    """Identity aspects activated in this context."""

    component_ids: tuple[str, ...] = ()
    component_descriptions: tuple[str, ...] = ()
    activation_levels: tuple[float, ...] = ()
    centrality_scores: tuple[float, ...] = ()


@dataclass(frozen=True)
class RelevantBehavioralPatterns:
    """Behavioral patterns observed in this context domain."""

    pattern_ids: tuple[str, ...] = ()
    pattern_descriptions: tuple[str, ...] = ()
    frequency_scores: tuple[float, ...] = ()
    consistency_scores: tuple[float, ...] = ()
    trigger_conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelevantPredictions:
    """Predictions relevant to the current situation."""

    prediction_ids: tuple[str, ...] = ()
    prediction_statements: tuple[str, ...] = ()
    confidence_levels: tuple[float, ...] = ()
    time_horizons: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelevantRealityObjects:
    """Reality-check objects relevant to the context."""

    reality_ids: tuple[str, ...] = ()
    descriptions: tuple[str, ...] = ()
    calibration_scores: tuple[float, ...] = ()
    evidence_strength: tuple[float, ...] = ()


@dataclass(frozen=True)
class ContextConfidence:
    """Multi-dimensional confidence assessment for the context."""

    completeness: float = 0.0
    relevance: float = 0.0
    recency: float = 0.0
    coherence: float = 0.0
    overall: float = 0.0


@dataclass(frozen=True)
class VersionMetadata:
    """Version tracking metadata for the context object."""

    schema_version: str = '1.0.0'
    engine_version: str = '1.0.0'
    build_number: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Core type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContextObject:
    """Complete context object built by the context builder pipeline (DLG-03)."""

    context_identifier: ContextIdentifier = field(default_factory=ContextIdentifier)
    conversation_identifier: ConversationIdentifier = field(
        default_factory=ConversationIdentifier,
    )
    current_intent: CurrentIntent = field(default_factory=CurrentIntent)
    current_dialogue_state: CurrentDialogueState = field(
        default_factory=CurrentDialogueState,
    )
    primary_cognitive_focus: PrimaryCognitiveFocus = field(
        default_factory=PrimaryCognitiveFocus,
    )
    working_memory: WorkingMemory = field(default_factory=WorkingMemory)
    relevant_episodes: RelevantEpisodes = field(default_factory=RelevantEpisodes)
    relevant_semantic_memories: RelevantSemanticMemories = field(
        default_factory=RelevantSemanticMemories,
    )
    relevant_beliefs: RelevantBeliefs = field(default_factory=RelevantBeliefs)
    relevant_narratives: RelevantNarratives = field(default_factory=RelevantNarratives)
    relevant_goals: RelevantGoals = field(default_factory=RelevantGoals)
    relevant_identity_components: RelevantIdentityComponents = field(
        default_factory=RelevantIdentityComponents,
    )
    relevant_behavioral_patterns: RelevantBehavioralPatterns = field(
        default_factory=RelevantBehavioralPatterns,
    )
    relevant_predictions: RelevantPredictions = field(
        default_factory=RelevantPredictions,
    )
    relevant_reality_objects: RelevantRealityObjects = field(
        default_factory=RelevantRealityObjects,
    )
    context_confidence: ContextConfidence = field(default_factory=ContextConfidence)
    version_metadata: VersionMetadata = field(default_factory=VersionMetadata)


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NarrativeContext:
    """Narrative-specific context sub-model."""

    active_narratives: tuple[str, ...] = ()
    narrative_coherence: float = 0.0
    narrative_tension: float = 0.0
    turning_points: tuple[str, ...] = ()
    unresolved_threads: tuple[str, ...] = ()
    character_arcs: tuple[str, ...] = ()
    themes: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdentityContext:
    """Identity-specific context sub-model."""

    activated_roles: tuple[str, ...] = ()
    identity_conflicts: tuple[str, ...] = ()
    role_pressures: tuple[str, ...] = ()
    aspirational_identities: tuple[str, ...] = ()
    threatened_identities: tuple[str, ...] = ()
    identity_coherence: float = 0.0


@dataclass(frozen=True)
class RealityContext:
    """Reality-calibration context sub-model (6 levels)."""

    level_1_facts: tuple[str, ...] = ()
    level_2_observations: tuple[str, ...] = ()
    level_3_interpretations: tuple[str, ...] = ()
    level_4_assumptions: tuple[str, ...] = ()
    level_5_narratives: tuple[str, ...] = ()
    level_6_projections: tuple[str, ...] = ()
    calibration_confidence: float = 0.0
    distortion_indicators: tuple[str, ...] = ()


@dataclass(frozen=True)
class MetaCognitiveContext:
    """Meta-cognitive awareness context."""

    thinking_patterns: tuple[str, ...] = ()
    cognitive_biases_detected: tuple[str, ...] = ()
    reasoning_quality: float = 0.0
    self_awareness_level: float = 0.0
    metacognitive_insights: tuple[str, ...] = ()
    blind_spots: tuple[str, ...] = ()
    reflection_readiness: float = 0.0
