"""Epistemic Analyzer — single owner of all epistemic interpretation.

This subsystem understands the epistemic nature of user requests.
It does NOT perform retrieval, rank knowledge, or generate responses.
It produces a structured EpistemicQueryAnalysis consumed by other subsystems.

Design Principles:
- The analyzer owns all epistemic interpretation
- RetrievalService must never infer domains
- ReasoningEngine must never infer epistemic intent
- PromptComposer must never infer epistemic intent
- Only EpistemicAnalyzer performs this task
"""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EpistemicIntent(StrEnum):
    """Types of epistemic intent in user queries."""

    QUESTION = "question"
    REFLECTION = "reflection"
    DECISION = "decision"
    SELF_OBSERVATION = "self_observation"
    LEARNING = "learning"
    COMPARISON = "comparison"
    MEANING = "meaning"
    PRACTICE = "practice"


class EpistemicSignal(StrEnum):
    """Signals that indicate epistemic requirements."""

    SCIENTIFIC = "scientific"
    CLINICAL = "clinical"
    PHILOSOPHICAL = "philosophical"
    HISTORICAL = "historical"
    CONTEMPLATIVE = "contemplative"
    ETHICAL = "ethical"
    BEHAVIORAL = "behavioral"
    EXPERIENTIAL = "experiential"


class EpistemicFramework(StrEnum):
    """Epistemological frameworks that may be relevant."""

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


class EvidenceType(StrEnum):
    """Types of evidence that may be expected."""

    EMPIRICAL = "empirical"
    PHENOMENOLOGICAL = "phenomenological"
    LOGICAL = "logical"
    CONTEMPLATIVE = "contemplative"
    TRADITIONAL = "traditional"
    ANECDOTAL = "anecdotal"


class ClaimType(StrEnum):
    """Types of claims the query implies."""

    FACTUAL = "factual"
    INTERPRETIVE = "interpretive"
    NORMATIVE = "normative"
    DESCRIPTIVE = "descriptive"
    PRESCRIPTIVE = "prescriptive"
    ANALOGICAL = "analogical"
    SPECULATIVE = "speculative"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class EpistemicIntentResult:
    """Detected intent with confidence."""

    intent: EpistemicIntent
    confidence: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class EpistemicSignalResult:
    """Detected signal with confidence."""

    signal: EpistemicSignal
    confidence: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class EpistemicFrameworkResult:
    """Inferred framework with confidence."""

    framework: EpistemicFramework
    confidence: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class AnalysisExplanation:
    """Explanation of how the analysis was performed."""

    stages_completed: list[str] = field(default_factory=list)
    primary_signals: list[str] = field(default_factory=list)
    inference_reasoning: list[str] = field(default_factory=list)
    confidence_factors: list[str] = field(default_factory=list)


@dataclass
class EpistemicQueryAnalysis:
    """Complete epistemic interpretation of a user request.

    This is the single source of truth for epistemic properties of a query.
    All downstream subsystems consume this object instead of inferring themselves.
    """

    # Query metadata
    query: str = ""
    analysis_version: str = "1.0.0"

    # Intent
    primary_intent: EpistemicIntent = EpistemicIntent.QUESTION
    intent_confidence: float = 0.5
    alternative_intents: list[EpistemicIntentResult] = field(default_factory=list)

    # Domains
    primary_domains: list[str] = field(default_factory=list)
    secondary_domains: list[str] = field(default_factory=list)

    # Frameworks
    candidate_frameworks: list[EpistemicFrameworkResult] = field(default_factory=list)

    # Reasoning
    reasoning_style: str = "deductive"
    expected_evidence_level: str = "philosophical"

    # Evidence
    preferred_sources: list[str] = field(default_factory=list)
    discouraged_sources: list[str] = field(default_factory=list)

    # Claim type
    claim_type: ClaimType = ClaimType.INTERPRETIVE

    # Contexts
    applicable_contexts: list[str] = field(default_factory=list)
    excluded_contexts: list[str] = field(default_factory=list)

    # Requirements
    uncertainty_tolerance: float = 0.5
    requires_multiple_frameworks: bool = False
    requires_cross_framework_reasoning: bool = False
    requires_uncertainty_statement: bool = False
    requires_citations: bool = False
    requires_reflective_dialogue: bool = False
    requires_goal_context: bool = False
    requires_memory_context: bool = False
    requires_knowledge_context: bool = False

    # Confidence
    confidence: float = 0.5

    # Explanation
    analysis_explanation: AnalysisExplanation = field(default_factory=AnalysisExplanation)


