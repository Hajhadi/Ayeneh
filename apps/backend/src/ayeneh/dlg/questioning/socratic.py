"""DLG-05 Socratic Question Progression.

9-step Socratic method for deepening cognitive exploration:

1. Observation
2. Evidence
3. Interpretation
4. AlternativeInterpretation
5. UnderlyingAssumption
6. BroaderPattern
7. IdentityRelationship
8. RealityCalibration
9. MetaCognitiveReflection
"""

from __future__ import annotations

from typing import Any

import structlog

from ayeneh.dlg.questioning.types import SOCRATIC_STEPS

logger = structlog.get_logger(__name__)


class SocraticQuestionProgression:
    """Guides questioning through a 9-step Socratic progression."""

    def __init__(self) -> None:
        self._step_history: list[str] = []

    def get_current_step(self, context: dict[str, Any] | None = None) -> str:
        """Determine the appropriate Socratic step based on context."""
        ctx = context or {}
        depth = ctx.get('depth', 0)
        step_index = min(depth, len(SOCRATIC_STEPS) - 1)
        return SOCRATIC_STEPS[step_index]

    def get_next_step(self, current_step: str) -> str:
        """Return the next step in the Socratic progression."""
        try:
            idx = SOCRATIC_STEPS.index(current_step)
            if idx < len(SOCRATIC_STEPS) - 1:
                return SOCRATIC_STEPS[idx + 1]
        except ValueError:
            pass
        return SOCRATIC_STEPS[0]

    def get_step_prompt(self, step: str, context: dict[str, Any] | None = None) -> str:
        """Return the guiding prompt for a given Socratic step."""
        prompts: dict[str, str] = {
            'observation': 'What exactly are you observing in this situation?',
            'evidence': 'What evidence do you have for this observation?',
            'interpretation': 'How are you interpreting what you observe?',
            'alternative_interpretation': 'Could there be another way to interpret this?',
            'underlying_assumption': 'What assumption lies beneath your interpretation?',
            'broader_pattern': 'Does this connect to a broader pattern in your life?',
            'identity_relationship': 'How does this relate to who you are?',
            'reality_calibration': 'How well does this match objective reality?',
            'meta_cognitive_reflection': 'What does your thinking about this tell you?',
        }
        return prompts.get(step, 'Tell me more about your perspective.')

    def record_step(self, step: str) -> None:
        """Record that a Socratic step was used."""
        self._step_history.append(step)
        logger.debug('socratic_step_recorded', step=step)

    def get_progress(self) -> dict[str, Any]:
        """Return the current Socratic progression state."""
        return {
            'steps_used': list(self._step_history),
            'total_steps': len(SOCRATIC_STEPS),
            'unique_steps_used': len(set(self._step_history)),
            'deepest_step_reached': self._deepest_step(),
        }

    def _deepest_step(self) -> str:
        if not self._step_history:
            return SOCRATIC_STEPS[0]
        deepest_index = 0
        for step in self._step_history:
            try:
                idx = SOCRATIC_STEPS.index(step)
                deepest_index = max(deepest_index, idx)
            except ValueError:
                pass
        return SOCRATIC_STEPS[deepest_index]

    def should_advance(self, current_step: str, response_quality: float) -> bool:
        """Decide whether to advance to the next Socratic step."""
        if response_quality >= 0.7:
            return True
        if current_step in ('observation', 'evidence'):
            return response_quality >= 0.5
        return False

    def reset(self) -> None:
        """Reset the progression to the beginning."""
        self._step_history.clear()
        logger.debug('socratic_progression_reset')
