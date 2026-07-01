"""Contemplative Dialogue Framework — single owner of all dialogue decisions.

Ayeneh exists to improve the user's quality of observation
rather than to maximize answers.

This subsystem decides WHAT KIND OF INTERVENTION should happen
before any retrieval, reasoning, or response generation.
"""

from ayeneh.dialogue.engine import DialogueIntentionEngine
from ayeneh.dialogue.policies import (
    DialoguePolicy,
    ObservationFirst,
    PreserveUncertainty,
    PromoteAutonomy,
    QuestionBeforeAdvice,
)
from ayeneh.dialogue.types import (
    DialogueAnalysis,
    DialogueDecision,
    DialogueIntervention,
    DialogueMetadata,
    DialogueNeed,
    DialogueReasoning,
    DialogueSignal,
    DialogueState,
)

__all__ = [
    "DialogueAnalysis",
    "DialogueDecision",
    "DialogueIntentionEngine",
    "DialogueIntervention",
    "DialogueMetadata",
    "DialogueNeed",
    "DialoguePolicy",
    "DialogueReasoning",
    "DialogueSignal",
    "DialogueState",
    "ObservationFirst",
    "PreserveUncertainty",
    "PromoteAutonomy",
    "QuestionBeforeAdvice",
]
