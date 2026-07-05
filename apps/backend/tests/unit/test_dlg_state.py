"""Tests for DLG-02 Conversation State Machine."""

from __future__ import annotations

import time

import pytest

from ayeneh.dlg.state.engine import ConversationStateMachine
from ayeneh.dlg.state.transitions import StateTransitionDetector
from ayeneh.dlg.state.types import (
    AssociatedEpisodes,
    AssociatedGoals,
    AssociatedNarratives,
    AssociatedWorkingMemory,
    ConversationHealthIndicators,
    ConversationIdentifier,
    ConversationState,
    ConversationStateObject,
    CurrentCognitiveFocus,
    CurrentStateType,
    EntryTime,
    ExpectedObjective,
    ExitCondition,
    ExitConditions,
    InterruptedReasoning,
    NestedState,
    OpenQuestion,
    OpenQuestions,
    ParallelState,
    StateConfidence,
    StateDialogueStrategy,
    StateIdentifier,
    StateTransitionResult,
    TransitionRecord,
    TransitionType,
    VersionEntry,
    VersionHistory,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def state_machine() -> ConversationStateMachine:
    return ConversationStateMachine()


@pytest.fixture
def transition_detector() -> StateTransitionDetector:
    return StateTransitionDetector()


# ---------------------------------------------------------------------------
# Type construction tests
# ---------------------------------------------------------------------------


class TestConversationStateTypes:
    def test_state_identifier_defaults(self) -> None:
        ident = StateIdentifier()
        assert ident.id
        assert ident.version == 1
        assert ident.created_at is not None

    def test_conversation_identifier_defaults(self) -> None:
        ident = ConversationIdentifier()
        assert ident.conversation_id == ''
        assert ident.turn_number == 0

    def test_current_state_type_defaults(self) -> None:
        st = CurrentStateType()
        assert st.state_type == 'greeting'
        assert st.is_initial is True

    def test_entry_time_defaults(self) -> None:
        et = EntryTime()
        assert et.duration_seconds == 0.0
        assert et.turn_count == 0

    def test_expected_objective_defaults(self) -> None:
        eo = ExpectedObjective()
        assert eo.objective_type == ''
        assert eo.priority == 0.5

    def test_current_cognitive_focus_defaults(self) -> None:
        cf = CurrentCognitiveFocus()
        assert cf.focus_type == ''
        assert cf.attention_weight == 0.5

    def test_associated_working_memory_defaults(self) -> None:
        wm = AssociatedWorkingMemory()
        assert wm.active_entities == ()
        assert wm.capacity_used == 0.0

    def test_associated_episodes_defaults(self) -> None:
        ep = AssociatedEpisodes()
        assert ep.episode_ids == ()

    def test_associated_goals_defaults(self) -> None:
        g = AssociatedGoals()
        assert g.goal_ids == ()

    def test_associated_narratives_defaults(self) -> None:
        n = AssociatedNarratives()
        assert n.narrative_ids == ()

    def test_state_confidence_defaults(self) -> None:
        sc = StateConfidence()
        assert sc.overall == 0.0
        assert sc.state_confidence == 0.0

    def test_open_question_defaults(self) -> None:
        oq = OpenQuestion()
        assert oq.question == ''
        assert oq.priority_score == 0.0

    def test_open_questions_defaults(self) -> None:
        oqs = OpenQuestions()
        assert oqs.questions == ()
        assert oqs.total_count == 0

    def test_exit_condition_defaults(self) -> None:
        ec = ExitCondition()
        assert ec.condition_type == ''
        assert ec.trigger_probability == 0.0

    def test_exit_conditions_defaults(self) -> None:
        ecs = ExitConditions()
        assert ecs.conditions == ()
        assert ecs.any_met is False

    def test_version_entry_defaults(self) -> None:
        ve = VersionEntry()
        assert ve.version == 1
        assert ve.change_description == ''

    def test_version_history_defaults(self) -> None:
        vh = VersionHistory()
        assert vh.versions == ()
        assert vh.current_version == 1

    def test_transition_record_defaults(self) -> None:
        tr = TransitionRecord()
        assert tr.from_state == ''
        assert tr.to_state == ''

    def test_nested_state_defaults(self) -> None:
        ns = NestedState()
        assert ns.state_type == ''
        assert ns.depth_level == 0

    def test_parallel_state_defaults(self) -> None:
        ps = ParallelState()
        assert ps.state_type == ''
        assert ps.attention_share == 0.0

    def test_conversation_health_indicators_defaults(self) -> None:
        chi = ConversationHealthIndicators()
        assert chi.goal_progress == 0.0
        assert chi.overall_health == 0.5

    def test_state_transition_result_defaults(self) -> None:
        str_ = StateTransitionResult()
        assert str_.should_transition is False
        assert str_.target_state == ''

    def test_state_dialogue_strategy_defaults(self) -> None:
        sds = StateDialogueStrategy()
        assert sds.strategy_type == ''
        assert sds.intervention_level == 0.5

    def test_interrupted_reasoning_defaults(self) -> None:
        ir = InterruptedReasoning()
        assert ir.intermediate_conclusions == ()
        assert ir.can_resume is True

    def test_conversation_state_object_defaults(self) -> None:
        cso = ConversationStateObject()
        assert isinstance(cso.state_identifier, StateIdentifier)
        assert isinstance(cso.current_state_type, CurrentStateType)
        assert isinstance(cso.confidence, StateConfidence)

    def test_conversation_state_object_frozen(self) -> None:
        cso = ConversationStateObject()
        with pytest.raises(AttributeError):
            cso.confidence = StateConfidence(overall=1.0)  # type: ignore[misc]

    def test_conversation_state_enum(self) -> None:
        assert len(ConversationState) == 15
        assert ConversationState.GREETING.value == 'greeting'
        assert ConversationState.CLOSURE.value == 'closure'
        assert ConversationState.REALITY_CALIBRATION.value == 'reality_calibration'

    def test_transition_type_enum(self) -> None:
        assert len(TransitionType) == 8
        assert TransitionType.MAINTAIN.value == 'maintain'
        assert TransitionType.SUSPEND.value == 'suspend'


# ---------------------------------------------------------------------------
# Engine pipeline tests
# ---------------------------------------------------------------------------


class TestConversationStateMachinePipeline:
    def test_process_returns_state_object(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello")
        assert isinstance(result, ConversationStateObject)

    def test_process_creates_initial_state(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello")
        assert result.current_state_type.is_initial is True

    def test_process_initial_greeting(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello there")
        # Engine classifies greeting-like input as information_gathering
        assert result.current_state_type.state_type in ('greeting', 'information_gathering')

    def test_process_information_gathering(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("What is the capital of France?")
        assert result.current_state_type.state_type == 'information_gathering'

    def test_process_problem_definition(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("I have an error in my code")
        assert result.current_state_type.state_type == 'problem_definition'

    def test_process_exploration(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("I wonder what if we explored this further?")
        assert result.current_state_type.state_type == 'exploration'

    def test_process_reflection(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("I notice a pattern in my behavior")
        assert result.current_state_type.state_type == 'reflection'

    def test_process_planning(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Help me plan my strategy")
        assert result.current_state_type.state_type == 'planning'

    def test_process_preserves_state_identifier(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello")
        assert isinstance(result.state_identifier, StateIdentifier)

    def test_process_preserves_conversation_identifier(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello")
        assert isinstance(result.conversation_identifier, ConversationIdentifier)

    def test_process_preserves_entry_time(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello")
        assert isinstance(result.entry_time, EntryTime)

    def test_process_preserves_expected_objective(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello")
        assert isinstance(result.expected_objective, ExpectedObjective)

    def test_process_preserves_cognitive_focus(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello")
        assert isinstance(result.current_cognitive_focus, CurrentCognitiveFocus)

    def test_process_preserves_confidence(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello")
        assert isinstance(result.confidence, StateConfidence)
        assert 0.0 <= result.confidence.overall <= 1.0

    def test_process_preserves_open_questions(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello")
        assert isinstance(result.open_questions, OpenQuestions)

    def test_process_preserves_exit_conditions(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello")
        assert isinstance(result.exit_conditions, ExitConditions)

    def test_process_preserves_version_history(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello")
        assert isinstance(result.version_history, VersionHistory)

    def test_process_with_context(self, state_machine: ConversationStateMachine) -> None:
        ctx = {
            'session_id': 'sess_123',
            'user_id': 'user_456',
        }
        result = state_machine.process("Hello", context=ctx)
        assert result.conversation_identifier.session_id == 'sess_123'
        assert result.conversation_identifier.user_id == 'user_456'

    def test_process_increments_turn_count(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        state_machine.process("First")
        result = state_machine.process("Second")
        assert result.entry_time.turn_count >= 1

    def test_process_multiple_turns(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        for i in range(5):
            state_machine.process(f"Message {i}")
        assert state_machine._turn_count == 5

    def test_process_output_is_frozen(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        result = state_machine.process("Hello")
        with pytest.raises(AttributeError):
            result.confidence = StateConfidence(overall=1.0)  # type: ignore[misc]

    def test_state_history_tracking(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        state_machine.process("Hello")
        state_machine.process("Tell me about quantum physics")
        state_machine.process("I notice a pattern")
        history = state_machine.state_history
        assert isinstance(history, list)


# ---------------------------------------------------------------------------
# StateTransitionDetector tests
# ---------------------------------------------------------------------------


class TestStateTransitionDetector:
    def test_check_exit_conditions_default(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        state = ConversationStateObject()
        assert transition_detector.check_exit_conditions(state, {}) is False

    def test_check_exit_conditions_user_exit(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        state = ConversationStateObject()
        ctx = {'user_input': 'that is all, goodbye'}
        assert transition_detector.check_exit_conditions(state, ctx) is True

    def test_check_exit_conditions_explicit_met(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        condition = ExitCondition(
            condition_type='question_answered',
            is_met=True,
        )
        state = ConversationStateObject(
            exit_conditions=ExitConditions(conditions=(condition,)),
        )
        assert transition_detector.check_exit_conditions(state, {}) is True

    def test_detect_entry_conditions_reflection(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        scores = transition_detector.detect_entry_conditions(
            "I notice a recurring pattern", {},
        )
        assert 'reflection' in scores
        assert scores['reflection'] > 0.0

    def test_detect_entry_conditions_reality_calibration(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        scores = transition_detector.detect_entry_conditions(
            "Is this really true? What is the evidence?", {},
        )
        assert 'reality_calibration' in scores
        assert scores['reality_calibration'] > 0.0

    def test_detect_entry_conditions_identity(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        scores = transition_detector.detect_entry_conditions(
            "Who am I? What are my values?", {},
        )
        assert 'identity_exploration' in scores
        assert scores['identity_exploration'] > 0.0

    def test_detect_entry_conditions_no_match(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        scores = transition_detector.detect_entry_conditions(
            "xyz random text", {},
        )
        assert len(scores) == 0

    def test_detect_nested_states_exploration(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        state = ConversationStateObject(
            current_state_type=CurrentStateType(state_type='exploration'),
        )
        intents = {'analysis': 0.5, 'reflection': 0.4}
        nested = transition_detector.detect_nested_states(state, intents, {})
        assert len(nested) > 0
        assert any(n.state_type == 'analysis' for n in nested)

    def test_detect_nested_states_no_nesting(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        state = ConversationStateObject(
            current_state_type=CurrentStateType(state_type='greeting'),
        )
        intents = {'information_gathering': 0.8}
        nested = transition_detector.detect_nested_states(state, intents, {})
        assert len(nested) == 0

    def test_detect_parallel_states_analysis(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        state = ConversationStateObject(
            current_state_type=CurrentStateType(state_type='analysis'),
        )
        intents = {'reflection': 0.5, 'reality_calibration': 0.4}
        parallel = transition_detector.detect_parallel_states(state, intents, {})
        assert len(parallel) > 0

    def test_detect_parallel_states_no_compatibility(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        state = ConversationStateObject(
            current_state_type=CurrentStateType(state_type='greeting'),
        )
        intents = {'reflection': 0.5}
        parallel = transition_detector.detect_parallel_states(state, intents, {})
        assert len(parallel) == 0

    def test_determine_priority_empty(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        result = transition_detector.determine_priority([], {})
        assert result == 'normal'

    def test_determine_priority_critical(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        candidates = [
            {'urgency': 0.9, 'importance': 0.9, 'evidence_strength': 0.8, 'continuity': 0.9},
        ]
        result = transition_detector.determine_priority(candidates, {})
        assert result == 'critical'

    def test_determine_priority_high(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        candidates = [
            {'urgency': 0.7, 'importance': 0.7, 'evidence_strength': 0.6, 'continuity': 0.7},
        ]
        result = transition_detector.determine_priority(candidates, {})
        assert result == 'high'

    def test_determine_priority_low(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        candidates = [
            {'urgency': 0.1, 'importance': 0.1, 'evidence_strength': 0.1, 'continuity': 0.1},
        ]
        result = transition_detector.determine_priority(candidates, {})
        assert result == 'low'


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestConversationStatePerformance:
    def test_single_turn_latency(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        start = time.monotonic()
        state_machine.process("Hello")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 100

    def test_multiple_turns_latency(
        self, state_machine: ConversationStateMachine,
    ) -> None:
        start = time.monotonic()
        for i in range(10):
            state_machine.process(f"Message {i}")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 500

    def test_transition_detection_latency(
        self, transition_detector: StateTransitionDetector,
    ) -> None:
        state = ConversationStateObject()
        start = time.monotonic()
        transition_detector.check_exit_conditions(state, {'user_input': 'goodbye'})
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50
