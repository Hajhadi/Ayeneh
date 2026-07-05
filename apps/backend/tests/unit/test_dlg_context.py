"""Tests for DLG-03 Context Builder."""

from __future__ import annotations

import pytest

from ayeneh.dlg.context.compression import ContextCompressor
from ayeneh.dlg.context.engine import ContextBuilder
from ayeneh.dlg.context.types import (
    CONTEXT_LAYERS,
    CONTEXT_SELECTION_CRITERIA,
    ContextConfidence,
    ContextIdentifier,
    ContextObject,

    ConversationIdentifier,
    CurrentDialogueState,
    CurrentIntent,
    IdentityContext,
    MetaCognitiveContext,
    NarrativeContext,
    PrimaryCognitiveFocus,
    RealityContext,
    RelevantBehavioralPatterns,
    RelevantBeliefs,
    RelevantEpisodes,
    RelevantGoals,
    RelevantIdentityComponents,
    RelevantNarratives,
    RelevantPredictions,
    RelevantRealityObjects,
    RelevantSemanticMemories,
    VersionMetadata,
    WorkingMemory,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def builder() -> ContextBuilder:
    return ContextBuilder()


@pytest.fixture
def compressor() -> ContextCompressor:
    return ContextCompressor()


@pytest.fixture
def sample_memories() -> dict:
    return {
        'episode_ids': ('ep1', 'ep2'),
        'episode_summaries': ('Walked in park', 'Read a book'),
        'relevance_scores': (0.9, 0.7),
        'temporal_distances': (0.1, 0.5),
        'emotional_resonances': (0.8, 0.4),
        'semantic_ids': ('sm1',),
        'concepts': ('wellness',),
        'semantic_confidences': (0.85,),
        'source_references': ('session1',),
        'belief_ids': ('b1',),
        'belief_statements': ('Exercise is good',),
        'belief_confidences': (0.9,),
        'belief_supporting': ('e1',),
        'belief_contradicting': (),
        'narrative_ids': ('n1',),
        'narrative_summaries': ('Health journey',),
        'narrative_activations': (0.8,),
        'narrative_coherences': (0.7,),
        'goal_ids': ('g1',),
        'goal_descriptions': ('Run a marathon',),
        'goal_priorities': (0.9,),
        'goal_progress': (0.3,),
        'goal_blocked': (False,),
        'identity_ids': ('id1',),
        'identity_descriptions': ('Athlete',),
        'identity_activations': (0.8,),
        'identity_centralities': (0.7,),
        'behavioral_ids': ('bp1',),
        'behavioral_descriptions': ('Morning jog',),
        'behavioral_frequencies': (0.9,),
        'behavioral_consistencies': (0.85,),
        'behavioral_triggers': ('alarm',),
        'prediction_ids': ('pred1',),
        'prediction_statements': ('Will finish marathon',),
        'prediction_confidences': (0.6,),
        'prediction_horizons': ('6 months',),
        'reality_ids': ('r1',),
        'reality_descriptions': ('Current fitness level',),
        'reality_calibrations': (0.7,),
        'reality_evidence': (0.8,),
    }


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestContextTypes:
    def test_context_layers_count(self) -> None:
        assert len(CONTEXT_LAYERS) == 6

    def test_context_layers_values(self) -> None:
        assert 'immediate' in CONTEXT_LAYERS
        assert 'meta_cognitive' in CONTEXT_LAYERS

    def test_selection_criteria_count(self) -> None:
        assert len(CONTEXT_SELECTION_CRITERIA) == 9

    def test_selection_criteria_values(self) -> None:
        assert 'relevance' in CONTEXT_SELECTION_CRITERIA
        assert 'evidence_quality' in CONTEXT_SELECTION_CRITERIA

    def test_context_identifier_frozen(self) -> None:
        ci = ContextIdentifier(id='test-id')
        with pytest.raises(AttributeError):
            ci.id = 'other'  # type: ignore[misc]

    def test_conversation_identifier_defaults(self) -> None:
        ci = ConversationIdentifier()
        assert ci.conversation_id == ''
        assert ci.turn_number == 0

    def test_current_intent_defaults(self) -> None:
        intent = CurrentIntent()
        assert intent.intent_type == ''
        assert intent.confidence == 0.0

    def test_dialogue_state_defaults(self) -> None:
        state = CurrentDialogueState()
        assert state.phase == 'greeting'
        assert state.engagement_level == 0.5

    def test_working_memory_frozen(self) -> None:
        wm = WorkingMemory()
        with pytest.raises(AttributeError):
            wm.capacity_used = 0.9  # type: ignore[misc]

    def test_relevant_episodes_defaults(self) -> None:
        ep = RelevantEpisodes()
        assert len(ep.episode_ids) == 0

    def test_relevant_semantic_defaults(self) -> None:
        sm = RelevantSemanticMemories()
        assert len(sm.memory_ids) == 0

    def test_relevant_beliefs_defaults(self) -> None:
        b = RelevantBeliefs()
        assert len(b.belief_ids) == 0

    def test_relevant_narratives_defaults(self) -> None:
        n = RelevantNarratives()
        assert len(n.narrative_ids) == 0

    def test_relevant_goals_defaults(self) -> None:
        g = RelevantGoals()
        assert len(g.goal_ids) == 0

    def test_relevant_identity_defaults(self) -> None:
        i = RelevantIdentityComponents()
        assert len(i.component_ids) == 0

    def test_relevant_behavioral_defaults(self) -> None:
        bp = RelevantBehavioralPatterns()
        assert len(bp.pattern_ids) == 0

    def test_relevant_predictions_defaults(self) -> None:
        p = RelevantPredictions()
        assert len(p.prediction_ids) == 0

    def test_relevant_reality_defaults(self) -> None:
        r = RelevantRealityObjects()
        assert len(r.reality_ids) == 0

    def test_context_confidence_defaults(self) -> None:
        cc = ContextConfidence()
        assert cc.overall == 0.0

    def test_version_metadata_defaults(self) -> None:
        vm = VersionMetadata()
        assert vm.schema_version == '1.0.0'

    def test_context_object_frozen(self) -> None:
        co = ContextObject()
        with pytest.raises(AttributeError):
            co.context_identifier = ContextIdentifier()  # type: ignore[misc]

    def test_narrative_context_defaults(self) -> None:
        nc = NarrativeContext()
        assert nc.narrative_coherence == 0.0

    def test_identity_context_defaults(self) -> None:
        ic = IdentityContext()
        assert ic.identity_coherence == 0.0

    def test_reality_context_levels(self) -> None:
        rc = RealityContext()
        assert len(rc.level_1_facts) == 0
        assert len(rc.level_6_projections) == 0
        assert rc.calibration_confidence == 0.0

    def test_metacognitive_context_defaults(self) -> None:
        mc = MetaCognitiveContext()
        assert mc.reasoning_quality == 0.0
        assert mc.reflection_readiness == 0.0


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestContextBuilder:
    def test_build_returns_context(self, builder: ContextBuilder) -> None:
        ctx = builder.build('Hello, how are you?')
        assert isinstance(ctx, ContextObject)

    def test_build_populates_intent(self, builder: ContextBuilder) -> None:
        ctx = builder.build('How do I improve my focus?')
        assert ctx.current_intent.intent_type != ''

    def test_build_detects_information_seeking(self, builder: ContextBuilder) -> None:
        ctx = builder.build('Why does this happen?')
        assert ctx.current_intent.intent_type == 'information_seeking'

    def test_build_detects_self_expression(self, builder: ContextBuilder) -> None:
        ctx = builder.build('I feel anxious about this')
        assert ctx.current_intent.intent_type == 'self_expression'

    def test_build_detects_assistance(self, builder: ContextBuilder) -> None:
        ctx = builder.build('I need help with planning')
        assert ctx.current_intent.intent_type == 'assistance_request'

    def test_build_with_conversation_id(self, builder: ContextBuilder) -> None:
        ctx = builder.build('test', conversation_id='conv1')
        assert ctx.conversation_identifier.conversation_id == 'conv1'

    def test_build_with_user_id(self, builder: ContextBuilder) -> None:
        ctx = builder.build('test', user_id='user1')
        assert ctx.conversation_identifier.user_id == 'user1'

    def test_build_with_session_id(self, builder: ContextBuilder) -> None:
        ctx = builder.build('test', session_id='sess1')
        assert ctx.conversation_identifier.session_id == 'sess1'

    def test_build_turn_number(self, builder: ContextBuilder) -> None:
        ctx = builder.build('test', turn_number=5)
        assert ctx.conversation_identifier.turn_number == 5

    def test_build_with_memories(
        self, builder: ContextBuilder, sample_memories: dict,
    ) -> None:
        ctx = builder.build('test', available_memories=sample_memories)
        assert len(ctx.relevant_episodes.episode_ids) == 2
        assert len(ctx.relevant_semantic_memories.memory_ids) == 1
        assert len(ctx.relevant_beliefs.belief_ids) == 1

    def test_build_prior_context(self, builder: ContextBuilder) -> None:
        first = builder.build('Hello')
        second = builder.build('Tell me more', prior_context=first)
        assert second.current_dialogue_state.phase == 'continuation'
        assert second.current_dialogue_state.depth == 1

    def test_build_working_memory_entities(self, builder: ContextBuilder) -> None:
        ctx = builder.build('Alice and Bob discussed Python')
        assert len(ctx.working_memory.active_entities) > 0

    def test_build_confidence(self, builder: ContextBuilder) -> None:
        ctx = builder.build('How are you?')
        assert 0.0 <= ctx.context_confidence.overall <= 1.0

    def test_build_version_metadata(self, builder: ContextBuilder) -> None:
        ctx = builder.build('test')
        assert ctx.version_metadata.schema_version == '1.0.0'


# ---------------------------------------------------------------------------
# Compression tests
# ---------------------------------------------------------------------------


class TestContextCompressor:
    def test_compress_returns_context(self, compressor: ContextCompressor) -> None:
        ctx = ContextObject()
        compressed = compressor.compress(ctx)
        assert isinstance(compressed, ContextObject)

    def test_compress_preserves_id(
        self, compressor: ContextCompressor,
    ) -> None:
        ctx = ContextObject()
        compressed = compressor.compress(ctx)
        assert compressed.context_identifier.id == ctx.context_identifier.id

    def test_compress_truncates_entities(
        self, compressor: ContextCompressor,
    ) -> None:
        many_entities = tuple(f'entity_{i}' for i in range(30))
        wm = WorkingMemory(active_entities=many_entities)
        ctx = ContextObject(working_memory=wm)
        compressed = compressor.compress(ctx)
        assert len(compressed.working_memory.active_entities) == 20

    def test_compress_truncates_episodes(
        self, compressor: ContextCompressor,
    ) -> None:
        many_ids = tuple(f'ep_{i}' for i in range(10))
        ep = RelevantEpisodes(
            episode_ids=many_ids,
            episode_summaries=tuple(f'sum_{i}' for i in range(10)),
            relevance_scores=tuple(0.5 for _ in range(10)),
            temporal_distances=tuple(0.5 for _ in range(10)),
            emotional_resonances=tuple(0.5 for _ in range(10)),
        )
        ctx = ContextObject(relevant_episodes=ep)
        compressed = compressor.compress(ctx)
        assert len(compressed.relevant_episodes.episode_ids) == 5

    def test_estimate_tokens_empty(self, compressor: ContextCompressor) -> None:
        ctx = ContextObject()
        tokens = compressor.estimate_tokens(ctx)
        assert tokens == 0

    def test_estimate_tokens_with_data(
        self, compressor: ContextCompressor,
    ) -> None:
        wm = WorkingMemory(active_entities=('a', 'b'), recent_facts=('fact1',))
        ep = RelevantEpisodes(episode_ids=('ep1',))
        ctx = ContextObject(working_memory=wm, relevant_episodes=ep)
        tokens = compressor.estimate_tokens(ctx)
        assert tokens > 0
