"""Golden test questions and expected properties for regression testing."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GoldenQuestion:
    """A golden test question with expected properties."""

    question: str
    # Expected behaviors (not exact wording)
    expected_retrieval: bool = True
    expected_graph_usage: bool = True
    expected_reasoning: bool = True
    expected_uncertainty: bool = True
    expected_provenance: bool = True
    expected_safety: bool = True
    # Expected content properties
    expected_keywords: list[str] = field(default_factory=list)
    expected_no_advice: bool = True
    expected_framework_attribution: bool = True
    # Description for reporting
    description: str = ""


GOLDEN_QUESTIONS: list[GoldenQuestion] = [
    GoldenQuestion(
        question="What is the relationship between ACT acceptance and Buddhist non-attachment?",
        description="Cross-tradition comparison: ACT and Buddhism",
        expected_keywords=["acceptance", "non-attachment", "similarities", "differences"],
        expected_framework_attribution=True,
    ),
    GoldenQuestion(
        question="How does Metzinger differ from Nisargadatta regarding the Self?",
        description="Philosophical comparison: Metzinger vs Nisargadatta",
        expected_keywords=["self", "Metzinger", "Nisargadatta"],
        expected_framework_attribution=True,
    ),
    GoldenQuestion(
        question="Compare Sapolsky's stress model with ACT.",
        description="Cross-domain comparison: neuroscience and psychology",
        expected_keywords=["stress", "ACT", "cortisol", "psychological flexibility"],
        expected_framework_attribution=True,
    ),
    GoldenQuestion(
        question="Compare Predictive Processing with Zen.",
        description="Cross-domain comparison: cognitive science and contemplative tradition",
        expected_keywords=["predictive", "processing", "Zen", "awareness"],
        expected_framework_attribution=True,
    ),
    GoldenQuestion(
        question="What do Wittgenstein and Ryle agree on?",
        description="Philosophical agreement analysis",
        expected_keywords=["Wittgenstein", "Ryle", "agree"],
        expected_framework_attribution=True,
    ),
    GoldenQuestion(
        question="Where do Damasio and Metzinger disagree?",
        description="Philosophical disagreement analysis",
        expected_keywords=["Damasio", "Metzinger", "disagree"],
        expected_framework_attribution=True,
    ),
    GoldenQuestion(
        question="What similarities exist between Tao Te Ching and Zen Mind Beginner's Mind?",
        description="Cross-tradition similarity analysis",
        expected_keywords=["Tao", "Zen", "similarities"],
        expected_framework_attribution=True,
    ),
    GoldenQuestion(
        question="Explain awareness across neuroscience, ACT and contemplative traditions.",
        description="Multi-framework awareness analysis",
        expected_keywords=["awareness", "neuroscience", "ACT", "contemplative"],
        expected_framework_attribution=True,
    ),
]
