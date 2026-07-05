"""DLG-02 Conversation State Machine engine.

Models conversation as a dynamic state machine through an 8-phase pipeline:
User Input -> Intent Analysis -> Current State Identification ->
Transition Detection -> Dialogue Strategy Selection -> Response Planning ->
State Update -> Memory Update.

Specification: DLG-02 Conversation State Machine.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from ayeneh.dlg.state.transitions import StateTransitionDetector
from ayeneh.dlg.state.types import (
    AssociatedEpisodes,
    AssociatedGoals,
    AssociatedNarratives,
    AssociatedWorkingMemory,
    ConversationHealthIndicators,
    ConversationIdentifier,
    ConversationState,
    CurrentCognitiveFocus,
    CurrentStateType,
    EntryTime,
    ExpectedObjective,
    NestedState,
    OpenQuestion,
    OpenQuestions,
    ExitCondition,
    ExitConditions,
    ParallelState,
    StateConfidence,
    StateDialogueStrategy,
    StateIdentifier,
    StateTransitionResult,
    TransitionRecord,
    TransitionType,
    ConversationStateObject,
    VersionEntry,
    VersionHistory,
)

logger = structlog.get_logger(__name__)

# Intent analysis keyword maps
_STATE_INTENT_HINTS: dict[str, list[str]] = {
    'greeting': ['hello', 'hi', 'hey', 'good morning', 'good evening'],
    'information_gathering': [
        'what', 'how', 'tell me', 'explain', 'describe', 'define',
    ],
    'problem_definition': [
        'problem', 'issue', 'error', 'struggling', 'stuck', 'broken',
    ],
    'exploration': [
        'explore', 'wonder', 'what if', 'curious', 'investigate',
    ],
    'reflection': [
        'reflect', 'think about', 'notice', 'pattern', 'always',
    ],
    'analysis': [
        'analyze', 'compare', 'evaluate', 'assess', 'measure',
    ],
    'planning': [
        'plan', 'strategy', 'roadmap', 'steps', 'approach',
    ],
    'decision_support': [
        'should i', 'which', 'decide', 'choose', 'recommend',
    ],
    'reality_calibration': [
        'is it true', 'actually', 'really', 'fact', 'evidence',
    ],
    'narrative_investigation': [
        'story', 'narrative', 'journey', 'meaning', 'theme',
    ],
    'identity_exploration': [
        'who am i', 'identity', 'values', 'beliefs', 'purpose',
    ],
    'meta_cognitive_reflection': [
        'thinking about thinking', 'metacognition', 'awareness',
    ],
    'project_design': [
        'design', 'architecture', 'system', 'structure', 'build',
    ],
    'review': [
        'review', 'check', 'validate', 'verify', 'audit',
    ],
    'closure': [
        'wrap up', 'conclude', 'summary', 'end', 'finish',
    ],
}

# Valid transitions between states
_VALID_TRANSITIONS: dict[str, tuple[str, ...]] = {
    'greeting': ('information_gathering', 'exploration', 'closure'),
    'information_gathering': (
        'problem_definition', 'exploration', 'analysis', 'planning',
    ),
    'problem_definition': (
        'analysis', 'exploration', 'planning', 'decision_support',
    ),
    'exploration': (
        'reflection', 'analysis', 'narrative_investigation',
        'identity_exploration',
    ),
    'reflection': (
        'meta_cognitive_reflection', 'analysis', 'planning', 'closure',
    ),
    'analysis': (
        'planning', 'decision_support', 'review', 'reflection',
    ),
    'planning': (
        'decision_support', 'project_design', 'review',
    ),
    'decision_support': ('review', 'planning', 'closure'),
    'reality_calibration': (
        'reflection', 'narrative_investigation', 'analysis',
    ),
    'narrative_investigation': (
        'reality_calibration', 'reflection', 'identity_exploration',
    ),
    'identity_exploration': (
        'reflection', 'meta_cognitive_reflection', 'narrative_investigation',
    ),
    'meta_cognitive_reflection': (
        'reflection', 'analysis', 'closure',
    ),
    'project_design': (
        'planning', 'review', 'analysis',
    ),
    'review': ('closure', 'planning', 'analysis'),
    'closure': ('greeting', 'information_gathering'),
}


class ConversationStateMachine:
    """Models conversation as a dynamic state machine.

    Every interaction occurs within a current cognitive state. Each response
    may maintain, deepen, transition, or resolve the current state.
    """

    def __init__(self, ai_router: Any = None) -> None:
        self._ai_router = ai_router
        self._transition_detector = StateTransitionDetector()
        self._turn_count: int = 0
        self._current_state: ConversationStateObject | None = None
        self._state_history: list[TransitionRecord] = []
        self._suspended_states: list[ConversationStateObject] = []
        self._conversation_health = ConversationHealthIndicators()

    @property
    def current_state(self) -> ConversationStateObject | None:
        """Return the current conversation state."""
        return self._current_state

    @property
    def state_history(self) -> list[TransitionRecord]:
        """Return the history of state transitions."""
        return list(self._state_history)

    def process(
        self,
        user_input: str,
        context: dict[str, Any] | None = None,
    ) -> ConversationStateObject:
        """Run the full 8-phase state machine pipeline."""
        ctx = context or {}
        start = time.monotonic()

        logger.info(
            "dlg02_pipeline_start",
            input_length=len(user_input),
            turn=self._turn_count,
            current_state=(
                self._current_state.current_state_type.state_type
                if self._current_state else 'none'
            ),
        )

        # Phase 1: User Input
        processed_input = self._process_user_input(user_input, ctx)

        # Phase 2: Intent Analysis
        detected_intents = self._analyze_intent(processed_input, ctx)

        # Phase 3: Current State Identification
        current_state = self._identify_current_state(detected_intents, ctx)

        # Phase 4: Transition Detection
        transition_result = self._detect_transitions(
            current_state, detected_intents, ctx,
        )

        # Phase 5: Dialogue Strategy Selection
        strategy = self._select_dialogue_strategy(
            current_state, transition_result, detected_intents, ctx,
        )

        # Phase 6: Response Planning
        response_plan = self._plan_response(
            current_state, transition_result, strategy, ctx,
        )

        # Phase 7: State Update
        updated_state = self._update_state(
            current_state, transition_result, response_plan, ctx,
        )

        # Phase 8: Memory Update
        self._update_memory(
            processed_input, detected_intents, updated_state, ctx,
        )

        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "dlg02_pipeline_complete",
            state=updated_state.current_state_type.state_type,
            transitioned=transition_result.should_transition,
            confidence=round(updated_state.confidence.overall, 3),
            latency_ms=round(elapsed_ms, 2),
        )

        return updated_state

    # ------------------------------------------------------------------
    # Phase 1: User Input Processing
    # ------------------------------------------------------------------

    def _process_user_input(
        self, user_input: str, ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize user input for state analysis."""
        normalized = user_input.strip()
        return {
            'raw_input': user_input,
            'normalized_input': normalized,
            'input_length': len(normalized),
            'word_count': len(normalized.split()),
            'turn_number': self._turn_count,
            'context': ctx,
        }

    # ------------------------------------------------------------------
    # Phase 2: Intent Analysis
    # ------------------------------------------------------------------

    def _analyze_intent(
        self,
        processed_input: dict[str, Any],
        ctx: dict[str, Any],
    ) -> dict[str, float]:
        """Analyze user intent for state determination."""
        text = processed_input['normalized_input'].lower()
        scores: dict[str, float] = {}

        for state_type, keywords in _STATE_INTENT_HINTS.items():
            matches = [kw for kw in keywords if kw in text]
            if matches:
                scores[state_type] = min(1.0, 0.3 + len(matches) * 0.2)

        if not scores:
            if self._current_state:
                current_type = self._current_state.current_state_type.state_type
                scores[current_type] = 0.5
            else:
                scores['greeting'] = 0.3

        return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))

    # ------------------------------------------------------------------
    # Phase 3: Current State Identification
    # ------------------------------------------------------------------

    def _identify_current_state(
        self,
        intents: dict[str, float],
        ctx: dict[str, Any],
    ) -> ConversationStateObject:
        """Identify or create the current conversation state."""
        if self._current_state is None:
            return self._create_initial_state(intents, ctx)

        # Check if we should stay in current state
        current_type = self._current_state.current_state_type.state_type
        current_score = intents.get(current_type, 0.0)

        # If a higher-scored valid transition exists, it will be caught
        # by the transition detector in Phase 4
        return self._current_state

    def _create_initial_state(
        self,
        intents: dict[str, float],
        ctx: dict[str, Any],
    ) -> ConversationStateObject:
        """Create the initial conversation state."""
        top_intent = next(iter(intents), 'greeting')

        state_type = CurrentStateType(
            state_type=top_intent,
            state_name=top_intent.replace('_', ' ').title(),
            description=f"Initial state: {top_intent}",
            is_initial=True,
        )

        return ConversationStateObject(
            state_identifier=StateIdentifier(),
            conversation_identifier=ConversationIdentifier(
                turn_number=self._turn_count,
                session_id=ctx.get('session_id', ''),
                user_id=ctx.get('user_id', ''),
            ),
            current_state_type=state_type,
            entry_time=EntryTime(turn_count=self._turn_count),
            expected_objective=ExpectedObjective(
                description=f"Pursue {top_intent}",
            ),
            confidence=StateConfidence(
                overall=0.5,
                state_confidence=intents.get(top_intent, 0.5),
            ),
        )

    # ------------------------------------------------------------------
    # Phase 4: Transition Detection
    # ------------------------------------------------------------------

    def _detect_transitions(
        self,
        current_state: ConversationStateObject,
        intents: dict[str, float],
        ctx: dict[str, Any],
    ) -> StateTransitionResult:
        """Detect state transitions."""
        current_type = current_state.current_state_type.state_type

        # Get exit condition evaluation
        exit_met = self._transition_detector.check_exit_conditions(
            current_state, ctx,
        )

        # Check for valid transitions based on intents
        best_target: str | None = None
        best_score = 0.0

        for candidate_state, score in intents.items():
            if candidate_state == current_type:
                continue
            if score > best_score:
                valid_targets = _VALID_TRANSITIONS.get(current_type, ())
                if candidate_state in valid_targets or not valid_targets:
                    best_target = candidate_state
                    best_score = score

        # Determine if transition should occur
        transition_threshold = 0.4
        should_transition = (
            (best_target is not None and best_score >= transition_threshold)
            or exit_met
        )

        if should_transition and best_target:
            return StateTransitionResult(
                should_transition=True,
                target_state=best_target,
                transition_type=TransitionType.TRANSITION.value,
                confidence=best_score,
                reason=(
                    f"Intent score {best_score:.2f} for {best_target}"
                    if best_score >= transition_threshold
                    else "Exit condition met"
                ),
            )

        # Check for nesting opportunities
        nested = self._transition_detector.detect_nested_states(
            current_state, intents, ctx,
        )

        # Check for parallel states
        parallel = self._transition_detector.detect_parallel_states(
            current_state, intents, ctx,
        )

        return StateTransitionResult(
            should_transition=False,
            target_state=current_type,
            transition_type=TransitionType.MAINTAIN.value,
            confidence=current_state.confidence.overall,
            nested_states=nested,
            parallel_states=parallel,
        )

    # ------------------------------------------------------------------
    # Phase 5: Dialogue Strategy Selection
    # ------------------------------------------------------------------

    def _select_dialogue_strategy(
        self,
        current_state: ConversationStateObject,
        transition: StateTransitionResult,
        intents: dict[str, float],
        ctx: dict[str, Any],
    ) -> StateDialogueStrategy:
        """Select dialogue strategy for the current state."""
        state_type = current_state.current_state_type.state_type

        strategy_map: dict[str, tuple[str, str]] = {
            'greeting': ('warm_opening', 'friendly'),
            'information_gathering': ('focused_inquiry', 'direct'),
            'problem_definition': ('structured_diagnosis', 'analytical'),
            'exploration': ('open_ended', 'curious'),
            'reflection': ('socratic', 'gentle'),
            'analysis': ('analytical', 'systematic'),
            'planning': ('structured', 'action_oriented'),
            'decision_support': ('comparative', 'balanced'),
            'reality_calibration': ('evidence_based', 'calibrated'),
            'narrative_investigation': ('interpretive', 'empathic'),
            'identity_exploration': ('exploratory', 'safe'),
            'meta_cognitive_reflection': ('meta_cognitive', 'observational'),
            'project_design': ('architectural', 'systematic'),
            'review': ('evaluative', 'thorough'),
            'closure': ('summarizing', 'integrative'),
        }

        strategy_type, response_style = strategy_map.get(
            state_type, ('default', 'neutral'),
        )

        intervention_level = 0.5
        if transition.should_transition:
            intervention_level = 0.3
        elif state_type in ('reflection', 'identity_exploration'):
            intervention_level = 0.7

        return StateDialogueStrategy(
            strategy_type=strategy_type,
            response_style=response_style,
            intervention_level=intervention_level,
            question_generation=state_type in (
                'exploration', 'reflection', 'identity_exploration',
                'meta_cognitive_reflection',
            ),
            reflection_timing='opportunistic',
        )

    # ------------------------------------------------------------------
    # Phase 6: Response Planning
    # ------------------------------------------------------------------

    def _plan_response(
        self,
        current_state: ConversationStateObject,
        transition: StateTransitionResult,
        strategy: StateDialogueStrategy,
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        """Plan the response based on state and strategy."""
        return {
            'strategy': strategy.strategy_type,
            'style': strategy.response_style,
            'intervention_level': strategy.intervention_level,
            'questions_enabled': strategy.question_generation,
            'transition_context': {
                'should_transition': transition.should_transition,
                'target': transition.target_state,
                'type': transition.transition_type,
            },
            'state_depth': current_state.current_state_type.depth_level,
        }

    # ------------------------------------------------------------------
    # Phase 7: State Update
    # ------------------------------------------------------------------

    def _update_state(
        self,
        current_state: ConversationStateObject,
        transition: StateTransitionResult,
        response_plan: dict[str, Any],
        ctx: dict[str, Any],
    ) -> ConversationStateObject:
        """Update the conversation state based on the pipeline."""
        if transition.should_transition:
            # Record transition
            record = TransitionRecord(
                from_state=current_state.current_state_type.state_type,
                to_state=transition.target_state,
                transition_type=transition.transition_type,
                trigger_reason=transition.reason,
                confidence=transition.confidence,
                turn_number=self._turn_count,
            )
            self._state_history.append(record)

            # Suspend current state if needed
            if transition.transition_type == TransitionType.SUSPEND.value:
                self._suspended_states.append(current_state)

            # Create new state
            new_state_type = CurrentStateType(
                state_type=transition.target_state,
                state_name=transition.target_state.replace('_', ' ').title(),
                description=f"Transitioned from {current_state.current_state_type.state_type}",
                is_initial=False,
            )

            new_entry = EntryTime(
                turn_count=self._turn_count,
            )

            new_confidence = StateConfidence(
                overall=transition.confidence,
                state_confidence=transition.confidence,
                transition_confidence=transition.confidence,
            )

            new_version = VersionHistory(
                versions=(
                    VersionEntry(
                        version=1,
                        change_description=f"Created via transition from {record.from_state}",
                    ),
                ),
                current_version=1,
                total_changes=1,
            )

            updated = ConversationStateObject(
                state_identifier=StateIdentifier(),
                conversation_identifier=current_state.conversation_identifier,
                current_state_type=new_state_type,
                entry_time=new_entry,
                expected_objective=ExpectedObjective(
                    description=f"Pursue {transition.target_state}",
                ),
                current_cognitive_focus=current_state.current_cognitive_focus,
                confidence=new_confidence,
                version_history=new_version,
            )

            self._current_state = updated
            return updated

        # No transition — update existing state
        old_entry = current_state.entry_time
        updated_entry = EntryTime(
            entry_timestamp=old_entry.entry_timestamp,
            duration_seconds=old_entry.duration_seconds,
            turn_count=old_entry.turn_count + 1,
        )

        updated_confidence = StateConfidence(
            overall=current_state.confidence.overall,
            state_confidence=current_state.confidence.state_confidence,
            transition_confidence=current_state.confidence.transition_confidence,
            prediction_confidence=transition.confidence,
        )

        old_version = current_state.version_history
        new_entry_version = VersionEntry(
            version=old_version.current_version + 1,
            change_description=f"Turn {self._turn_count} update",
        )
        updated_version = VersionHistory(
            versions=old_version.versions + (new_entry_version,),
            current_version=old_version.current_version + 1,
            total_changes=old_version.total_changes + 1,
        )

        updated = ConversationStateObject(
            state_identifier=current_state.state_identifier,
            conversation_identifier=current_state.conversation_identifier,
            current_state_type=current_state.current_state_type,
            entry_time=updated_entry,
            expected_objective=current_state.expected_objective,
            current_cognitive_focus=current_state.current_cognitive_focus,
            associated_working_memory=current_state.associated_working_memory,
            associated_episodes=current_state.associated_episodes,
            associated_goals=current_state.associated_goals,
            associated_narratives=current_state.associated_narratives,
            confidence=updated_confidence,
            open_questions=current_state.open_questions,
            exit_conditions=current_state.exit_conditions,
            version_history=updated_version,
        )

        self._current_state = updated
        return updated

    # ------------------------------------------------------------------
    # Phase 8: Memory Update
    # ------------------------------------------------------------------

    def _update_memory(
        self,
        processed_input: dict[str, Any],
        intents: dict[str, float],
        state: ConversationStateObject,
        ctx: dict[str, Any],
    ) -> None:
        """Update state machine memory."""
        self._turn_count += 1
        logger.info(
            "dlg02_memory_updated",
            turn=self._turn_count,
            state=state.current_state_type.state_type,
            history_length=len(self._state_history),
            suspended_count=len(self._suspended_states),
        )
