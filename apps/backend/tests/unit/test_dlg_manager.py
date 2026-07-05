"""Tests for DLG-01 Dialogue Manager."""

from __future__ import annotations

import time

import pytest

from ayeneh.dlg.manager.engine import DialogueManager
from ayeneh.dlg.manager.evaluation import SelfEvaluator
from ayeneh.dlg.manager.types import (
    ActiveWorkingMemory,
    Confidence,
    ConversationIdentifier,
    CurrentCognitiveFocus,
    DetectedIntent,
    DialogueGranularity,
    DialogueIdentifier,
    DialogueMode,
    DialogueObjective,
    DialogueObject,
    DialoguePlan,
    DialogueResponse,
    EvaluationResult,
    FollowUpOpportunity,
    FollowUpOpportunities,
    PrimaryObjective,
    ReferencedEvidence,
    ReferencedMemories,
    ResponseStrategy,
    Uncertainty,
    VersionMetadata,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager() -> DialogueManager:
    return DialogueManager()


@pytest.fixture
def evaluator() -> SelfEvaluator:
    return SelfEvaluator()


# ---------------------------------------------------------------------------
# Type construction tests
# ---------------------------------------------------------------------------


class TestDialogueManagerTypes:
    def test_dialogue_identifier_defaults(self) -> None:
        ident = DialogueIdentifier()
        assert ident.id
        assert ident.version == 1
        assert ident.created_at is not None

    def test_conversation_identifier_defaults(self) -> None:
        ident = ConversationIdentifier()
        assert ident.conversation_id == ''
        assert ident.turn_number == 0

    def test_detected_intent_defaults(self) -> None:
        intent = DetectedIntent()
        assert intent.intent_type == ''
        assert intent.confidence == 0.0
        assert intent.secondary_intents == ()

    def test_current_cognitive_focus_defaults(self) -> None:
        focus = CurrentCognitiveFocus()
        assert focus.focus_type == ''
        assert focus.attention_weight == 0.5

    def test_active_working_memory_defaults(self) -> None:
        wm = ActiveWorkingMemory()
        assert wm.active_entities == ()
        assert wm.capacity_used == 0.0

    def test_primary_objective_defaults(self) -> None:
        obj = PrimaryObjective()
        assert obj.objective_type == ''
        assert obj.priority == 0.5

    def test_response_strategy_defaults(self) -> None:
        strat = ResponseStrategy()
        assert strat.strategy_type == ''
        assert strat.mode == 'teacher'

    def test_confidence_defaults(self) -> None:
        conf = Confidence()
        assert conf.overall == 0.0
        assert conf.intent_confidence == 0.0

    def test_uncertainty_defaults(self) -> None:
        unc = Uncertainty()
        assert unc.identified_gaps == ()
        assert unc.confidence_intervals == {}

    def test_referenced_memories_defaults(self) -> None:
        rm = ReferencedMemories()
        assert rm.memory_ids == ()

    def test_referenced_evidence_defaults(self) -> None:
        re = ReferencedEvidence()
        assert re.evidence_ids == ()

    def test_follow_up_opportunity_defaults(self) -> None:
        fu = FollowUpOpportunity()
        assert fu.description == ''
        assert fu.priority_score == 0.0

    def test_follow_up_opportunities_defaults(self) -> None:
        fus = FollowUpOpportunities()
        assert fus.opportunities == ()

    def test_version_metadata_defaults(self) -> None:
        vm = VersionMetadata()
        assert vm.schema_version == '1.0.0'
        assert vm.specification_id == 'DLG-01'

    def test_dialogue_plan_defaults(self) -> None:
        plan = DialoguePlan()
        assert plan.primary_objective == ''
        assert plan.secondary_objectives == ()

    def test_dialogue_response_defaults(self) -> None:
        resp = DialogueResponse()
        assert resp.content == ''
        assert resp.response_type == 'text'

    def test_evaluation_result_defaults(self) -> None:
        ev = EvaluationResult()
        assert ev.overall_quality == 0.0
        assert ev.passes_threshold is True

    def test_dialogue_object_defaults(self) -> None:
        obj = DialogueObject()
        assert isinstance(obj.dialogue_identifier, DialogueIdentifier)
        assert isinstance(obj.detected_intent, DetectedIntent)
        assert isinstance(obj.confidence, Confidence)

    def test_dialogue_object_frozen(self) -> None:
        obj = DialogueObject()
        with pytest.raises(AttributeError):
            obj.confidence = Confidence(overall=1.0)  # type: ignore[misc]

    def test_dialogue_objectives_enum(self) -> None:
        assert len(DialogueObjective) == 10
        assert DialogueObjective.ANSWER_QUESTION.value == 'answer_question'
        assert DialogueObjective.CALIBRATE_REALITY.value == 'calibrate_reality'

    def test_intent_type_enum(self) -> None:
        assert len(DetectedIntent.__dataclass_fields__) > 0
        from ayeneh.dlg.manager.types import IntentType
        assert len(IntentType) == 11
        assert IntentType.INFORMATION_SEEKING.value == 'information_seeking'

    def test_dialogue_mode_enum(self) -> None:
        assert len(DialogueMode) == 9
        assert DialogueMode.TEACHER.value == 'teacher'
        assert DialogueMode.SILENT_OBSERVER.value == 'silent_observer'

    def test_dialogue_granularity_enum(self) -> None:
        assert len(DialogueGranularity) == 6
        assert DialogueGranularity.BRIEF.value == 'brief'
        assert DialogueGranularity.SCIENTIFIC_DISCUSSION.value == 'scientific_discussion'


# ---------------------------------------------------------------------------
# Engine pipeline tests
# ---------------------------------------------------------------------------


class TestDialogueManagerPipeline:
    def test_process_returns_dialogue_object(self, manager: DialogueManager) -> None:
        result = manager.process("What is cognitive behavioral therapy?")
        assert isinstance(result, DialogueObject)

    def test_process_detects_information_seeking(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("Explain how memory works")
        assert result.detected_intent.intent_type == 'information_seeking'
        assert result.detected_intent.confidence > 0.0

    def test_process_detects_reflection_intent(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("I notice I keep procrastinating")
        assert result.detected_intent.intent_type == 'reflection'

    def test_process_detects_planning_intent(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("Help me plan my project roadmap")
        assert result.detected_intent.intent_type == 'planning'

    def test_process_detects_debugging_intent(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("I have an error in my code")
        assert result.detected_intent.intent_type == 'debugging'

    def test_process_detects_decision_support(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("Should I choose option A or B?")
        assert result.detected_intent.intent_type == 'decision_support'

    def test_process_detects_learning_intent(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("Teach me about machine learning")
        assert result.detected_intent.intent_type == 'learning'

    def test_process_detects_emotional_processing(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("I feel stressed about the deadline")
        assert result.detected_intent.intent_type == 'emotional_processing'

    def test_process_detects_reality_calibration(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("Is it true that we only use 10% of our brain?")
        assert result.detected_intent.intent_type == 'reality_calibration'

    def test_process_preserves_dialogue_identifiers(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("Hello")
        assert isinstance(result.dialogue_identifier, DialogueIdentifier)
        assert isinstance(result.conversation_identifier, ConversationIdentifier)

    def test_process_preserves_cognitive_focus(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("Explain quantum computing")
        assert isinstance(result.current_cognitive_focus, CurrentCognitiveFocus)
        assert result.current_cognitive_focus.focus_type == 'factual_recall'

    def test_process_preserves_working_memory(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("What do we know about the project?")
        assert isinstance(result.active_working_memory, ActiveWorkingMemory)

    def test_process_preserves_primary_objective(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("Help me understand this concept")
        assert isinstance(result.primary_objective, PrimaryObjective)
        assert result.primary_objective.objective_type != ''

    def test_process_preserves_response_strategy(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("Give me a brief answer")
        assert isinstance(result.response_strategy, ResponseStrategy)

    def test_process_preserves_confidence(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("What is the capital of France?")
        assert isinstance(result.confidence, Confidence)
        assert 0.0 <= result.confidence.overall <= 1.0

    def test_process_preserves_uncertainty(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("What is the meaning of life?")
        assert isinstance(result.uncertainty, Uncertainty)

    def test_process_preserves_referenced_memories(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("Tell me about our last meeting")
        assert isinstance(result.referenced_memories, ReferencedMemories)

    def test_process_preserves_referenced_evidence(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("What evidence supports this claim?")
        assert isinstance(result.referenced_evidence, ReferencedEvidence)

    def test_process_preserves_follow_up_opportunities(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("Explain this concept")
        assert isinstance(result.follow_up_opportunities, FollowUpOpportunities)

    def test_process_preserves_version_metadata(
        self, manager: DialogueManager,
    ) -> None:
        result = manager.process("Hello")
        assert isinstance(result.version_metadata, VersionMetadata)
        assert result.version_metadata.specification_id == 'DLG-01'

    def test_process_with_context(self, manager: DialogueManager) -> None:
        ctx = {
            'active_entities': ('project_alpha', 'team_beta'),
            'recent_facts': ('sprint_started',),
            'active_goals': ('complete_feature_x',),
            'emotional_state': 'focused',
        }
        result = manager.process("What is the status?", context=ctx)
        assert result.active_working_memory.active_entities == (
            'project_alpha', 'team_beta',
        )
        assert result.active_working_memory.recent_facts == ('sprint_started',)
        assert result.active_working_memory.active_goals == ('complete_feature_x',)
        assert result.active_working_memory.emotional_state == 'focused'

    def test_process_increments_turn_count(
        self, manager: DialogueManager,
    ) -> None:
        manager.process("First message")
        result = manager.process("Second message")
        assert result.conversation_identifier.turn_number == 2

    def test_process_multiple_turns(self, manager: DialogueManager) -> None:
        for i in range(5):
            result = manager.process(f"Message {i}")
        assert result.conversation_identifier.turn_number == 5

    def test_process_with_empty_input(self, manager: DialogueManager) -> None:
        result = manager.process("")
        assert isinstance(result, DialogueObject)

    def test_process_granularity_brief(self, manager: DialogueManager) -> None:
        result = manager.process("Give me a quick short brief answer")
        assert result.response_strategy.granularity == 'brief'

    def test_process_granularity_deep(self, manager: DialogueManager) -> None:
        result = manager.process("Give me a deep detailed comprehensive analysis")
        assert result.response_strategy.granularity == 'deep_analysis'

    def test_process_mode_detection(self, manager: DialogueManager) -> None:
        result = manager.process("Teach me about quantum physics")
        assert result.response_strategy.mode == 'teacher'

    def test_process_socratic_mode(self, manager: DialogueManager) -> None:
        result = manager.process("Why do I think this way?")
        assert result.response_strategy.mode == 'socratic_guide'

    def test_process_output_is_frozen(self, manager: DialogueManager) -> None:
        result = manager.process("Hello")
        with pytest.raises(AttributeError):
            result.confidence = Confidence(overall=1.0)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SelfEvaluator tests
# ---------------------------------------------------------------------------


class TestSelfEvaluator:
    def test_evaluate_returns_evaluation_result(
        self, evaluator: SelfEvaluator,
    ) -> None:
        response = DialogueResponse(content="Test response")
        plan = DialoguePlan(primary_objective='answer_question')
        result = evaluator.evaluate(response, plan)
        assert isinstance(result, EvaluationResult)

    def test_evaluate_dimensions_in_range(
        self, evaluator: SelfEvaluator,
    ) -> None:
        response = DialogueResponse(content="A detailed response with citations")
        plan = DialoguePlan(
            primary_objective='answer_question',
            expected_user_benefit='understanding',
        )
        result = evaluator.evaluate(response, plan)
        assert 0.0 <= result.accuracy <= 1.0
        assert 0.0 <= result.evidence_support <= 1.0
        assert 0.0 <= result.explainability <= 1.0
        assert 0.0 <= result.relevance <= 1.0
        assert 0.0 <= result.cognitive_usefulness <= 1.0
        assert 0.0 <= result.uncertainty_communication <= 1.0
        assert 0.0 <= result.narrative_neutrality <= 1.0

    def test_evaluate_quality_score_average(
        self, evaluator: SelfEvaluator,
    ) -> None:
        response = DialogueResponse(content="Test")
        plan = DialoguePlan()
        result = evaluator.evaluate(response, plan)
        expected = (
            result.accuracy + result.evidence_support + result.explainability
            + result.relevance + result.cognitive_usefulness
            + result.uncertainty_communication + result.narrative_neutrality
        ) / 7.0
        assert abs(result.overall_quality - expected) < 0.01

    def test_evaluate_empty_response(
        self, evaluator: SelfEvaluator,
    ) -> None:
        response = DialogueResponse(content="")
        plan = DialoguePlan()
        result = evaluator.evaluate(response, plan)
        assert isinstance(result, EvaluationResult)
        assert result.revision_needed or result.passes_threshold

    def test_evaluate_with_evidence_citations(
        self, evaluator: SelfEvaluator,
    ) -> None:
        response = DialogueResponse(
            content="This is supported by evidence",
            evidence_citations=("source_1", "source_2"),
        )
        plan = DialoguePlan(primary_objective='answer_question')
        result = evaluator.evaluate(response, plan)
        assert result.evidence_support > 0.3

    def test_evaluate_neutral_tone(
        self, evaluator: SelfEvaluator,
    ) -> None:
        response = DialogueResponse(
            content="A calm response",
            emotional_tone='neutral',
        )
        plan = DialoguePlan()
        result = evaluator.evaluate(response, plan)
        assert result.narrative_neutrality > 0.5


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestDialogueManagerPerformance:
    def test_single_turn_latency(self, manager: DialogueManager) -> None:
        start = time.monotonic()
        manager.process("What is cognitive behavioral therapy?")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 100  # Should complete in under 100ms

    def test_multiple_turns_latency(self, manager: DialogueManager) -> None:
        start = time.monotonic()
        for i in range(10):
            manager.process(f"Message {i}: Explain concept {i}")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 500  # 10 turns in under 500ms

    def test_evaluator_latency(self, evaluator: SelfEvaluator) -> None:
        response = DialogueResponse(content="Test response")
        plan = DialoguePlan(primary_objective='answer_question')
        start = time.monotonic()
        evaluator.evaluate(response, plan)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50  # Evaluation under 50ms
