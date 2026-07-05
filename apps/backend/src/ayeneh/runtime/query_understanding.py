"""Query Understanding Pipeline — per SPEC-21.

Transforms an unstructured user request into a deterministic semantic
representation. This module never answers questions — it only understands them.

Processing Phases (SPEC-21 §9):
1. Preparation
2. Language Detection
3. Intent Analysis
4. Concept Discovery
5. Canonical Resolution
6. Entity Recognition
7. Complexity Estimation
8. Capability Analysis
9. QueryAnalysis Publication
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from ayeneh.runtime.pipeline import QueryAnalysis

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Phase Output Types
# ---------------------------------------------------------------------------


@dataclass
class LanguageAnalysis:
    """Output of Language Detection phase (SPEC-21 §13)."""
    primary_language: str = "en"
    secondary_languages: list[str] = field(default_factory=list)
    confidence: float = 1.0
    detected_scripts: list[str] = field(default_factory=list)


@dataclass
class IntentAnalysis:
    """Output of Intent Analysis phase (SPEC-21 §14)."""
    primary_intent: str = "question"
    secondary_intents: list[str] = field(default_factory=list)
    confidence: float = 0.5
    question_type: str = "open_ended"


@dataclass
class ConceptDiscovery:
    """Output of Concept Discovery phase (SPEC-21 §16)."""
    resolved_concepts: list[dict[str, Any]] = field(default_factory=list)
    unresolved_terms: list[str] = field(default_factory=list)
    ambiguities: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class EntityDiscovery:
    """Output of Entity Recognition phase (SPEC-21 §20)."""
    entities: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ComplexityEstimate:
    """Output of Complexity Estimation phase (SPEC-21 §21)."""
    level: str = "medium"  # very_low, low, medium, high, very_high, extreme
    linguistic: float = 0.5
    conceptual: float = 0.5
    reasoning: float = 0.5
    retrieval: float = 0.5
    ambiguity: float = 0.0
    cross_book: bool = False
    cross_tradition: bool = False


@dataclass
class CapabilityAnalysis:
    """Output of Capability Analysis phase (SPEC-21 §22)."""
    required_capabilities: list[str] = field(default_factory=list)
    reasoning_depth: str = "single_source"
    retrieval_depth: str = "single_book"
    safety_level: str = "standard"


# ---------------------------------------------------------------------------
# Query Understanding Pipeline
# ---------------------------------------------------------------------------


class QueryUnderstandingPipeline:
    """SPEC-21 compliant Query Understanding pipeline.

    Each phase is a separate method. Phases execute in order.
    Final output: QueryAnalysis artifact.
    """

    def __init__(self) -> None:
        self._concept_resolver = None

    def _init(self) -> None:
        if self._concept_resolver is None:
            from ayeneh.runtime.query_concept_resolver import QueryConceptResolver
            self._concept_resolver = QueryConceptResolver()

    def execute(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]] | None = None,
        session_id: str = "",
    ) -> QueryAnalysis:
        """Execute the full Query Understanding pipeline.

        Returns exactly one immutable QueryAnalysis.
        """
        self._init()
        history = conversation_history or []

        # Phase 1: Preparation
        phase1 = self._phase_preparation(user_message, history)

        # Phase 2: Language Detection
        phase2 = self._phase_language_detection(user_message)

        # Phase 3: Intent Analysis
        phase3 = self._phase_intent_analysis(user_message, history)

        # Phase 4: Concept Discovery
        phase4 = self._phase_concept_discovery(user_message, phase2)

        # Phase 5: Canonical Resolution (handled inside concept discovery)

        # Phase 6: Entity Recognition
        phase6 = self._phase_entity_recognition(user_message, phase2)

        # Phase 7: Complexity Estimation
        phase7 = self._phase_complexity_estimation(
            phase3, phase4, phase6, history
        )

        # Phase 8: Capability Analysis
        phase8 = self._phase_capability_analysis(
            phase3, phase4, phase6, phase7
        )

        # Phase 9: QueryAnalysis Publication
        qa = self._phase_publication(
            user_message, phase2, phase3, phase4, phase6, phase7, phase8, session_id
        )

        return qa

    # ------------------------------------------------------------------
    # Phase 1: Preparation (SPEC-21 §10)
    # ------------------------------------------------------------------

    def _phase_preparation(
        self, user_message: str, history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Prepare deterministic analysis. No semantic processing."""
        return {
            "frozen_message": user_message,
            "history_length": len(history),
            "message_length": len(user_message.split()),
        }

    # ------------------------------------------------------------------
    # Phase 2: Language Detection (SPEC-21 §13)
    # ------------------------------------------------------------------

    def _phase_language_detection(self, text: str) -> LanguageAnalysis:
        """Detect every language in the request."""
        persian_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F')
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        english_words = sum(1 for w in text.lower().split() if w.isascii() and len(w) > 2)

        primary = "en"
        secondary = []
        confidence = 1.0

        if persian_chars > len(text) * 0.1:
            primary = "fa"
            if english_words > 2:
                secondary.append("en")
        elif english_words > 2 and persian_chars == 0:
            primary = "en"
        elif arabic_chars > len(text) * 0.1:
            primary = "ar"

        scripts = []
        if persian_chars > 0:
            scripts.append("Persian")
        if english_words > 0:
            scripts.append("Latin")
        if arabic_chars > 0 and persian_chars == 0:
            scripts.append("Arabic")

        return LanguageAnalysis(
            primary_language=primary,
            secondary_languages=secondary,
            confidence=confidence,
            detected_scripts=scripts,
        )

    # ------------------------------------------------------------------
    # Phase 3: Intent Analysis (SPEC-21 §14)
    # ------------------------------------------------------------------

    def _phase_intent_analysis(
        self, text: str, history: list[dict[str, Any]]
    ) -> IntentAnalysis:
        """Determine what the user is trying to accomplish."""
        text_lower = text.lower()

        # Intent detection with priority ordering
        intent_patterns = {
            "comparison": ["compared", "compare", "تفاوت", "فرق", "vs", "versus", "اختلاف", "متفاوت", "similar", "مشابه", "همان"],
            "definition": ["what is", "چیست", "تعریف", "define", "explain", "به چه معنا", "یعنی چه", "چه مفهوم"],
            "methodology": ["how", "چگونه", "نحوه", "way", "method", "روش", "چطور"],
            "relationship": ["relationship", "ارتباط", "relate", "connect", "اتصال", "پیوند", "سازگار"],
            "critique": ["critique", "criticize", "نقد", "نقد کردن", "weakness", "ضعف"],
            "summary": ["summary", "summarize", "خلاصه", "خلاصه کن", "overview"],
            "recommendation": ["advice", "should", "recommend", "توصیه", "باید", "پیشنهاد"],
            "explanation": ["explain", "توضیح", "چرا", "why", "because"],
            "exploration": ["explore", "کشف", "جستجو", "discover"],
        }

        primary_intent = "question"
        for intent, keywords in intent_patterns.items():
            if any(kw in text_lower for kw in keywords):
                primary_intent = intent
                break

        # Question type classification (SPEC-21 §15)
        question_type = "open_ended"
        if primary_intent == "comparison":
            question_type = "comparative"
        elif primary_intent == "definition":
            question_type = "explanatory"
        elif primary_intent == "methodology":
            question_type = "procedural"
        elif primary_intent == "critique":
            question_type = "evaluative"
        elif "?" in text or "؟" in text:
            question_type = "binary" if any(w in text_lower for w in ["آیا", "is it", "does", "can"]) else "open_ended"

        return IntentAnalysis(
            primary_intent=primary_intent,
            confidence=0.8,
            question_type=question_type,
        )

    # ------------------------------------------------------------------
    # Phase 4: Concept Discovery (SPEC-21 §16)
    # ------------------------------------------------------------------

    def _phase_concept_discovery(
        self, text: str, lang: LanguageAnalysis
    ) -> ConceptDiscovery:
        """Extract concept candidates from the user message."""
        resolution = self._concept_resolver.resolve(text, language=lang.primary_language)

        return ConceptDiscovery(
            resolved_concepts=[{"canonical": c.canonical, "confidence": c.confidence, "source": c.source} for c in resolution.resolved_concepts],
            unresolved_terms=resolution.unresolved_terms,
            ambiguities=[{"a": a.term_a, "b": a.term_b, "similarity": a.similarity} for a in resolution.ambiguities],
            confidence=resolution.concept_confidence,
        )

    # ------------------------------------------------------------------
    # Phase 6: Entity Recognition (SPEC-21 §20)
    # ------------------------------------------------------------------

    def _phase_entity_recognition(
        self, text: str, lang: LanguageAnalysis
    ) -> EntityDiscovery:
        """Identify named entities independently from concepts."""
        resolution = self._concept_resolver.resolve(text, language=lang.primary_language)

        return EntityDiscovery(
            entities=[{"name": e.name, "type": e.entity_type, "confidence": e.confidence} for e in resolution.resolved_entities],
            confidence=resolution.entity_confidence,
        )

    # ------------------------------------------------------------------
    # Phase 7: Complexity Estimation (SPEC-21 §21)
    # ------------------------------------------------------------------

    def _phase_complexity_estimation(
        self,
        intent: IntentAnalysis,
        concepts: ConceptDiscovery,
        entities: EntityDiscovery,
        history: list[dict[str, Any]],
    ) -> ComplexityEstimate:
        """Estimate computational complexity."""
        num_concepts = len(concepts.resolved_concepts)
        num_entities = len(entities.entities)
        num_ambiguities = len(concepts.ambiguities)
        has_history = len(history) > 0

        # Linguistic complexity
        linguistic = 0.3
        if num_entities > 2:
            linguistic += 0.2

        # Conceptual complexity
        conceptual = min(1.0, num_concepts * 0.15 + num_ambiguities * 0.2)

        # Reasoning complexity
        reasoning = 0.3
        if intent.primary_intent in ("comparison", "critique", "relationship"):
            reasoning += 0.3
        if num_entities >= 2:
            reasoning += 0.2

        # Retrieval complexity
        retrieval = 0.3
        if num_concepts >= 3:
            retrieval += 0.2
        if num_entities >= 2:
            retrieval += 0.2

        # Cross-book/cross-tradition detection
        cross_book = num_entities >= 2 or intent.primary_intent == "comparison"
        cross_tradition = any(e.get("type") == "tradition" for e in entities.entities)

        # Overall level
        overall = (linguistic + conceptual + reasoning + retrieval) / 4
        if overall < 0.2:
            level = "very_low"
        elif overall < 0.4:
            level = "low"
        elif overall < 0.6:
            level = "medium"
        elif overall < 0.8:
            level = "high"
        else:
            level = "very_high"

        return ComplexityEstimate(
            level=level,
            linguistic=linguistic,
            conceptual=conceptual,
            reasoning=reasoning,
            retrieval=retrieval,
            ambiguity=num_ambiguities * 0.2,
            cross_book=cross_book,
            cross_tradition=cross_tradition,
        )

    # ------------------------------------------------------------------
    # Phase 8: Capability Analysis (SPEC-21 §22)
    # ------------------------------------------------------------------

    def _phase_capability_analysis(
        self,
        intent: IntentAnalysis,
        concepts: ConceptDiscovery,
        entities: EntityDiscovery,
        complexity: ComplexityEstimate,
    ) -> CapabilityAnalysis:
        """Derive Runtime capability requirements."""
        capabilities = ["intent_classification", "concept_resolution", "safety_validation"]

        # Add capabilities based on intent
        if intent.primary_intent in ("comparison", "critique", "relationship"):
            capabilities.append("cross_book_reasoning")
        if intent.primary_intent in ("definition", "explanation"):
            capabilities.append("summarization")
        if intent.primary_intent == "methodology":
            capabilities.append("citation_generation")

        # Add capabilities based on entities
        if len(entities.entities) >= 2:
            capabilities.append("cross_book_reasoning")
        if any(e.get("type") == "tradition" for e in entities.entities):
            capabilities.append("cross_tradition_comparison")

        # Add capabilities based on complexity
        if complexity.level in ("high", "very_high"):
            capabilities.append("long_context")
            capabilities.append("streaming")

        # Determine reasoning depth
        reasoning_depth = "single_source"
        if complexity.cross_book:
            reasoning_depth = "cross_book"
        if complexity.cross_tradition:
            reasoning_depth = "cross_tradition"

        # Determine retrieval depth
        retrieval_depth = "single_book"
        if complexity.cross_book:
            retrieval_depth = "cross_book"
        if complexity.cross_tradition:
            retrieval_depth = "cross_tradition"

        # Safety level
        safety_level = "standard"
        if complexity.level in ("high", "very_high"):
            safety_level = "elevated"

        return CapabilityAnalysis(
            required_capabilities=list(set(capabilities)),
            reasoning_depth=reasoning_depth,
            retrieval_depth=retrieval_depth,
            safety_level=safety_level,
        )

    # ------------------------------------------------------------------
    # Phase 9: QueryAnalysis Publication (SPEC-21 §23)
    # ------------------------------------------------------------------

    def _phase_publication(
        self,
        user_message: str,
        lang: LanguageAnalysis,
        intent: IntentAnalysis,
        concepts: ConceptDiscovery,
        entities: EntityDiscovery,
        complexity: ComplexityEstimate,
        capabilities: CapabilityAnalysis,
        session_id: str,
    ) -> QueryAnalysis:
        """Publish exactly one immutable QueryAnalysis."""
        qa = QueryAnalysis(
            query_length=len(user_message.split()),
        )

        # Language
        qa.languages = [lang.primary_language] + lang.secondary_languages

        # Intent
        qa.intent = intent.primary_intent
        qa.question_type = intent.question_type
        qa.expected_answer = intent.primary_intent

        # Concepts
        qa.concepts = [c["canonical"] for c in concepts.resolved_concepts]
        qa.resolved_concepts = concepts.resolved_concepts
        qa.unresolved_terms = concepts.unresolved_terms
        qa.ambiguities = concepts.ambiguities
        qa.concept_confidence = concepts.confidence

        # Entities
        qa.entities = [e["name"] for e in entities.entities]
        qa.resolved_entities = entities.entities
        qa.entity_confidence = entities.confidence

        # Complexity
        qa.complexity = complexity.level

        # Scope
        if complexity.cross_book:
            qa.scope = "cross_book"
        elif complexity.cross_tradition:
            qa.scope = "cross_tradition"
        else:
            qa.scope = "single_book"

        # Reasoning
        qa.required_reasoning = capabilities.reasoning_depth
        qa.requires_interpretation = intent.primary_intent in ("definition", "explanation", "comparison")
        qa.requires_epistemic_safety = True
        qa.requires_graph_reasoning = complexity.cross_book or complexity.cross_tradition or intent.primary_intent in ("comparison", "critique")

        # Topics (from concepts)
        qa.topics = list(set(c["canonical"].lower() for c in concepts.resolved_concepts if c["canonical"] in ("Self", "Awareness", "Meditation", "Consciousness", "Fana", "Non-self")))

        return qa
