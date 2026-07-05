"""DLG-02 State Transition Detector.

Detects and evaluates state transitions including entry conditions,
exit conditions, nested states, parallel states, and priority dynamics.

Specification: DLG-02 §6-§11, §13-§17.
"""

from __future__ import annotations

from typing import Any

import structlog

from ayeneh.dlg.state.types import (
    ConversationStateObject,
    ExitCondition,
    ExitConditions,
    NestedState,
    ParallelState,
    StatePriority,
)

logger = structlog.get_logger(__name__)

# Default exit condition triggers
_EXIT_SIGNALS: dict[str, list[str]] = {
    'question_answered': ['answer', 'solved', 'resolved', 'got it'],
    'problem_resolved': ['fixed', 'working', 'resolved', 'solution'],
    'goal_achieved': ['done', 'completed', 'finished', 'achieved'],
    'context_shifted': ['different', 'another', 'instead', 'unrelated'],
    'dialogue_redirected': ['let us', 'moving on', 'actually', 'change topic'],
    'user_initiated_exit': ['bye', 'goodbye', 'see you', 'thanks', 'that is all'],
    'natural_conclusion': ['wrap up', 'conclude', 'summary', 'end'],
}

# Entry condition signal keywords
_ENTRY_SIGNALS: dict[str, list[str]] = {
    'reflection': [
        'notice', 'pattern', 'always', 'recurring', 'observe',
    ],
    'reality_calibration': [
        'true', 'real', 'actually', 'evidence', 'fact',
    ],
    'identity_exploration': [
        'who am i', 'values', 'beliefs', 'purpose', 'meaning',
    ],
    'meta_cognitive_reflection': [
        'thinking about', 'awareness', 'metacognition', 'observe my',
    ],
    'narrative_investigation': [
        'story', 'journey', 'narrative', 'theme', 'meaning',
    ],
}


class StateTransitionDetector:
    """Detects state transitions through probabilistic evaluation.

    Evaluates entry conditions, exit conditions, nested states,
    parallel states, and priority dynamics.
    """

    def check_exit_conditions(
        self,
        state: ConversationStateObject,
        ctx: dict[str, Any],
    ) -> bool:
        """Check if any exit conditions for the current state are met."""
        text = ctx.get('user_input', '').lower()
        state_type = state.current_state_type.state_type

        # Check explicit exit conditions on the state
        for condition in state.exit_conditions.conditions:
            if condition.is_met:
                logger.info(
                    "exit_condition_met",
                    state=state_type,
                    condition=condition.condition_type,
                )
                return True

        # Check signal-based exits
        for exit_type, signals in _EXIT_SIGNALS.items():
            if any(s in text for s in signals):
                if self._is_valid_exit_target(state_type, exit_type):
                    logger.info(
                        "exit_signal_detected",
                        state=state_type,
                        signal=exit_type,
                    )
                    return True

        # Check turn-based exit
        turn_count = state.entry_time.turn_count
        if turn_count > 0 and state.entry_time.turn_count > 20:
            return True

        return False

    def detect_entry_conditions(
        self,
        text: str,
        ctx: dict[str, Any],
    ) -> dict[str, float]:
        """Evaluate probabilistic entry conditions for each state."""
        text_lower = text.lower()
        scores: dict[str, float] = {}

        for state_type, signals in _ENTRY_SIGNALS.items():
            matches = [s for s in signals if s in text_lower]
            if matches:
                scores[state_type] = min(1.0, 0.4 + len(matches) * 0.2)

        return scores

    def detect_nested_states(
        self,
        current_state: ConversationStateObject,
        intents: dict[str, float],
        ctx: dict[str, Any],
    ) -> tuple[NestedState, ...]:
        """Detect potential nested sub-states."""
        nested: list[NestedState] = []
        current_type = current_state.current_state_type.state_type

        # Nesting rules: certain states naturally contain sub-states
        nesting_rules: dict[str, list[str]] = {
            'exploration': ['analysis', 'reflection'],
            'analysis': ['problem_definition', 'information_gathering'],
            'planning': ['decision_support', 'analysis'],
            'narrative_investigation': ['reality_calibration', 'reflection'],
            'identity_exploration': ['reflection', 'meta_cognitive_reflection'],
        }

        allowed_children = nesting_rules.get(current_type, [])
        for child in allowed_children:
            score = intents.get(child, 0.0)
            if score > 0.3:
                nested.append(NestedState(
                    state_type=child,
                    state_name=child.replace('_', ' ').title(),
                    depth_level=current_state.current_state_type.depth_level + 1,
                    objective=f"Sub-state: {child}",
                    is_active=True,
                ))

        return tuple(nested)

    def detect_parallel_states(
        self,
        current_state: ConversationStateObject,
        intents: dict[str, float],
        ctx: dict[str, Any],
    ) -> tuple[ParallelState, ...]:
        """Detect parallel states that may be active simultaneously."""
        parallel: list[ParallelState] = []
        current_type = current_state.current_state_type.state_type

        # Parallel state rules: some states can coexist
        parallel_compatibility: dict[str, list[str]] = {
            'analysis': ['reflection', 'reality_calibration'],
            'planning': ['decision_support', 'project_design'],
            'reflection': ['identity_exploration', 'narrative_investigation'],
            'exploration': ['learning', 'curiosity'],
        }

        compatible = parallel_compatibility.get(current_type, [])
        total_score = sum(intents.get(s, 0.0) for s in compatible)

        for candidate in compatible:
            score = intents.get(candidate, 0.0)
            if score > 0.2 and total_score > 0:
                attention_share = score / total_score if total_score > 0 else 0.0
                parallel.append(ParallelState(
                    state_type=candidate,
                    state_name=candidate.replace('_', ' ').title(),
                    priority=StatePriority.NORMAL.value,
                    attention_share=attention_share,
                    is_primary=False,
                ))

        return tuple(parallel)

    def determine_priority(
        self,
        candidates: list[dict[str, Any]],
        ctx: dict[str, Any],
    ) -> str:
        """Determine priority among competing states."""
        if not candidates:
            return StatePriority.NORMAL.value

        # Sort by urgency and importance
        scored = []
        for candidate in candidates:
            urgency = candidate.get('urgency', 0.0)
            importance = candidate.get('importance', 0.0)
            evidence = candidate.get('evidence_strength', 0.0)
            continuity = candidate.get('continuity', 0.0)
            total = urgency * 0.3 + importance * 0.3 + evidence * 0.2 + continuity * 0.2
            scored.append((candidate, total))

        scored.sort(key=lambda x: x[1], reverse=True)
        best_score = scored[0][1] if scored else 0.0

        if best_score > 0.8:
            return StatePriority.CRITICAL.value
        if best_score > 0.6:
            return StatePriority.HIGH.value
        if best_score > 0.3:
            return StatePriority.NORMAL.value
        return StatePriority.LOW.value

    def _is_valid_exit_target(self, current_state: str, exit_type: str) -> bool:
        """Check if the exit type is valid for the current state."""
        # Some states should not exit on certain signals
        restricted_exits: dict[str, set[str]] = {
            'greeting': {'question_answered', 'problem_resolved'},
            'closure': set(),
        }
        restricted = restricted_exits.get(current_state, set())
        return exit_type not in restricted
