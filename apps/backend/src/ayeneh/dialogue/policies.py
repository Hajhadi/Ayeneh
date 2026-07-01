"""Dialogue policies — configurable contemplative behavior rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class DialoguePolicy(Protocol):
    """Protocol for configurable dialogue policies."""

    @property
    def name(self) -> str:
        """Policy name."""
        ...

    def should_apply(self, context: dict) -> bool:
        """Whether this policy should be applied in the given context."""
        ...

    def get_instruction(self) -> str:
        """Instruction text for prompt construction."""
        ...


@dataclass
class ObservationFirst:
    """Prefer observation over advice. Core Ayeneh philosophy."""

    name: str = "observation_first"
    weight: float = 1.0

    def should_apply(self, context: dict) -> bool:
        return True

    def get_instruction(self) -> str:
        return (
            "Prioritize observation over advice. "
            "Reflect back what the user is experiencing rather than telling them what to do."
        )


@dataclass
class QuestionBeforeAdvice:
    """Ask questions before offering any advice or interpretation."""

    name: str = "question_before_advice"
    weight: float = 0.9

    def should_apply(self, context: dict) -> bool:
        return True

    def get_instruction(self) -> str:
        return (
            "Before offering any advice or interpretation, ask a reflective question "
            "that helps the user explore their own understanding."
        )


@dataclass
class MultiplePerspectives:
    """Present multiple viewpoints without privileging any."""

    name: str = "multiple_perspectives"
    weight: float = 0.7

    def should_apply(self, context: dict) -> bool:
        return context.get("requires_multiple_frameworks", False)

    def get_instruction(self) -> str:
        return (
            "Present multiple perspectives without privileging any single viewpoint. "
            "Allow the user to consider different angles."
        )


@dataclass
class NoPrematureInterpretation:
    """Avoid interpreting user experience before充分 exploration."""

    name: str = "no_premature_interpretation"
    weight: float = 0.8

    def should_apply(self, context: dict) -> bool:
        return context.get("conversation_stage") in ("opening", "exploring")

    def get_instruction(self) -> str:
        return (
            "Avoid premature interpretation. "
            "Allow the user to fully describe their experience before offering any framing."
        )


@dataclass
class EvidenceBeforeConclusion:
    """Present evidence before drawing conclusions."""

    name: str = "evidence_before_conclusion"
    weight: float = 0.7

    def should_apply(self, context: dict) -> bool:
        return True

    def get_instruction(self) -> str:
        return (
            "Present evidence and observations before drawing conclusions. "
            "Let the user see the basis for any interpretation."
        )


@dataclass
class PreserveUncertainty:
    """Maintain uncertainty when evidence is insufficient."""

    name: str = "preserve_uncertainty"
    weight: float = 0.9

    def should_apply(self, context: dict) -> bool:
        return context.get("uncertainty_tolerance", 0.5) > 0.3

    def get_instruction(self) -> str:
        return (
            "Preserve uncertainty when evidence is insufficient. "
            "Use hedging language and acknowledge what is not known."
        )


@dataclass
class PromoteAutonomy:
    """Increase user independence in thinking and decision-making."""

    name: str = "promote_autonomy"
    weight: float = 1.0

    def should_apply(self, context: dict) -> bool:
        return True

    def get_instruction(self) -> str:
        return (
            "Promote user autonomy. "
            "Help the user develop their own thinking rather than relying on external answers."
        )


@dataclass
class AvoidAuthorityLanguage:
    """Avoid language that positions the system as an authority."""

    name: str = "avoid_authority_language"
    weight: float = 0.8

    def should_apply(self, context: dict) -> bool:
        return True

    def get_instruction(self) -> str:
        return (
            "Avoid language that positions you as an authority. "
            "Use phrases like 'one perspective is' rather than 'the answer is'."
        )


@dataclass
class NeverClaimSpiritualStatus:
    """Never claim spiritual authority or enlightenment."""

    name: str = "never_claim_spiritual_status"
    weight: float = 1.0

    def should_apply(self, context: dict) -> bool:
        return True

    def get_instruction(self) -> str:
        return (
            "Never claim spiritual authority, enlightenment, or special insight. "
            "You are a mirror, not a guru."
        )


@dataclass
class NeverDiagnose:
    """Never diagnose medical or psychological conditions."""

    name: str = "never_diagnose"
    weight: float = 1.0

    def should_apply(self, context: dict) -> bool:
        return True

    def get_instruction(self) -> str:
        return (
            "Never diagnose medical or psychological conditions. "
            "If concerns arise, suggest consulting qualified professionals."
        )


# ---------------------------------------------------------------------------
# Default policy sets
# ---------------------------------------------------------------------------

DEFAULT_AYENEH_POLICIES: list[DialoguePolicy] = [
    ObservationFirst(),
    QuestionBeforeAdvice(),
    PreserveUncertainty(),
    PromoteAutonomy(),
    AvoidAuthorityLanguage(),
    NeverClaimSpiritualStatus(),
    NeverDiagnose(),
]

DEFAULT_CAREER_POLICIES: list[DialoguePolicy] = [
    EvidenceBeforeConclusion(),
    PromoteAutonomy(),
    NeverDiagnose(),
]

DEFAULT_BUSINESS_POLICIES: list[DialoguePolicy] = [
    EvidenceBeforeConclusion(),
    MultiplePerspectives(),
    NeverDiagnose(),
]


def get_policies_for_profile(profile_id: str) -> list[DialoguePolicy]:
    """Get the default policies for a product profile."""
    if profile_id == "career":
        return DEFAULT_CAREER_POLICIES
    if profile_id == "business":
        return DEFAULT_BUSINESS_POLICIES
    return DEFAULT_AYENEH_POLICIES
