"""Tests for DLG-05 Question Generation."""

from __future__ import annotations

import pytest

from ayeneh.dlg.questioning.engine import QuestionGenerationEngine
from ayeneh.dlg.questioning.socratic import SocraticQuestionProgression
from ayeneh.dlg.questioning.types import (
    QUESTION_CATEGORIES,
    QUESTION_OBJECTIVES,
    SOCRATIC_STEPS,
    AssociatedCognitiveObjects,
    ExpectedInformationGain,
    PrimaryObjective,
    QuestionIdentifier,
    QuestionObject,
    QuestionType,
    RelevantEvidence,
    TargetUncertainty,
    VersionMetadata,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> QuestionGenerationEngine:
    return QuestionGenerationEngine()


@pytest.fixture
def socratic() -> SocraticQuestionProgression:
    return SocraticQuestionProgression()


# ---------------------------------------------------------------------------
# Type tests
# ---------------------------------------------------------------------------


class TestQuestionTypes:
    def test_objectives_count(self) -> None:
        assert len(QUESTION_OBJECTIVES) == 11

    def test_objective_values(self) -> None:
        assert 'clarify_ambiguity' in QUESTION_OBJECTIVES
        assert 'expand_reflection' in QUESTION_OBJECTIVES

    def test_categories_count(self) -> None:
        assert len(QUESTION_CATEGORIES) == 10

    def test_category_values(self) -> None:
        assert 'clarification' in QUESTION_CATEGORIES
        assert 'meta_cognitive' in QUESTION_CATEGORIES

    def test_socratic_steps_count(self) -> None:
        assert len(SOCRATIC_STEPS) == 9

    def test_socratic_steps_values(self) -> None:
        assert SOCRATIC_STEPS[0] == 'observation'
        assert SOCRATIC_STEPS[-1] == 'meta_cognitive_reflection'

    def test_question_identifier_frozen(self) -> None:
        qi = QuestionIdentifier(id='test-id')
        with pytest.raises(AttributeError):
            qi.id = 'other'  # type: ignore[misc]

    def test_question_type_defaults(self) -> None:
        qt = QuestionType()
        assert qt.primary_type == 'open_ended'
        assert qt.complexity == 1

    def test_primary_objective_defaults(self) -> None:
        po = PrimaryObjective()
        assert po.priority == 0.5

    def test_associated_cognitive_objects_defaults(self) -> None:
        aco = AssociatedCognitiveObjects()
        assert len(aco.belief_ids) == 0
        assert len(aco.goal_ids) == 0

    def test_relevant_evidence_defaults(self) -> None:
        re = RelevantEvidence()
        assert len(re.evidence_ids) == 0

    def test_target_uncertainty_defaults(self) -> None:
        tu = TargetUncertainty()
        assert tu.current_confidence == 0.0
        assert tu.target_confidence == 0.0

    def test_expected_information_gain_defaults(self) -> None:
        eig = ExpectedInformationGain()
        assert eig.overall_gain == 0.0

    def test_question_object_frozen(self) -> None:
        qo = QuestionObject()
        with pytest.raises(AttributeError):
            qo.question_text = 'new'  # type: ignore[misc]

    def test_question_object_defaults(self) -> None:
        qo = QuestionObject()
        assert qo.estimated_cognitive_load == 0.3
        assert qo.estimated_reflection_value == 0.5
        assert qo.confidence == 0.5

    def test_version_metadata_defaults(self) -> None:
        vm = VersionMetadata()
        assert vm.schema_version == '1.0.0'


# ---------------------------------------------------------------------------
# Socratic progression tests
# ---------------------------------------------------------------------------


class TestSocraticQuestionProgression:
    def test_get_current_step_default(self, socratic: SocraticQuestionProgression) -> None:
        step = socratic.get_current_step()
        assert step == 'observation'

    def test_get_current_step_depth(self, socratic: SocraticQuestionProgression) -> None:
        step = socratic.get_current_step({'depth': 3})
        assert step == 'alternative_interpretation'

    def test_get_current_step_deep(self, socratic: SocraticQuestionProgression) -> None:
        step = socratic.get_current_step({'depth': 100})
        assert step == 'meta_cognitive_reflection'

    def test_get_next_step(self, socratic: SocraticQuestionProgression) -> None:
        nxt = socratic.get_next_step('observation')
        assert nxt == 'evidence'

    def test_get_next_step_last(self, socratic: SocraticQuestionProgression) -> None:
        nxt = socratic.get_next_step('meta_cognitive_reflection')
        assert nxt == 'observation'

    def test_get_next_step_invalid(self, socratic: SocraticQuestionProgression) -> None:
        nxt = socratic.get_next_step('nonexistent')
        assert nxt == 'observation'

    def test_get_step_prompt(self, socratic: SocraticQuestionProgression) -> None:
        prompt = socratic.get_step_prompt('observation')
        assert 'observing' in prompt.lower()

    def test_get_step_prompt_all_steps(self, socratic: SocraticQuestionProgression) -> None:
        for step in SOCRATIC_STEPS:
            prompt = socratic.get_step_prompt(step)
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    def test_record_step(self, socratic: SocraticQuestionProgression) -> None:
        socratic.record_step('observation')
        progress = socratic.get_progress()
        assert 'observation' in progress['steps_used']

    def test_get_progress_empty(self, socratic: SocraticQuestionProgression) -> None:
        progress = socratic.get_progress()
        assert progress['total_steps'] == 9
        assert progress['unique_steps_used'] == 0

    def test_get_progress_multiple(self, socratic: SocraticQuestionProgression) -> None:
        socratic.record_step('observation')
        socratic.record_step('evidence')
        socratic.record_step('observation')
        progress = socratic.get_progress()
        assert progress['unique_steps_used'] == 2

    def test_deepest_step(self, socratic: SocraticQuestionProgression) -> None:
        socratic.record_step('observation')
        socratic.record_step('identity_relationship')
        progress = socratic.get_progress()
        assert progress['deepest_step_reached'] == 'identity_relationship'

    def test_should_advance_high_quality(self, socratic: SocraticQuestionProgression) -> None:
        assert socratic.should_advance('observation', 0.8) is True

    def test_should_advance_low_quality(self, socratic: SocraticQuestionProgression) -> None:
        assert socratic.should_advance('reality_calibration', 0.3) is False

    def test_should_advance_observation(self, socratic: SocraticQuestionProgression) -> None:
        assert socratic.should_advance('observation', 0.6) is True

    def test_reset(self, socratic: SocraticQuestionProgression) -> None:
        socratic.record_step('observation')
        socratic.reset()
        progress = socratic.get_progress()
        assert progress['unique_steps_used'] == 0


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


class TestQuestionGenerationEngine:
    def test_process_returns_none_or_question(
        self, engine: QuestionGenerationEngine,
    ) -> None:
        result = engine.process({})
        assert result is None or isinstance(result, QuestionObject)

    def test_process_empty_context(self, engine: QuestionGenerationEngine) -> None:
        result = engine.process({})
        assert result is None or isinstance(result, QuestionObject)

    def test_process_with_dict_context(self, engine: QuestionGenerationEngine) -> None:
        ctx = {
            'relevant_beliefs': {'belief_ids': ('b1',), 'belief_statements': ('test',)},
            'relevant_goals': {'goal_ids': ('g1',), 'goal_progress': (0.1,)},
        }
        result = engine.process(ctx)
        assert isinstance(result, QuestionObject)
        assert result.question_text != ''

    def test_process_with_knowledge(self, engine: QuestionGenerationEngine) -> None:
        ctx = {
            'relevant_beliefs': {'belief_ids': ('b1',), 'belief_statements': ('test',)},
        }
        knowledge = {'b1': {'content': 'known'}}
        result = engine.process(ctx, existing_knowledge=knowledge)
        assert isinstance(result, QuestionObject)

    def test_process_all_gaps_known(self, engine: QuestionGenerationEngine) -> None:
        ctx = {
            'relevant_beliefs': {'belief_ids': ('b1',), 'belief_statements': ('test',)},
        }
        knowledge = {'b1': {}}
        result = engine.process(ctx, existing_knowledge=knowledge)
        assert isinstance(result, QuestionObject)

    def test_process_low_intent_confidence(self, engine: QuestionGenerationEngine) -> None:
        ctx = {'current_intent': {'confidence': 0.2}}
        result = engine.process(ctx)
        assert isinstance(result, QuestionObject)

    def test_process_with_history(self, engine: QuestionGenerationEngine) -> None:
        result = engine.process({}, conversation_history=['msg1', 'msg2'])
        assert result is None or isinstance(result, QuestionObject)

    def test_process_question_has_identifier(
        self, engine: QuestionGenerationEngine,
    ) -> None:
        ctx = {
            'relevant_beliefs': {'belief_ids': ('b1',), 'belief_statements': ('test',)},
        }
        result = engine.process(ctx)
        if result is not None:
            assert result.question_identifier.id != ''

    def test_process_question_has_type(
        self, engine: QuestionGenerationEngine,
    ) -> None:
        ctx = {
            'relevant_beliefs': {'belief_ids': ('b1',), 'belief_statements': ('test',)},
        }
        result = engine.process(ctx)
        if result is not None:
            assert result.question_type.primary_type == 'open_ended'
