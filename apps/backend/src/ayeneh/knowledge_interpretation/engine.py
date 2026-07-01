"""InterpretationEngine — single owner of interpretation generation."""

from __future__ import annotations

import time
from typing import Any

import structlog

from ayeneh.knowledge_interpretation.types import (
    ConfidenceLevel,
    CrossTraditionMapping,
    GraphReasoningResult,
    Interpretation,
    InterpretationCacheKey,
    InterpretationContext,
    InterpretationKind,
    InterpretationMetadata,
    InterpretationVersion,
    ModernMapping,
    SourceReference,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Abstract ports
# ---------------------------------------------------------------------------


class InterpretationStore:
    """Abstract persistence for interpretations."""

    async def save_interpretation(self, interpretation: Interpretation) -> Interpretation:
        raise NotImplementedError

    async def get_interpretation(self, interpretation_id: str) -> Interpretation | None:
        raise NotImplementedError

    async def get_interpretations_by_chunk(self, chunk_id: str) -> list[Interpretation]:
        raise NotImplementedError

    async def get_interpretations_by_chapter(self, chapter_id: str) -> list[Interpretation]:
        raise NotImplementedError

    async def get_interpretations_by_document(self, document_id: str) -> list[Interpretation]:
        raise NotImplementedError

    async def update_interpretation(self, interpretation: Interpretation) -> None:
        raise NotImplementedError


class InterpretationVersionStore:
    """Abstract persistence for interpretation versions."""

    async def save_version(self, version: InterpretationVersion) -> InterpretationVersion:
        raise NotImplementedError

    async def get_versions(self, interpretation_id: str) -> list[InterpretationVersion]:
        raise NotImplementedError


class EventPublisher:
    """Abstract event publishing interface."""

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Interpretation Generator
# ---------------------------------------------------------------------------


class InterpretationGenerator:
    """Generates interpretations from knowledge passages.

    Never modifies the original document.
    Interpretations are secondary artifacts.
    """

    def generate(
        self,
        context: InterpretationContext,
    ) -> Interpretation:
        """Generate an interpretation for a passage."""
        text = context.chunk_content
        text_lower = text.lower()

        # Build source reference
        source = SourceReference(
            document_id=context.document_id,
            book_id=context.book_id,
            chapter_id=context.chapter_id,
            chapter_title=context.chapter_title,
            chunk_id=context.chunk_id,
            topic_id=context.topic_id,
            original_text=text[:500],
        )

        # Generate practical insight
        practical_insight = self._generate_practical_insight(text, context)

        # Generate conceptual meaning
        conceptual_meaning = self._generate_conceptual_meaning(text, context)

        # Generate modern translation
        modern_translation = self._generate_modern_translation(text, context)

        # Generate framework-specific interpretations
        psychological = self._generate_psychological(text, context)
        neuroscience = self._generate_neuroscience(text, context)
        act = self._generate_act(text, context)
        analytical = self._generate_analytical(text, context)
        zen = self._generate_zen(text, context)
        khorasan = self._generate_khorasan(text, context)

        # Generate alternative interpretations
        alternatives = self._generate_alternatives(text, context)

        # Generate modern mappings
        mappings = self._generate_modern_mappings(text, context)

        # Generate cross-tradition mappings
        cross_mappings = self._generate_cross_tradition_mappings(text, context)

        # Generate provenance
        provenance = self._generate_provenance(text, context, source)

        # Compute decomposed confidence
        confidence_breakdown = self._compute_confidence_breakdown(text, context, provenance)
        confidence = confidence_breakdown.overall_confidence
        confidence_level = self._compute_confidence_level(confidence)

        # Generate limitations
        limitations = self._generate_limitations(text, context)

        # Generate uncertainties
        uncertainties = self._generate_uncertainties(text, context)

        return Interpretation(
            source=source,
            practical_insight=practical_insight,
            conceptual_meaning=conceptual_meaning,
            modern_translation=modern_translation,
            psychological_interpretation=psychological,
            neuroscience_interpretation=neuroscience,
            act_interpretation=act,
            analytical_philosophy_interpretation=analytical,
            zen_interpretation=zen,
            khorasan_mysticism_interpretation=khorasan,
            alternative_interpretations=alternatives,
            modern_mappings=mappings,
            cross_tradition_mappings=cross_mappings,
            provenance=provenance,
            confidence_breakdown=confidence_breakdown,
            confidence=confidence,
            confidence_level=confidence_level,
            limitations=limitations,
            uncertainties=uncertainties,
        )

    # ------------------------------------------------------------------
    # Content generation methods
    # ------------------------------------------------------------------

    def _generate_practical_insight(self, text: str, context: InterpretationContext) -> str:
        """Generate a practical insight from the passage."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["meditation", "contemplation", "practice"]):
            return "This passage suggests that regular practice of attentional focus may be beneficial for mental clarity."
        if any(w in text_lower for w in ["truth", "reality", "existence"]):
            return "This passage invites reflection on the nature of what we consider real or true."
        if any(w in text_lower for w in ["suffering", "pain", "difficulty"]):
            return "This passage acknowledges the reality of human suffering and suggests pathways through it."
        if any(w in text_lower for w in ["wisdom", "insight", "understanding"]):
            return "This passage points toward deeper understanding through careful observation."

        return "This passage offers a perspective worth considering in the context of personal reflection."

    def _generate_conceptual_meaning(self, text: str, context: InterpretationContext) -> str:
        """Generate conceptual meaning from the passage."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["consciousness", "awareness", "mind"]):
            return "The passage explores the nature of consciousness and awareness as fundamental aspects of human experience."
        if any(w in text_lower for w in ["self", "identity", "ego"]):
            return "The passage examines the construction and nature of self-identity."
        if any(w in text_lower for w in ["time", "impermanence", "change"]):
            return "The passage reflects on the nature of time and the inevitability of change."

        return "The passage presents a perspective on fundamental aspects of human experience."

    def _generate_modern_translation(self, text: str, context: InterpretationContext) -> str:
        """Generate a modern translation of the passage."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["dhikr", "remembrance", "repetition"]):
            return "The practice described may resemble repeated attentional redirection toward a focal point."
        if any(w in text_lower for w in ["fana", "annihilation", "ego-death"]):
            return "The concept described may relate to the dissolution of the sense of separate self."
        if any(w in text_lower for w in ["sabr", "patience", "endurance"]):
            return "The virtue described may involve maintaining equanimity through difficult experiences."

        return "The passage may be understood in contemporary terms as a reflection on human experience."

    def _generate_psychological(self, text: str, context: InterpretationContext) -> str:
        """Generate psychological interpretation."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["habit", "pattern", "behavior"]):
            return "From a psychological perspective, this may relate to behavioral patterns and cognitive habits."
        if any(w in text_lower for w in ["emotion", "feeling", "affect"]):
            return "This passage may be understood through the lens of emotional regulation and affective processing."
        if any(w in text_lower for w in ["anxiety", "fear", "worry"]):
            return "This may relate to anxiety management and cognitive reappraisal strategies."

        return "This passage may be relevant to psychological understanding of human cognition and behavior."

    def _generate_neuroscience(self, text: str, context: InterpretationContext) -> str:
        """Generate neuroscience interpretation."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["attention", "focus", "concentration"]):
            return "Neuroscience research suggests this may relate to attentional network activation and prefrontal cortex engagement."
        if any(w in text_lower for w in ["memory", "remember", "recall"]):
            return "This may relate to memory consolidation processes involving the hippocampus and associated structures."
        if any(w in text_lower for w in ["emotion", "feeling", "affect"]):
            return "Neuroscience suggests this may involve limbic system activation and emotional processing circuits."

        return "Neuroscience research may offer insights into the neural correlates of the processes described."

    def _generate_act(self, text: str, context: InterpretationContext) -> str:
        """Generate ACT (Acceptance and Commitment Therapy) interpretation."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["acceptance", "accept", "allow"]):
            return "This may resonate with the ACT concept of acceptance — making room for difficult experiences without trying to change them."
        if any(w in text_lower for w in ["defusion", "distance", "observe"]):
            return "This may relate to cognitive defusion — creating distance from thoughts and observing them as mental events."
        if any(w in text_lower for w in ["values", "meaning", "purpose"]):
            return "This may connect to the ACT concept of values — clarifying what matters most and acting accordingly."
        if any(w in text_lower for w in ["presence", "mindfulness", "awareness"]):
            return "This may relate to present-moment awareness as practiced in mindfulness-based approaches."

        return "This passage may have relevance to psychological flexibility as described in Acceptance and Commitment Therapy."

    def _generate_analytical(self, text: str, context: InterpretationContext) -> str:
        """Generate analytical philosophy interpretation."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["truth", "reality", "knowledge"]):
            return "From an analytical perspective, this raises questions about the nature of truth, reality, and knowledge."
        if any(w in text_lower for w in ["meaning", "language", "concept"]):
            return "This may be analyzed through the lens of philosophy of language and conceptual analysis."
        if any(w in text_lower for w in ["argument", "reason", "logic"]):
            return "This passage may be evaluated in terms of its logical structure and argumentative validity."

        return "This passage may be subject to analytical philosophical examination."

    def _generate_zen(self, text: str, context: InterpretationContext) -> str:
        """Generate Zen interpretation."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["silence", "stillness", "emptiness"]):
            return "This may resonate with the Zen emphasis on direct experience beyond conceptual thought."
        if any(w in text_lower for w in ["present", "moment", "now"]):
            return "This may relate to the Zen teaching of present-moment awareness."
        if any(w in text_lower for w in ["nature", "original", "beginner"]):
            return "This may connect to the Zen concept of original mind or beginner's mind."

        return "This passage may have resonance with Zen Buddhist perspectives on awareness and experience."

    def _generate_khorasan(self, text: str, context: InterpretationContext) -> str:
        """Generate Khorasan Mysticism interpretation."""
        text_lower = text.lower()

        if any(w in text_lower for w in ["love", "divine", "heart"]):
            return "This may relate to the Khorasan tradition's emphasis on divine love and heart-centered practice."
        if any(w in text_lower for w in ["surrender", "trust", "letting go"]):
            return "This may connect to the Khorasan concept of tawakkul — trust in divine guidance."
        if any(w in text_lower for w in ["remembrance", "dhikr", "repetition"]):
            return "This may relate to the practice of dhikr as repeated attentional redirection toward the divine."

        return "This passage may have resonance with Khorasan mystical traditions."

    def _generate_alternatives(self, text: str, context: InterpretationContext) -> list[str]:
        """Generate alternative interpretations."""
        alternatives: list[str] = []

        if any(w in text.lower() for w in ["truth", "reality"]):
            alternatives.append("A pragmatist might interpret this as a statement about practical consequences rather than absolute truth.")
            alternatives.append("A phenomenologist might focus on the lived experience described rather than propositional content.")

        if any(w in text.lower() for w in ["self", "identity"]):
            alternatives.append("A Buddhist perspective might interpret this as pointing to the constructed nature of self.")
            alternatives.append("A Western psychological perspective might focus on ego development and identity formation.")

        return alternatives

    def _generate_modern_mappings(self, text: str, context: InterpretationContext) -> list[ModernMapping]:
        """Generate modern framework mappings."""
        mappings: list[ModernMapping] = []
        text_lower = text.lower()

        if any(w in text_lower for w in ["attention", "focus", "concentration"]):
            mappings.append(ModernMapping(
                framework="Cognitive Science",
                tradition="Western",
                mapping="Attentional network activation",
                confidence=0.6,
                language="may resemble",
                limitations=["Neuroscience models are approximations"],
            ))

        if any(w in text_lower for w in ["acceptance", "allow", "embrace"]):
            mappings.append(ModernMapping(
                framework="ACT",
                tradition="Clinical Psychology",
                mapping="Psychological flexibility through acceptance",
                confidence=0.7,
                language="can be interpreted as",
                limitations=["Cultural context may differ"],
            ))

        return mappings

    def _generate_cross_tradition_mappings(
        self, text: str, context: InterpretationContext,
    ) -> list[CrossTraditionMapping]:
        """Generate cross-tradition mappings."""
        mappings: list[CrossTraditionMapping] = []
        text_lower = text.lower()

        if any(w in text_lower for w in ["meditation", "contemplation", "practice"]):
            mappings.append(CrossTraditionMapping(
                source_tradition=context.epistemic_profile.get("tradition", "unknown"),
                target_tradition="Zen Buddhism",
                concept="Meditation practice",
                source_description=context.chapter_title,
                target_description="Zazen and mindfulness meditation",
                mapping_description="Both traditions emphasize direct experiential practice",
                confidence=0.6,
                language="shares similarities with",
                limitations=["Different cultural contexts"],
            ))

        return mappings

    def _compute_confidence(self, text: str, context: InterpretationContext) -> float:
        """Compute interpretation confidence."""
        confidence = 0.5

        # Text length factor
        word_count = len(text.split())
        if word_count > 100:
            confidence += 0.1
        elif word_count > 30:
            confidence += 0.05

        # Epistemic profile factor
        if context.epistemic_profile:
            confidence += 0.1

        return min(1.0, confidence)

    def _compute_confidence_level(self, confidence: float) -> str:
        """Compute confidence level from score."""
        if confidence >= 0.8:
            return ConfidenceLevel.HIGH
        if confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        if confidence >= 0.4:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.SPECULATIVE

    def _generate_limitations(self, text: str, context: InterpretationContext) -> list[str]:
        """Generate limitations for the interpretation."""
        limitations: list[str] = [
            "Interpretation is secondary to the original text",
            "Modern mappings are approximations, not equivalences",
            "Cultural context may affect interpretation accuracy",
        ]

        if len(text.split()) < 50:
            limitations.append("Limited text context for interpretation")

        return limitations

    def _generate_uncertainties(self, text: str, context: InterpretationContext) -> list[str]:
        """Generate uncertainties for the interpretation."""
        uncertainties: list[str] = [
            "Original author's intent may differ from interpretation",
            "Cross-tradition mappings are tentative",
            "Multiple valid interpretations may exist",
        ]

        return uncertainties

    def _generate_provenance(
        self,
        text: str,
        context: InterpretationContext,
        source: SourceReference,
    ) -> list[Provenance]:
        """Generate provenance for interpretation elements."""
        from ayeneh.knowledge_interpretation.types import Provenance

        provenance: list[Provenance] = []

        # Provenance for practical insight
        provenance.append(Provenance(
            book_id=context.book_id,
            chapter_id=context.chapter_id,
            chunk_id=context.chunk_id,
            engine_version="1.0.0",
            generator="rule_based",
            reasoning_step="practical_insight_generation",
            evidence_summary="Text keyword analysis",
            confidence_contribution=0.15,
            confidence_reason="Based on text content analysis",
        ))

        # Provenance for conceptual meaning
        provenance.append(Provenance(
            book_id=context.book_id,
            chapter_id=context.chapter_id,
            chunk_id=context.chunk_id,
            engine_version="1.0.0",
            generator="rule_based",
            reasoning_step="conceptual_meaning_generation",
            evidence_summary="Concept extraction from text",
            confidence_contribution=0.15,
            confidence_reason="Based on conceptual analysis",
        ))

        # Provenance for modern translation
        provenance.append(Provenance(
            book_id=context.book_id,
            chapter_id=context.chapter_id,
            chunk_id=context.chunk_id,
            engine_version="1.0.0",
            generator="rule_based",
            reasoning_step="modern_translation_generation",
            evidence_summary="Contemporary language mapping",
            confidence_contribution=0.10,
            confidence_reason="Approximate modern equivalent",
        ))

        # Provenance from graph if available
        if context.knowledge_graph_context:
            provenance.append(Provenance(
                book_id=context.book_id,
                chapter_id=context.chapter_id,
                chunk_id=context.chunk_id,
                engine_version="1.0.0",
                generator="graph_enhanced",
                reasoning_step="graph_context_integration",
                evidence_summary="Knowledge graph relationships",
                confidence_contribution=0.20,
                confidence_reason="Graph-supported interpretation",
            ))

        return provenance

    def _compute_confidence_breakdown(
        self,
        text: str,
        context: InterpretationContext,
        provenance: list[Provenance],
    ) -> Any:
        """Compute decomposed confidence breakdown."""
        from ayeneh.knowledge_interpretation.types import ConfidenceBreakdown

        # Source confidence
        word_count = len(text.split())
        source_conf = 0.3
        if word_count > 100:
            source_conf = 0.7
        elif word_count > 50:
            source_conf = 0.5
        if context.epistemic_profile:
            source_conf = min(1.0, source_conf + 0.1)

        # Interpretation confidence
        interp_conf = 0.5
        if len(text.split()) > 50:
            interp_conf = 0.6

        # Graph confidence
        graph_conf = 0.3
        if context.knowledge_graph_context:
            graph_conf = context.knowledge_graph_context.get("graph_confidence", 0.5)

        # Cross-tradition confidence
        cross_trad_conf = 0.4
        if context.knowledge_graph_context:
            if context.knowledge_graph_context.get("alternative_traditions"):
                cross_trad_conf = 0.5

        # Mapping confidence
        mapping_conf = 0.5
        if context.knowledge_graph_context:
            if context.knowledge_graph_context.get("shared_concepts"):
                mapping_conf = 0.6

        # Evidence confidence
        evidence_conf = 0.5
        if len(provenance) > 2:
            evidence_conf = 0.6

        breakdown = ConfidenceBreakdown(
            source_confidence=source_conf,
            interpretation_confidence=interp_conf,
            graph_confidence=graph_conf,
            cross_tradition_confidence=cross_trad_conf,
            mapping_confidence=mapping_conf,
            evidence_confidence=evidence_conf,
        )

        breakdown.compute_overall()
        return breakdown


# ---------------------------------------------------------------------------
# Interpretation Validator
# ---------------------------------------------------------------------------


class InterpretationValidator:
    """Validates interpretations for completeness and correctness."""

    def validate(self, interpretation: Interpretation) -> list[str]:
        """Validate an interpretation. Returns list of errors."""
        errors: list[str] = []

        # Check source reference exists
        if not interpretation.source.document_id:
            errors.append("Missing document_id in source reference")

        if not interpretation.source.original_text:
            errors.append("Missing original_text in source reference")

        # Check confidence range
        if interpretation.confidence < 0.0 or interpretation.confidence > 1.0:
            errors.append("Confidence must be between 0.0 and 1.0")

        # Check limitations present
        if not interpretation.limitations:
            errors.append("Limitations must be present")

        # Check uncertainties present
        if not interpretation.uncertainties:
            errors.append("Uncertainties must be present")

        # Check alternative interpretations present
        if not interpretation.alternative_interpretations:
            errors.append("Alternative interpretations must be present")

        # Check modern mappings don't present as certainty
        for mapping in interpretation.modern_mappings:
            if mapping.language in ("is", "equals", "means"):
                errors.append(f"Modern mapping uses certainty language: {mapping.language}")

        return errors


# ---------------------------------------------------------------------------
# Interpretation Engine
# ---------------------------------------------------------------------------


class InterpretationEngine:
    """Single owner of interpretation generation and validation.

    Never modifies the original document.
    Interpretations are secondary artifacts.
    """

    def __init__(
        self,
        store: InterpretationStore | None = None,
        version_store: InterpretationVersionStore | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._store = store
        self._version_store = version_store
        self._events = event_publisher
        self._generator = InterpretationGenerator()
        self._validator = InterpretationValidator()

    async def generate_interpretation(
        self,
        context: InterpretationContext,
    ) -> Interpretation:
        """Generate an interpretation for a passage."""
        start = time.monotonic()

        # Generate interpretation
        interpretation = self._generator.generate(context)

        # Validate
        errors = self._validator.validate(interpretation)
        if errors:
            logger.warning(
                "interpretation_validation_failed",
                errors=errors,
            )

        # Store
        if self._store:
            interpretation = await self._store.save_interpretation(interpretation)

        # Version
        if self._version_store:
            version = InterpretationVersion(
                interpretation_id=interpretation.id,
                version=1,
                interpretation_data=self._to_dict(interpretation),
            )
            await self._version_store.save_version(version)

        # Publish event
        if self._events:
            await self._events.publish("InterpretationGenerated", {
                "interpretation_id": interpretation.id,
                "document_id": context.document_id,
                "chunk_id": context.chunk_id,
                "confidence": interpretation.confidence,
            })

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "interpretation_generated",
            interpretation_id=interpretation.id,
            confidence=interpretation.confidence,
            duration_ms=round(duration_ms, 2),
        )

        return interpretation

    async def get_interpretation(self, interpretation_id: str) -> Interpretation | None:
        """Get an interpretation by ID."""
        if self._store:
            return await self._store.get_interpretation(interpretation_id)
        return None

    async def get_interpretations_for_chunk(self, chunk_id: str) -> list[Interpretation]:
        """Get all interpretations for a chunk."""
        if self._store:
            return await self._store.get_interpretations_by_chunk(chunk_id)
        return []

    async def get_interpretations_for_chapter(self, chapter_id: str) -> list[Interpretation]:
        """Get all interpretations for a chapter."""
        if self._store:
            return await self._store.get_interpretations_by_chapter(chapter_id)
        return []

    async def get_interpretation_history(self, interpretation_id: str) -> list[InterpretationVersion]:
        """Get version history for an interpretation."""
        if self._version_store:
            return await self._version_store.get_versions(interpretation_id)
        return []

    def _to_dict(self, interpretation: Interpretation) -> dict[str, Any]:
        """Convert interpretation to dictionary."""
        return {
            "id": interpretation.id,
            "interpretation_kind": interpretation.interpretation_kind,
            "source": {
                "document_id": interpretation.source.document_id,
                "book_id": interpretation.source.book_id,
                "chapter_id": interpretation.source.chapter_id,
                "chunk_id": interpretation.source.chunk_id,
                "original_text": interpretation.source.original_text[:200],
            },
            "practical_insight": interpretation.practical_insight,
            "conceptual_meaning": interpretation.conceptual_meaning,
            "modern_translation": interpretation.modern_translation,
            "confidence": interpretation.confidence,
            "confidence_level": interpretation.confidence_level,
            "version": interpretation.version,
        }


# ---------------------------------------------------------------------------
# Interpretation Cache (Context-Aware)
# ---------------------------------------------------------------------------


class InterpretationCache:
    """In-memory cache for interpretations with structured keys.

    Ensures idempotent behavior: repeated requests never regenerate
    identical interpretations.

    Supports both simple chunk_id keys (backward compatible) and
    structured InterpretationCacheKey for context-aware caching.
    """

    def __init__(self) -> None:
        self._cache: dict[str, Interpretation] = {}
        self._key_cache: dict[str, Interpretation] = {}  # For structured keys

    def get(self, chunk_id: str) -> Interpretation | None:
        """Get cached interpretation by chunk_id (backward compatible)."""
        return self._cache.get(chunk_id)

    def get_by_key(self, key: InterpretationCacheKey) -> Interpretation | None:
        """Get cached interpretation by structured key."""
        return self._key_cache.get(key.to_string())

    def put(self, chunk_id: str, interpretation: Interpretation) -> None:
        """Cache an interpretation (backward compatible)."""
        self._cache[chunk_id] = interpretation

    def put_by_key(self, key: InterpretationCacheKey, interpretation: Interpretation) -> None:
        """Cache an interpretation with structured key."""
        self._key_cache[key.to_string()] = interpretation

    def invalidate(self, chunk_id: str) -> bool:
        """Remove an interpretation from cache by chunk_id."""
        removed = False
        if chunk_id in self._cache:
            del self._cache[chunk_id]
            removed = True
        # Also remove from key cache
        keys_to_remove = [k for k in self._key_cache if k.startswith(chunk_id + ":")]
        for k in keys_to_remove:
            del self._key_cache[k]
            removed = True
        return removed

    def invalidate_key(self, key: InterpretationCacheKey) -> bool:
        """Remove an interpretation from cache by structured key."""
        if key.to_string() in self._key_cache:
            del self._key_cache[key.to_string()]
            return True
        return False

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()
        self._key_cache.clear()

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {
            "simple_cache_size": len(self._cache),
            "key_cache_size": len(self._key_cache),
            "total_size": len(self._cache) + len(self._key_cache),
        }

    def __len__(self) -> int:
        return len(self._cache) + len(self._key_cache)

    def __contains__(self, chunk_id: str) -> bool:
        return chunk_id in self._cache


# ---------------------------------------------------------------------------
# On-Demand Interpretation Service
# ---------------------------------------------------------------------------


class OnDemandInterpretationService:
    """Transparently provides interpretations, generating them lazily if needed.

    Consumers should not know whether the interpretation already existed.
    Supports consumer-driven interpretation kind selection.
    """

    def __init__(
        self,
        engine: InterpretationEngine,
        cache: InterpretationCache | None = None,
    ) -> None:
        self._engine = engine
        self._cache = cache or InterpretationCache()
        self._graph_context_provider: Any | None = None
        self._type_selector = InterpretationTypeSelector()
        self._graph_reasoner = DeepGraphReasoner()

    def set_graph_context_provider(self, provider: Any) -> None:
        """Set an optional graph context provider for graph-aware generation."""
        self._graph_context_provider = provider

    async def get_or_generate(
        self,
        context: InterpretationContext,
        *,
        interpretation_kind: str | None = None,
        product_profile: str = "default",
    ) -> Interpretation:
        """Get an existing interpretation or generate one transparently.

        This is the main entry point for on-demand interpretation.
        Consumers can optionally request a specific interpretation kind.

        Priority:
        1. Explicit interpretation_kind request
        2. Automatic selector
        3. Default Conservative
        """
        chunk_id = context.chunk_id

        # Determine interpretation kind
        kind = interpretation_kind or self._type_selector.select(
            context, context.knowledge_graph_context,
        )

        # Step 1: Check cache with structured key
        cache_key = InterpretationCacheKey(
            chunk_id=chunk_id,
            product_profile=product_profile,
            interpretation_kind=kind,
        )
        cached = self._cache.get_by_key(cache_key)
        if cached is not None:
            return cached

        # Also check simple cache for backward compatibility
        cached_simple = self._cache.get(chunk_id)
        if cached_simple is not None and cached_simple.interpretation_kind == kind:
            return cached_simple

        # Step 2: Check repository
        if self._engine._store:
            existing = await self._engine._store.get_interpretations_by_chunk(chunk_id)
            if existing:
                # Find matching kind
                for interp in existing:
                    if interp.interpretation_kind == kind:
                        self._cache.put_by_key(cache_key, interp)
                        return interp
                # If no exact match, use first available
                interpretation = existing[0]
                self._cache.put_by_key(cache_key, interpretation)
                return interpretation

        # Step 3: Enrich context with graph if available
        if self._graph_context_provider:
            try:
                graph_ctx = await self._graph_context_provider.get_context(
                    context.chunk_id, context.document_id,
                )
                if graph_ctx:
                    context.knowledge_graph_context = graph_ctx
            except Exception:
                pass  # Graph is optional, never require it

        # Step 4: Generate interpretation with deep graph reasoning
        context_copy = InterpretationContext(
            document_id=context.document_id,
            book_id=context.book_id,
            chapter_id=context.chapter_id,
            chapter_title=context.chapter_title,
            chunk_id=context.chunk_id,
            chunk_content=context.chunk_content,
            topic_id=context.topic_id,
            epistemic_profile=context.epistemic_profile,
            knowledge_graph_context=context.knowledge_graph_context,
            related_interpretations=context.related_interpretations,
        )

        interpretation = await self._engine.generate_interpretation(context_copy)

        # Set the determined interpretation kind
        interpretation.interpretation_kind = kind

        # Step 5: Deep graph reasoning if graph available
        if context.knowledge_graph_context:
            interpretation = self._graph_reasoner.enhance(
                interpretation, context.knowledge_graph_context,
            )

        # Step 6: Cache the result
        self._cache.put_by_key(cache_key, interpretation)

        return interpretation

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()


# ---------------------------------------------------------------------------
# Deep Graph Reasoner
# ---------------------------------------------------------------------------


class DeepGraphReasoner:
    """Actively reasons using the Knowledge Graph for interpretations.

    Goes beyond simple confidence boosting to generate rich graph-informed
    perspectives.
    """

    def enhance(
        self,
        interpretation: Interpretation,
        graph_data: dict[str, Any],
    ) -> Interpretation:
        """Enhance interpretation with deep graph reasoning."""
        from ayeneh.knowledge_interpretation.types import GraphContext, GraphReasoningResult

        # Build graph context
        graph_ctx = GraphContext(
            related_concepts=graph_data.get("related_concepts", []),
            supporting_books=graph_data.get("supporting_books", []),
            alternative_traditions=graph_data.get("alternative_traditions", []),
            known_disagreements=graph_data.get("known_disagreements", []),
            complementary_viewpoints=graph_data.get("complementary_viewpoints", []),
            shared_concepts=graph_data.get("shared_concepts", []),
            historical_influences=graph_data.get("historical_influences", []),
            authority_comparisons=graph_data.get("authority_comparisons", []),
            scope_comparisons=graph_data.get("scope_comparisons", []),
            graph_confidence=graph_data.get("graph_confidence", 0.5),
        )

        interpretation.graph_context = graph_ctx

        # Perform deep reasoning
        reasoning = self._reason(graph_ctx, interpretation)
        interpretation.graph_reasoning = reasoning

        # Add supporting perspectives
        for perspective in reasoning.supporting_perspectives:
            interpretation.alternative_interpretations.append(
                f"Supporting perspective: {perspective}"
            )

        # Add alternative perspectives (preserve distinctions)
        for perspective in reasoning.alternative_perspectives:
            interpretation.alternative_interpretations.append(
                f"Alternative perspective: {perspective}"
            )

        # Add conflicting perspectives (never merge)
        for perspective in reasoning.conflicting_perspectives:
            interpretation.alternative_interpretations.append(
                f"Conflicting perspective: {perspective}"
            )

        # Add complementary perspectives
        for perspective in reasoning.complementary_perspectives:
            interpretation.alternative_interpretations.append(
                f"Complementary perspective: {perspective}"
            )

        # Add scope limitations
        interpretation.limitations.extend(reasoning.scope_limitations)

        # Add authority differences
        interpretation.limitations.extend(reasoning.authority_differences)

        # Boost confidence based on graph support
        if reasoning.supporting_perspectives:
            interpretation.confidence = min(
                1.0, interpretation.confidence + 0.1 * len(reasoning.supporting_perspectives),
            )

        return interpretation

    def _reason(
        self,
        graph_ctx: GraphContext,
        interpretation: Interpretation,
    ) -> GraphReasoningResult:
        """Perform deep reasoning using graph context."""
        supporting: list[str] = []
        alternative: list[str] = []
        conflicting: list[str] = []
        complementary: list[str] = []
        scope_lim: list[str] = []
        authority_diff: list[str] = []
        evidence: list[str] = []

        # Reason about supporting perspectives
        if graph_ctx.supporting_books:
            for book in graph_ctx.supporting_books[:3]:
                supporting.append(
                    f"Similar perspective found in {book}"
                )
                evidence.append(f"supporting_book:{book}")

        # Reason about shared concepts
        if graph_ctx.shared_concepts:
            for concept in graph_ctx.shared_concepts[:3]:
                supporting.append(
                    f"Shares concept '{concept}' with related sources"
                )
                evidence.append(f"shared_concept:{concept}")

        # Reason about alternative traditions
        if graph_ctx.alternative_traditions:
            for tradition in graph_ctx.alternative_traditions[:3]:
                alternative.append(
                    f"The {tradition} tradition approaches this differently"
                )
                evidence.append(f"alternative_tradition:{tradition}")

        # Reason about disagreements
        if graph_ctx.known_disagreements:
            for disagreement in graph_ctx.known_disagreements[:3]:
                conflicting.append(
                    f"Known disagreement: {disagreement}"
                )
                evidence.append(f"disagreement:{disagreement}")

        # Reason about complementary viewpoints
        if graph_ctx.complementary_viewpoints:
            for viewpoint in graph_ctx.complementary_viewpoints[:3]:
                complementary.append(
                    f"Complementary perspective: {viewpoint}"
                )
                evidence.append(f"complementary:{viewpoint}")

        # Reason about scope comparisons
        if graph_ctx.scope_comparisons:
            for comparison in graph_ctx.scope_comparisons[:2]:
                scope_lim.append(
                    f"Scope consideration: {comparison}"
                )
                evidence.append(f"scope:{comparison}")

        # Reason about authority comparisons
        if graph_ctx.authority_comparisons:
            for comparison in graph_ctx.authority_comparisons[:2]:
                authority_diff.append(
                    f"Authority note: {comparison}"
                )
                evidence.append(f"authority:{comparison}")

        # Compute reasoning confidence
        reasoning_confidence = 0.5
        if supporting:
            reasoning_confidence += 0.1 * len(supporting)
        if alternative:
            reasoning_confidence += 0.05 * len(alternative)

        return GraphReasoningResult(
            supporting_perspectives=supporting,
            alternative_perspectives=alternative,
            conflicting_perspectives=conflicting,
            complementary_perspectives=complementary,
            scope_limitations=scope_lim,
            authority_differences=authority_diff,
            reasoning_confidence=min(1.0, reasoning_confidence),
            evidence_used=evidence,
        )


# ---------------------------------------------------------------------------
# Graph-Aware Interpretation Generator
# ---------------------------------------------------------------------------


class GraphAwareInterpretationGenerator:
    """Extends InterpretationGenerator with optional graph context.

    When graph is available, uses it for richer interpretations.
    When graph is unavailable, falls back to standard generation.
    """

    def __init__(self, base_generator: InterpretationGenerator | None = None) -> None:
        self._base_generator = base_generator or InterpretationGenerator()

    def generate(
        self,
        context: InterpretationContext,
    ) -> Interpretation:
        """Generate interpretation, optionally using graph context."""
        # Generate base interpretation
        interpretation = self._base_generator.generate(context)

        # If graph context is available, enrich the interpretation
        graph_data = context.knowledge_graph_context
        if graph_data:
            interpretation = self._enrich_with_graph_context(interpretation, graph_data)

        return interpretation

    def _enrich_with_graph_context(
        self,
        interpretation: Interpretation,
        graph_data: dict[str, Any],
    ) -> Interpretation:
        """Enrich interpretation with graph context."""
        from ayeneh.knowledge_interpretation.types import GraphContext

        graph_ctx = GraphContext(
            related_concepts=graph_data.get("related_concepts", []),
            supporting_books=graph_data.get("supporting_books", []),
            alternative_traditions=graph_data.get("alternative_traditions", []),
            known_disagreements=graph_data.get("known_disagreements", []),
            complementary_viewpoints=graph_data.get("complementary_viewpoints", []),
            shared_concepts=graph_data.get("shared_concepts", []),
            historical_influences=graph_data.get("historical_influences", []),
            authority_comparisons=graph_data.get("authority_comparisons", []),
            scope_comparisons=graph_data.get("scope_comparisons", []),
            graph_confidence=graph_data.get("graph_confidence", 0.5),
        )

        interpretation.graph_context = graph_ctx

        # Add graph-informed alternatives
        if graph_ctx.alternative_traditions:
            for alt in graph_ctx.alternative_traditions:
                interpretation.alternative_interpretations.append(
                    f"Another tradition ({alt}) may approach this differently"
                )

        # Add graph-informed cross-tradition mappings
        if graph_ctx.shared_concepts:
            for concept in graph_ctx.shared_concepts[:3]:
                interpretation.cross_tradition_mappings.append(
                    type("obj", (object,), {
                        "source_tradition": "current",
                        "target_tradition": "related",
                        "concept": concept,
                        "mapping_description": f"Shares concept: {concept}",
                        "confidence": graph_ctx.graph_confidence,
                        "language": "shares similarities with",
                        "limitations": ["Graph-derived mapping"],
                    })()
                )

        # Boost confidence if graph supports the interpretation
        if graph_ctx.supporting_books:
            interpretation.confidence = min(
                1.0, interpretation.confidence + 0.1,
            )

        return interpretation


# ---------------------------------------------------------------------------
# Interpretation Type Selector
# ---------------------------------------------------------------------------


class InterpretationTypeSelector:
    """Selects the appropriate interpretation kind based on context."""

    def select(
        self,
        context: InterpretationContext,
        graph_context: dict[str, Any] | None = None,
    ) -> str:
        """Select the interpretation kind."""
        text = context.chunk_content.lower()

        # Check for cross-tradition signals
        if graph_context:
            if graph_context.get("shared_concepts") or graph_context.get("alternative_traditions"):
                return "cross_tradition"

        # Check for comparative signals
        if any(w in text for w in ["compare", "versus", "different", "alternative"]):
            return "comparative"

        # Check for practical signals
        if any(w in text for w in ["practice", "technique", "how to", "apply", "exercise"]):
            return "practical"

        # Check for exploratory signals
        if any(w in text for w in ["hypothesis", "might", "possibly", "speculate"]):
            return "exploratory"

        # Default to conservative
        return "conservative"