# ---------------------------------------------------------------------------
# Protocol / Interface
# ---------------------------------------------------------------------------


@runtime_checkable
class EpistemicAnalysisEngine(Protocol):
    """Protocol for interchangeable epistemic analysis engines.

    Implementations must work without LLM (rule-based) or with LLM.
    The architecture allows LLMEpistemicAnalyzer to be added later
    without changing any consumer.
    """

    def analyze(self, query: str, context: dict | None = None) -> EpistemicQueryAnalysis:
        """Analyze a user query and return structured epistemic interpretation."""
        ...


# ---------------------------------------------------------------------------
# Rule-Based Analyzer (Default Implementation)
# ---------------------------------------------------------------------------


class RuleBasedEpistemicAnalyzer:
    """Default epistemic analyzer using rule-based inference.

    Works without any LLM. Produces structured interpretations
    that downstream systems consume.
    """

    def analyze(self, query: str, context: dict | None = None) -> EpistemicQueryAnalysis:
        """Analyze a user query and return structured epistemic interpretation."""
        analysis = EpistemicQueryAnalysis(query=query)
        ctx = context or {}

        # Stage 1: Intent understanding
        intents = self._detect_intents(query)
        if intents:
            analysis.primary_intent = intents[0].intent
            analysis.intent_confidence = intents[0].confidence
            analysis.alternative_intents = intents[1:]

        # Stage 2: Epistemic signal extraction
        signals = self._extract_signals(query)
        primary_signals = [s.signal for s in signals if s.confidence >= 0.5]
        analysis.analysis_explanation.primary_signals = [s.value for s in primary_signals]

        # Stage 3: Domain inference
        analysis.primary_domains, analysis.secondary_domains = self._infer_domains(query, signals)

        # Stage 4: Framework inference
        analysis.candidate_frameworks = self._infer_frameworks(query, signals)

        # Stage 5: Evidence expectation
        analysis.expected_evidence_level = self._infer_evidence_level(query, signals)
        analysis.preferred_sources, analysis.discouraged_sources = self._infer_sources(query, signals)

        # Stage 6: Claim type
        analysis.claim_type = self._infer_claim_type(query)

        # Stage 7: Reasoning style
        analysis.reasoning_style = self._infer_reasoning_style(query)

        # Stage 8: Context inference
        analysis.applicable_contexts, analysis.excluded_contexts = self._infer_contexts(query, signals)

        # Stage 9: Requirements
        analysis.uncertainty_tolerance = self._infer_uncertainty_tolerance(query, signals)
        analysis.requires_multiple_frameworks = len(analysis.candidate_frameworks) > 1
        analysis.requires_cross_framework_reasoning = self._detect_cross_framework(query, signals)
        analysis.requires_uncertainty_statement = self._detect_uncertainty_need(query)
        analysis.requires_citations = self._detect_citation_need(query, signals)
        analysis.requires_reflective_dialogue = self._detect_reflective_need(query)
        analysis.requires_goal_context = self._detect_goal_context_need(query)
        analysis.requires_memory_context = self._detect_memory_context_need(query)
        analysis.requires_knowledge_context = self._detect_knowledge_context_need(query)

        # Stage 10: Overall confidence
        analysis.confidence = self._compute_confidence(analysis)

        # Explanation
        analysis.analysis_explanation.stages_completed = [
            "intent", "signals", "domains", "frameworks",
            "evidence", "claim_type", "reasoning_style",
            "contexts", "requirements", "confidence",
        ]
        analysis.analysis_explanation.inference_reasoning = self._build_reasoning(analysis)

        return analysis

    # ------------------------------------------------------------------
    # Stage 1: Intent detection
    # ------------------------------------------------------------------

    def _detect_intents(self, query: str) -> list[EpistemicIntentResult]:
        """Detect epistemic intent from the query."""
        results: list[EpistemicIntentResult] = []
        q = query.lower()

        # Question patterns
        if any(q.startswith(w) for w in ["what", "why", "how", "when", "where", "who", "is ", "are ", "can ", "do ", "does "]):
            results.append(EpistemicIntentResult(
                intent=EpistemicIntent.QUESTION, confidence=0.9,
                evidence=["query starts with question word"],
            ))

        # Reflection patterns
        if any(w in q for w in ["i notice", "i feel", "i think", "i realize", "reflecting on", "looking back"]):
            results.append(EpistemicIntentResult(
                intent=EpistemicIntent.REFLECTION, confidence=0.8,
                evidence=["contains reflection markers"],
            ))

        # Decision patterns
        if any(w in q for w in ["should i", "which", "choose", "decide", "option", "better"]):
            results.append(EpistemicIntentResult(
                intent=EpistemicIntent.DECISION, confidence=0.8,
                evidence=["contains decision markers"],
            ))

        # Self-observation patterns
        if any(w in q for w in ["my pattern", "i keep", "always", "never", "habit", "tendency"]):
            results.append(EpistemicIntentResult(
                intent=EpistemicIntent.SELF_OBSERVATION, confidence=0.8,
                evidence=["contains self-observation markers"],
            ))

        # Learning patterns
        if any(w in q for w in ["explain", "teach", "learn", "understand", "concept", "theory"]):
            results.append(EpistemicIntentResult(
                intent=EpistemicIntent.LEARNING, confidence=0.7,
                evidence=["contains learning markers"],
            ))

        # Comparison patterns
        if any(w in q for w in ["compare", "versus", "vs", "difference", "similar", "better than"]):
            results.append(EpistemicIntentResult(
                intent=EpistemicIntent.COMPARISON, confidence=0.8,
                evidence=["contains comparison markers"],
            ))

        # Meaning patterns
        if any(w in q for w in ["meaning", "purpose", "significance", "value", "matter"]):
            results.append(EpistemicIntentResult(
                intent=EpistemicIntent.MEANING, confidence=0.7,
                evidence=["contains meaning markers"],
            ))

        # Practice patterns
        if any(w in q for w in ["practice", "exercise", "technique", "method", "step", "how to"]):
            results.append(EpistemicIntentResult(
                intent=EpistemicIntent.PRACTICE, confidence=0.7,
                evidence=["contains practice markers"],
            ))

        # Sort by confidence
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Stage 2: Signal extraction
    # ------------------------------------------------------------------

    def _extract_signals(self, query: str) -> list[EpistemicSignalResult]:
        """Extract epistemic signals from the query."""
        results: list[EpistemicSignalResult] = []
        q = query.lower()

        signal_patterns: dict[EpistemicSignal, list[str]] = {
            EpistemicSignal.SCIENTIFIC: [
                "research", "study", "data", "evidence", "experiment", "hypothesis",
                "neuroscience", "brain", "empirical", "statistical",
            ],
            EpistemicSignal.CLINICAL: [
                "therapy", "treatment", "diagnosis", "clinical", "disorder",
                "anxiety", "depression", "symptom", "intervention",
            ],
            EpistemicSignal.PHILOSOPHICAL: [
                "truth", "reality", "existence", "meaning", "ethics", "logic",
                "metaphysics", "epistemology", "ontology", "consciousness",
                "being", "essence", "virtue", "justice",
            ],
            EpistemicSignal.HISTORICAL: [
                "history", "historical", "century", "ancient", "tradition",
                "evolution", "development", "era", "period",
            ],
            EpistemicSignal.CONTEMPLATIVE: [
                "meditation", "contemplation", "prayer", "spiritual",
                "mysticism", "sufi", "zen", "awareness", "presence",
                "inner", "silence", "stillness",
            ],
            EpistemicSignal.ETHICAL: [
                "right", "wrong", "moral", "ethical", "virtue", "duty",
                "responsibility", "justice", "fairness",
            ],
            EpistemicSignal.BEHAVIORAL: [
                "behavior", "habit", "pattern", "action", "response",
                "reaction", "tendency", "choice", "decision",
            ],
            EpistemicSignal.EXPERIENTIAL: [
                "experience", "lived", "personal", "felt", "felt sense",
                "phenomenology", "subjective", "first-person",
            ],
        }

        for signal, keywords in signal_patterns.items():
            matches = [kw for kw in keywords if kw in q]
            if matches:
                confidence = min(1.0, 0.4 + len(matches) * 0.2)
                results.append(EpistemicSignalResult(
                    signal=signal, confidence=confidence,
                    evidence=[f"matched: {', '.join(matches[:3])}"],
                ))

        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Stage 3: Domain inference
    # ------------------------------------------------------------------

    def _infer_domains(
        self,
        query: str,
        signals: list[EpistemicSignalResult],
    ) -> tuple[list[str], list[str]]:
        """Infer primary and secondary domains."""
        signal_domain_map: dict[EpistemicSignal, str] = {
            EpistemicSignal.SCIENTIFIC: "science",
            EpistemicSignal.CLINICAL: "psychology",
            EpistemicSignal.PHILOSOPHICAL: "philosophy",
            EpistemicSignal.HISTORICAL: "history",
            EpistemicSignal.CONTEMPLATIVE: "spirituality",
            EpistemicSignal.ETHICAL: "philosophy",
            EpistemicSignal.BEHAVIORAL: "psychology",
            EpistemicSignal.EXPERIENTIAL: "phenomenology",
        }

        primary: list[str] = []
        secondary: list[str] = []

        for sig_result in signals:
            domain = signal_domain_map.get(sig_result.signal)
            if domain and domain not in primary and domain not in secondary:
                if sig_result.confidence >= 0.6:
                    primary.append(domain)
                elif sig_result.confidence >= 0.4:
                    secondary.append(domain)

        # Fallback: if no domains inferred, default to philosophy
        if not primary and not secondary:
            primary.append("philosophy")

        return primary, secondary

    # ------------------------------------------------------------------
    # Stage 4: Framework inference
    # ------------------------------------------------------------------

    def _infer_frameworks(
        self,
        query: str,
        signals: list[EpistemicSignalResult],
    ) -> list[EpistemicFrameworkResult]:
        """Infer likely epistemological frameworks."""
        results: list[EpistemicFrameworkResult] = []
        q = query.lower()

        framework_signals: dict[EpistemicFramework, list[EpistemicSignal]] = {
            EpistemicFramework.RATIONALIST: [EpistemicSignal.PHILOSOPHICAL, EpistemicSignal.ETHICAL],
            EpistemicFramework.EMPIRICIST: [EpistemicSignal.SCIENTIFIC, EpistemicSignal.CLINICAL],
            EpistemicFramework.PHENOMENOLOGICAL: [EpistemicSignal.EXPERIENTIAL, EpistemicSignal.CONTEMPLATIVE],
            EpistemicFramework.HERMENEUTIC: [EpistemicSignal.PHILOSOPHICAL, EpistemicSignal.HISTORICAL],
            EpistemicFramework.DIALECTICAL: [EpistemicSignal.PHILOSOPHICAL, EpistemicSignal.BEHAVIORAL],
            EpistemicFramework.PRAGMATIST: [EpistemicSignal.BEHAVIORAL, EpistemicSignal.CLINICAL],
            EpistemicFramework.INTUITIONIST: [EpistemicSignal.CONTEMPLATIVE, EpistemicSignal.EXPERIENTIAL],
            EpistemicFramework.NATURALISTIC: [EpistemicSignal.SCIENTIFIC, EpistemicSignal.BEHAVIORAL],
            EpistemicFramework.CONSTRUCTIVIST: [EpistemicSignal.BEHAVIORAL, EpistemicSignal.EXPERIENTIAL],
            EpistemicFramework.CRITICAL: [EpistemicSignal.ETHICAL, EpistemicSignal.HISTORICAL],
        }

        # Count signal matches for each framework
        framework_scores: dict[EpistemicFramework, float] = {}
        signal_types = {s.signal for s in signals}

        for framework, required_signals in framework_signals.items():
            matches = len(signal_types & set(required_signals))
            if matches > 0:
                framework_scores[framework] = matches * 0.3

        # Add keyword-based boosts
        framework_keywords: dict[EpistemicFramework, list[str]] = {
            EpistemicFramework.RATIONALIST: ["reason", "logic", "argument", "proof"],
            EpistemicFramework.EMPIRICIST: ["evidence", "data", "observation", "measurement"],
            EpistemicFramework.PHENOMENOLOGICAL: ["experience", "lived", "felt", "phenomenon"],
            EpistemicFramework.HERMENEUTIC: ["interpret", "meaning", "text", "understand"],
            EpistemicFramework.DIALECTICAL: ["contradiction", "tension", "thesis", "antithesis"],
            EpistemicFramework.PRAGMATIST: ["practical", "work", "action", "consequence"],
            EpistemicFramework.INTUITIONIST: ["intuit", "inner", "felt sense", "direct"],
            EpistemicFramework.NATURALISTIC: ["nature", "natural", "evolution", "biology"],
            EpistemicFramework.CONSTRUCTIVIST: ["construct", "build", "create", "social"],
            EpistemicFramework.CRITICAL: ["power", "critique", "justice", "inequality"],
        }

        for framework, keywords in framework_keywords.items():
            if any(kw in q for kw in keywords):
                framework_scores[framework] = framework_scores.get(framework, 0) + 0.4

        # Sort and return top frameworks
        sorted_frameworks = sorted(framework_scores.items(), key=lambda x: x[1], reverse=True)

        for framework, score in sorted_frameworks[:3]:
            if score >= 0.3:
                results.append(EpistemicFrameworkResult(
                    framework=framework,
                    confidence=min(0.9, score),
                    evidence=[f"signal and keyword analysis"],
                ))

        return results

    # ------------------------------------------------------------------
    # Stage 5: Evidence level
    # ------------------------------------------------------------------

    def _infer_evidence_level(
        self,
        query: str,
        signals: list[EpistemicSignalResult],
    ) -> str:
        """Infer the expected evidence level."""
        signal_evidence_map: dict[EpistemicSignal, str] = {
            EpistemicSignal.SCIENTIFIC: "empirical",
            EpistemicSignal.CLINICAL: "empirical",
            EpistemicSignal.PHILOSOPHICAL: "philosophical",
            EpistemicSignal.HISTORICAL: "traditional",
            EpistemicSignal.CONTEMPLATIVE: "contemplative",
            EpistemicSignal.ETHICAL: "philosophical",
            EpistemicSignal.BEHAVIORAL: "empirical",
            EpistemicSignal.EXPERIENTIAL: "phenomenological",
        }

        # Find highest confidence signal
        for sig_result in signals:
            if sig_result.confidence >= 0.5:
                level = signal_evidence_map.get(sig_result.signal)
                if level:
                    return level

        return "philosophical"

    def _infer_sources(
        self,
        query: str,
        signals: list[EpistemicSignalResult],
    ) -> tuple[list[str], list[str]]:
        """Infer preferred and discouraged sources."""
        preferred: list[str] = []
        discouraged: list[str] = []

        signal_source_map: dict[EpistemicSignal, tuple[list[str], list[str]]] = {
            EpistemicSignal.SCIENTIFIC: (
                ["peer_reviewed", "empirical_studies"],
                ["anecdotal", "traditional"],
            ),
            EpistemicSignal.CLINICAL: (
                ["clinical_guidelines", "research"],
                ["spiritual", "folklore"],
            ),
            EpistemicSignal.PHILOSOPHICAL: (
                ["primary_texts", "commentary"],
                ["empirical_studies"],
            ),
            EpistemicSignal.CONTEMPLATIVE: (
                ["contemplative_traditions", "experiential"],
                ["purely_empirical"],
            ),
        }

        for sig_result in signals:
            if sig_result.confidence >= 0.5:
                p, d = signal_source_map.get(sig_result.signal, ([], []))
                preferred.extend(p)
                discouraged.extend(d)

        return list(set(preferred)), list(set(discouraged))

    # ------------------------------------------------------------------
    # Stage 6: Claim type
    # ------------------------------------------------------------------

    def _infer_claim_type(self, query: str) -> ClaimType:
        """Infer the type of claim the query implies."""
        q = query.lower()

        if any(q.startswith(w) for w in ["what is", "what are", "define", "explain"]):
            return ClaimType.DESCRIPTIVE
        if any(w in q for w in ["should", "ought", "right", "wrong", "moral"]):
            return ClaimType.NORMATIVE
        if any(w in q for w in ["how to", "step", "method", "technique"]):
            return ClaimType.PRESCRIPTIVE
        if any(w in q for w in ["because", "therefore", "cause", "reason"]):
            return ClaimType.FACTUAL
        if any(w in q for w in ["like", "as if", "similar", "metaphor"]):
            return ClaimType.ANALOGICAL
        if any(w in q for w in ["might", "possibly", "perhaps", "hypothesis"]):
            return ClaimType.SPECULATIVE
        if any(w in q for w in ["meaning", "interpret", "understand", "significance"]):
            return ClaimType.INTERPRETIVE
        return ClaimType.INTERPRETIVE

    # ------------------------------------------------------------------
    # Stage 7: Reasoning style
    # ------------------------------------------------------------------

    def _infer_reasoning_style(self, query: str) -> str:
        """Infer the required reasoning style."""
        q = query.lower()
        if any(w in q for w in ["why", "cause", "reason", "because", "therefore"]):
            return "deductive"
        if any(w in q for w in ["pattern", "trend", "observe", "notice", "usually"]):
            return "inductive"
        if any(w in q for w in ["hypothesis", "suggest", "might", "possibly", "guess"]):
            return "abductive"
        if any(w in q for w in ["similar", "like", "as if", "metaphor", "compare"]):
            return "analogical"
        if any(w in q for w in ["contradiction", "tension", "paradox", "dialectic"]):
            return "dialectical"
        if any(w in q for w in ["feel", "sense", "intuit", "inner", "contemplat"]):
            return "contemplative"
        if any(w in q for w in ["story", "narrative", "once", "journey", "experience"]):
            return "narrative"
        return "deductive"

    # ------------------------------------------------------------------
    # Stage 8: Context inference
    # ------------------------------------------------------------------

    def _infer_contexts(
        self,
        query: str,
        signals: list[EpistemicSignalResult],
    ) -> tuple[list[str], list[str]]:
        """Infer applicable and excluded contexts."""
        applicable: list[str] = []
        excluded: list[str] = []
        q = query.lower()

        signal_context_map: dict[EpistemicSignal, tuple[list[str], list[str]]] = {
            EpistemicSignal.SCIENTIFIC: (
                ["research", "academic"],
                ["spiritual practice"],
            ),
            EpistemicSignal.CLINICAL: (
                ["therapy", "clinical practice"],
                ["spiritual guidance"],
            ),
            EpistemicSignal.PHILOSOPHICAL: (
                ["inquiry", "discussion", "study"],
                ["medical treatment"],
            ),
            EpistemicSignal.CONTEMPLATIVE: (
                ["meditation", "spiritual practice"],
                ["clinical diagnosis"],
            ),
        }

        for sig_result in signals:
            if sig_result.confidence >= 0.5:
                a, e = signal_context_map.get(sig_result.signal, ([], []))
                applicable.extend(a)
                excluded.extend(e)

        return list(set(applicable)), list(set(excluded))

    # ------------------------------------------------------------------
    # Stage 9: Requirements
    # ------------------------------------------------------------------

    def _infer_uncertainty_tolerance(
        self,
        query: str,
        signals: list[EpistemicSignalResult],
    ) -> float:
        """Infer how much uncertainty is acceptable."""
        q = query.lower()

        if any(w in q for w in ["uncertain", "doubt", "maybe", "possibly", "not sure"]):
            return 0.8
        if any(w in q for w in ["paradox", "contradiction", "complexity", "nuance"]):
            return 0.9
        if any(w in q for w in ["certain", "definitely", "sure", "prove", "fact"]):
            return 0.2
        return 0.5

    def _detect_cross_framework(self, query: str, signals: list[EpistemicSignalResult]) -> bool:
        """Detect if cross-framework reasoning is needed."""
        q = query.lower()
        if any(w in q for w in ["integrate", "combine", "both", "and", "multiple", "perspective"]):
            return True
        signal_types = {s.signal for s in signals}
        if len(signal_types) >= 3:
            return True
        return False

    def _detect_uncertainty_need(self, query: str) -> bool:
        """Detect if uncertainty statement is required."""
        q = query.lower()
        return any(w in q for w in [
            "uncertain", "doubt", "maybe", "possibly", "ambiguity",
            "complex", "nuance", "paradox",
        ])

    def _detect_citation_need(self, query: str, signals: list[EpistemicSignalResult]) -> bool:
        """Detect if citations are needed."""
        q = query.lower()
        if any(w in q for w in ["source", "reference", "cite", "according to", "study"]):
            return True
        for sig in signals:
            if sig.signal in (EpistemicSignal.SCIENTIFIC, EpistemicSignal.CLINICAL) and sig.confidence >= 0.5:
                return True
        return False

    def _detect_reflective_need(self, query: str) -> bool:
        """Detect if reflective dialogue is needed."""
        q = query.lower()
        return any(w in q for w in [
            "feel", "think", "notice", "observe", "reflect", "consider",
            "my pattern", "i keep", "always", "habit",
        ])

    def _detect_goal_context_need(self, query: str) -> bool:
        """Detect if goal context is needed."""
        q = query.lower()
        return any(w in q for w in [
            "goal", "aim", "target", "objective", "progress", "achieve",
        ])

    def _detect_memory_context_need(self, query: str) -> bool:
        """Detect if memory context is needed."""
        q = query.lower()
        return any(w in q for w in [
            "remember", "past", "before", "history", "previously", "already",
        ])

    def _detect_knowledge_context_need(self, query: str) -> bool:
        """Detect if knowledge context is needed."""
        q = query.lower()
        return any(w in q for w in [
            "book", "text", "source", "read", "learn", "teach", "explain",
        ])

    # ------------------------------------------------------------------
    # Stage 10: Confidence
    # ------------------------------------------------------------------

    def _compute_confidence(self, analysis: EpistemicQueryAnalysis) -> float:
        """Compute overall analysis confidence."""
        factors: list[float] = []

        # Intent confidence
        factors.append(analysis.intent_confidence)

        # Domain inference confidence
        if analysis.primary_domains:
            factors.append(0.7)
        else:
            factors.append(0.3)

        # Framework inference confidence
        if analysis.candidate_frameworks:
            factors.append(analysis.candidate_frameworks[0].confidence)
        else:
            factors.append(0.3)

        # Signal detection confidence
        if analysis.analysis_explanation.primary_signals:
            factors.append(0.7)
        else:
            factors.append(0.4)

        # Overall confidence is average of factors
        return sum(factors) / len(factors) if factors else 0.5

    # ------------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------------

    def _build_reasoning(self, analysis: EpistemicQueryAnalysis) -> list[str]:
        """Build human-readable reasoning for the analysis."""
        reasoning: list[str] = []

        reasoning.append(
            f"Detected primary intent: {analysis.primary_intent} "
            f"(confidence: {analysis.intent_confidence:.2f})"
        )

        if analysis.primary_domains:
            reasoning.append(
                f"Inferred primary domains: {', '.join(analysis.primary_domains)}"
            )

        if analysis.candidate_frameworks:
            fw_names = [f.framework.value for f in analysis.candidate_frameworks[:2]]
            reasoning.append(f"Candidate frameworks: {', '.join(fw_names)}")

        reasoning.append(f"Evidence level: {analysis.expected_evidence_level}")
        reasoning.append(f"Reasoning style: {analysis.reasoning_style}")

        if analysis.requires_multiple_frameworks:
            reasoning.append("Multiple frameworks required for this query")

        if analysis.requires_cross_framework_reasoning:
            reasoning.append("Cross-framework reasoning detected")

        return reasoning


# ---------------------------------------------------------------------------
# Main Analyzer (Orchestrator)
# ---------------------------------------------------------------------------


class EpistemicAnalyzer:
    """Single owner of all epistemic interpretation.

    Orchestrates the analysis pipeline using a pluggable engine.
    Consumers must use this class, never the engine directly.
    """

    def __init__(self, engine: EpistemicAnalysisEngine | None = None) -> None:
        self._engine = engine or RuleBasedEpistemicAnalyzer()

    def analyze(self, query: str, context: dict | None = None) -> EpistemicQueryAnalysis:
        """Analyze a user query and return structured epistemic interpretation."""
        return self._engine.analyze(query, context)

    def set_engine(self, engine: EpistemicAnalysisEngine) -> None:
        """Swap the analysis engine (e.g., from rule-based to LLM-based)."""
        self._engine = engine
