"""Epistemic enums — typed constants for knowledge source classification."""

from enum import StrEnum


class KnowledgeSource(StrEnum):
    """Origin type of a knowledge source."""

    BOOK = "book"
    ARTICLE = "article"
    LECTURE = "lecture"
    PAPER = "paper"
    INTERVIEW = "interview"
    EXPERIENCE = "experience"
    TRADITION = "tradition"
    REVELATION = "revelation"
    DIALOGUE = "dialogue"


class KnowledgeDomain(StrEnum):
    """Primary disciplinary domain of a knowledge source."""

    PHILOSOPHY = "philosophy"
    PSYCHOLOGY = "psychology"
    SPIRITUALITY = "spirituality"
    SCIENCE = "science"
    HISTORY = "history"
    LITERATURE = "literature"
    ARTS = "arts"
    SOCIAL_SCIENCE = "social_science"
    PRACTICAL = "practical"
    INTERDISCIPLINARY = "interdisciplinary"


class EvidenceLevel(StrEnum):
    """Strength and type of evidence a source provides."""

    EMPIRICAL = "empirical"
    ANECDOTAL = "anecdotal"
    THEORETICAL = "theoretical"
    PHILOSOPHICAL = "philosophical"
    TRADITIONAL = "traditional"
    EXPERIENTIAL = "experiential"
    CONSENSUS = "consensus"
    SPECULATIVE = "speculative"


class EpistemicFramework(StrEnum):
    """Epistemological framework the source operates within."""

    RATIONALIST = "rationalist"
    EMPIRICIST = "empiricist"
    PRAGMATIST = "pragmatist"
    PHENOMENOLOGICAL = "phenomenological"
    HERMENEUTIC = "hermeneutic"
    DIALECTICAL = "dialectical"
    INTUITIONIST = "intuitionist"
    NATURALISTIC = "naturalistic"
    CONSTRUCTIVIST = "constructivist"
    CRITICAL = "critical"


class KnowledgeAuthority(StrEnum):
    """Authority level of the source within its domain."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    COMMENTARY = "commentary"
    REFERENCE = "reference"
    CONTRARIAN = "contrarian"
    CORROBORATING = "corroborating"


class ClaimType(StrEnum):
    """Types of claims the source makes."""

    FACTUAL = "factual"
    INTERPRETIVE = "interpretive"
    NORMATIVE = "normative"
    DESCRIPTIVE = "descriptive"
    PRESCRIPTIVE = "prescriptive"
    ANALOGICAL = "analogical"
    SPECULATIVE = "speculative"


class ReasoningStyle(StrEnum):
    """Primary reasoning approach of the source."""

    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"
    DIALECTICAL = "dialectical"
    INTUITIVE = "intuitive"
    NARRATIVE = "narrative"
    CONTEMPLATIVE = "contemplative"
