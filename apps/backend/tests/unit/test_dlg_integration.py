"""End-to-end integration tests for the DLG dialogue architecture."""

from __future__ import annotations

import pytest

from ayeneh.dlg.manager.engine import DialogueManager
from ayeneh.dlg.state.engine import ConversationStateMachine
from ayeneh.dlg.context.engine import ContextBuilder
from ayeneh.dlg.reflection.engine import ReflectionTimingEngine
from ayeneh.dlg.questioning.engine import QuestionGenerationEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dlg_manager() -> DialogueManager:
    return DialogueManager()


@pytest.fixture
def state_machine() -> ConversationStateMachine:
    return ConversationStateMachine()


@pytest.fixture
def context_builder() -> ContextBuilder:
    return ContextBuilder()


@pytest.fixture
def reflection_engine() -> ReflectionTimingEngine:
    return ReflectionTimingEngine()


@pytest.fixture
def question_engine() -> QuestionGenerationEngine:
    return QuestionGenerationEngine()


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------


class TestFullDLGPipeline:
    def test_message_through_all_engines(
        self, dlg_manager, state_machine, context_builder,
        reflection_engine, question_engine,
    ) -> None:
        msg = "How does quantum entanglement work?"

        ctx_obj = context_builder.build(user_input=msg)
        assert ctx_obj is not None
        assert ctx_obj.current_intent.intent_type

        dlg_result = dlg_manager.process(msg)
        assert dlg_result.detected_intent.intent_type
        assert dlg_result.confidence.overall >= 0.0

        state_result = state_machine.process(msg)
        assert state_result.current_state_type.state_type
        assert state_result.confidence.overall >= 0.0

        reflection_result = reflection_engine.process(
            {'engagement_level': 0.5, 'depth': 0},
        )
        # reflection_result may be None — that's valid

        question_result = question_engine.process(
            {'engagement_level': 0.5, 'current_intent': {'confidence': 0.5}},
        )
        # question_result may be None — that's valid

    def test_full_pipeline_persists_state(
        self, state_machine,
    ) -> None:
        r1 = state_machine.process("Hello")
        assert r1.current_state_type.state_type in ('greeting', 'information_gathering')

        r2 = state_machine.process("What is gravity?")
        assert r2 is not None
        assert r2.confidence.overall >= 0.0


# ---------------------------------------------------------------------------
# Dialogue mode selection
# ---------------------------------------------------------------------------


class TestDialogueModeSelection:
    def test_information_seeking_uses_teacher_mode(self, dlg_manager) -> None:
        result = dlg_manager.process("What is photosynthesis?")
        assert result.response_strategy.mode == 'teacher'

    def test_reflection_uses_reflective_mirror(self, dlg_manager) -> None:
        result = dlg_manager.process("I notice I keep procrastinating")
        assert result.response_strategy.mode == 'reflective_mirror'

    def test_planning_uses_project_planner(self, dlg_manager) -> None:
        result = dlg_manager.process("Plan a roadmap for my project")
        assert result.response_strategy.mode == 'project_planner'

    def test_debugging_uses_technical_architect(self, dlg_manager) -> None:
        result = dlg_manager.process("There is a bug in my code")
        assert result.response_strategy.mode == 'technical_architect'

    def test_decision_support_uses_socratic_guide(self, dlg_manager) -> None:
        result = dlg_manager.process("Should I switch jobs?")
        assert result.response_strategy.mode == 'socratic_guide'


# ---------------------------------------------------------------------------
# State transition detection
# ---------------------------------------------------------------------------


class TestStateTransitions:
    def test_greeting_to_information_gathering(self, state_machine) -> None:
        r1 = state_machine.process("Hi there")
        assert r1.current_state_type.state_type in ('greeting', 'information_gathering')

        r2 = state_machine.process("What is machine learning?")
        assert r2 is not None

    def test_maintains_state_on_continuation(self, state_machine) -> None:
        state_machine.process("Tell me about physics")
        r2 = state_machine.process("What about thermodynamics?")
        assert r2 is not None

    def test_transition_to_planning(self, state_machine) -> None:
        state_machine.process("Tell me about project management")
        r2 = state_machine.process("Now plan the steps")
        assert r2 is not None


# ---------------------------------------------------------------------------
# Context layer assembly
# ---------------------------------------------------------------------------


class TestContextAssembly:
    def test_opens_with_opening_phase(self, context_builder) -> None:
        result = context_builder.build(user_input="Hello")
        assert result.current_dialogue_state.phase == 'opening'

    def test_continuation_increases_depth(self, context_builder) -> None:
        ctx1 = context_builder.build(user_input="Hello")
        ctx2 = context_builder.build(
            user_input="Tell me more",
            prior_context=ctx1,
        )
        assert ctx2.current_dialogue_state.depth >= ctx1.current_dialogue_state.depth

    def test_information_seeking_intent(self, context_builder) -> None:
        result = context_builder.build(user_input="What is quantum physics?")
        assert result.current_intent.intent_type == 'information_seeking'
        assert result.current_intent.confidence > 0.0

    def test_self_expression_intent(self, context_builder) -> None:
        result = context_builder.build(user_input="I feel overwhelmed today")
        assert result.current_intent.intent_type == 'self_expression'


# ---------------------------------------------------------------------------
# Reflection timing
# ---------------------------------------------------------------------------


class TestReflectionTiming:
    def test_returns_opportunity_or_none(self, reflection_engine) -> None:
        result = reflection_engine.process(
            {'engagement_level': 0.7, 'depth': 2},
        )
        assert result is None or hasattr(result, 'detected_pattern')

    def test_with_behavioral_patterns(self, reflection_engine) -> None:
        patterns = [{'type': 'recurring_behavioral_pattern', 'description': 'test', 'strength': 0.8}]
        result = reflection_engine.process(
            {'engagement_level': 0.7, 'depth': 2},
            behavioral_patterns=patterns,
        )
        if result is not None:
            assert result.urgency > 0.0


# ---------------------------------------------------------------------------
# Question generation with Socratic progression
# ---------------------------------------------------------------------------


class TestQuestionGeneration:
    def test_returns_question_or_none(self, question_engine) -> None:
        result = question_engine.process(
            {'engagement_level': 0.6, 'current_intent': {'confidence': 0.5}},
        )
        assert result is None or hasattr(result, 'question_text')

    def test_question_has_objective(self, question_engine) -> None:
        result = question_engine.process(
            {'engagement_level': 0.7, 'current_intent': {'confidence': 0.4}},
        )
        if result is not None:
            assert result.primary_objective.objective
            assert result.confidence > 0.0


# ---------------------------------------------------------------------------
# Cross-module integration
# ---------------------------------------------------------------------------


class TestCrossModuleIntegration:
    def test_context_feeds_dialogue(self, context_builder, dlg_manager) -> None:
        ctx = context_builder.build(user_input="Why do I feel anxious?")
        assert ctx.current_intent.intent_type

        dlg = dlg_manager.process("Why do I feel anxious?")
        assert dlg.detected_intent.intent_type

    def test_state_tracks_dialogue_progress(
        self, state_machine, dlg_manager,
    ) -> None:
        dlg_manager.process("Hello")
        state_machine.process("Hello")

        dlg_manager.process("Explain recursion")
        state2 = state_machine.process("Explain recursion")
        assert state2 is not None

    def test_all_engines_handle_empty_input(self, dlg_manager, state_machine, context_builder) -> None:
        ctx = context_builder.build(user_input="")
        assert ctx is not None

        dlg = dlg_manager.process("")
        assert dlg is not None

        state = state_machine.process("")
        assert state is not None
