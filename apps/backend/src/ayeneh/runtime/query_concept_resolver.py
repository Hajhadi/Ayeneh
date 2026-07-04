"""QueryConceptResolver — single owner of concept resolution for user queries.

Orchestrates existing knowledge_concepts components without duplicating logic.
No new extraction algorithms. No LLM. No graph mutation. Read-only access only.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from typing import Any

import structlog

from ayeneh.knowledge_concepts.engine import (
    CandidateGenerator,
    CandidateNormalizer,
    RuleBasedConceptDiscovery,
)
from ayeneh.knowledge_concepts.types import ConceptProvenance

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedConcept:
    """A concept resolved from the query text."""
    canonical: str
    confidence: float
    source: str  # "registry" | "normalizer" | "discovery"
    aliases: list[str] = field(default_factory=list)
    domain: str | None = None


@dataclass(frozen=True)
class ResolvedEntity:
    """A named entity resolved from the query text."""
    name: str
    entity_type: str  # "author" | "book" | "tradition" | "framework"
    confidence: float


@dataclass(frozen=True)
class AmbiguityItem:
    """Two concepts too similar to distinguish confidently."""
    term_a: str
    term_b: str
    similarity: float
    reason: str


@dataclass
class QueryConceptResolution:
    """Complete result of concept resolution."""
    resolved_concepts: list[ResolvedConcept] = field(default_factory=list)
    resolved_entities: list[ResolvedEntity] = field(default_factory=list)
    unresolved_terms: list[str] = field(default_factory=list)
    ambiguities: list[AmbiguityItem] = field(default_factory=list)
    concept_confidence: float = 0.0
    entity_confidence: float = 0.0


# ---------------------------------------------------------------------------
# Entity registry (separate from concepts)
# ---------------------------------------------------------------------------

ENTITY_MAP: dict[str, dict[str, Any]] = {
    "Metzinger": {"type": "author", "keywords": ["metzinger", "متزینگر"]},
    "Hayes": {"type": "author", "keywords": ["hayes", "هیز", "steven hayes"]},
    "Suzuki": {"type": "author", "keywords": ["suzuki", "سوزوکی", "shunryu suzuki"]},
    "Sapolsky": {"type": "author", "keywords": ["sapolsky", "ساپولسکی"]},
    "Damasio": {"type": "author", "keywords": ["damasio", "داماسیو"]},
    "Van der Kolk": {"type": "author", "keywords": ["van der kolk", "واندروکلک"]},
    "ACT": {"type": "framework", "keywords": ["act", "acceptance and commitment therapy", "درمان پذیرش و تعهد"]},
    "Zen": {"type": "tradition", "keywords": ["zen", "ذن", "zen mind"]},
    "Buddhism": {"type": "tradition", "keywords": ["buddhism", "بودیسم", "بودا", "dharma", "دارما"]},
    "Sufism": {"type": "tradition", "keywords": ["sufism", "تصوف", "صوفی", "عرفان"]},
    "Neuroscience": {"type": "framework", "keywords": ["neuroscience", "عصب‌شناسی"]},
    "Cognitive Science": {"type": "framework", "keywords": ["cognitive science", "علم شناخت"]},
}


# ---------------------------------------------------------------------------
# QueryConceptResolver
# ---------------------------------------------------------------------------


class QueryConceptResolver:
    """Orchestrates concept resolution using existing knowledge_concepts module.

    Three-tier resolution:
    Tier 1: Canonical registry lookup (fast, exact match)
    Tier 2: CandidateNormalizer (alias resolution)
    Tier 3: RuleBasedConceptDiscovery (full pipeline fallback)
    """

    def __init__(self) -> None:
        self._discovery = RuleBasedConceptDiscovery()
        self._normalizer = CandidateNormalizer()
        self._generator = CandidateGenerator()
        self._registry: dict[str, list[str]] | None = None

    def _load_registry(self) -> dict[str, list[str]]:
        """Load canonical concept registry from DB + CandidateGenerator."""
        if self._registry is not None:
            return self._registry

        registry: dict[str, list[str]] = {}

        # Source 1: CandidateGenerator dictionaries
        fa_to_en = {
            "خود": "Self", "هویت": "Self", "آگاهی": "Awareness", "حضور": "Presence",
            "شهود": "Witness", "فنا": "Fana", "توبه": "Repentance", "صبر": "Patience",
            "توکل": "Trust", "معرفت": "Knowledge", "ذکر": "Remembrance", "تمرین": "Practice",
            "مراقبه": "Meditation",
        }
        ar_to_en = {
            "النفس": "Self", "الذات": "Self", "الوعي": "Awareness", "الحضور": "Presence",
            "الشهود": "Witness", "الفنا": "Fana", "التوبة": "Repentance", "الصبر": "Patience",
            "التوكل": "Trust", "المعرفة": "Knowledge", "الذكر": "Remembrance", "التأمل": "Meditation",
        }
        for lang, concepts in self._generator.DICTIONARY_CONCEPTS.items():
            mapping = fa_to_en if lang == "fa" else ar_to_en if lang == "ar" else {}
            for c in concepts:
                canonical = mapping.get(c, c)
                if canonical not in registry:
                    registry[canonical] = []
                registry[canonical].append(c)

        # Source 2: Normalization map (keyword -> canonical) — reverse to canonical -> keywords
        for keyword, canonical in self._normalizer.NORMALIZATIONS.items():
            if canonical not in registry:
                registry[canonical] = []
            if keyword not in registry[canonical]:
                registry[canonical].append(keyword)

        # Source 3: Epistemic profile topics from DB
        try:
            db_path = "/home/hadi/ayeneh/Ayeneh/ayeneh.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT primary_topics, secondary_topics FROM epistemic_profiles WHERE deleted_at IS NULL")
            existing_keywords = set()
            for keywords in registry.values():
                existing_keywords.update(keywords)
            for canonical, keywords in self._normalizer.NORMALIZATIONS.items():
                existing_keywords.update(keywords)
            for row in cursor.fetchall():
                for topics_json in row:
                    if topics_json:
                        try:
                            topics = json.loads(topics_json) if isinstance(topics_json, str) else topics_json
                            for t in topics:
                                if t in existing_keywords:
                                    continue
                                canonical = t.capitalize() if t.islower() else t
                                if canonical in registry:
                                    continue
                                registry[canonical] = [t]
                                existing_keywords.add(t)
                        except (json.JSONDecodeError, TypeError):
                            pass
            conn.close()
        except Exception:
            pass

        # Source 4: Additional concepts
        additional = {
            "Non-self": ["non-self", "anatta", "بی‌خودی", "anatman"],
            "Defusion": ["defusion", "جداشدن", "آزادی از فکر"],
            "Enlightenment": ["enlightenment", "روشنایی", "بیداری", "awakening"],
            "Witness": ["witness", "گواه", "شاهد", "ناظر"],
            "Patience": ["patience", "صبر", "تحمل"],
            "Trust": ["trust", "اعتماد"],
            "Remembrance": ["remembrance", "ذکر"],
            "Practice": ["practice", "تمرین"],
            "Repentance": ["repentance", "توبه"],
            "Biology": ["biology", "زیست‌شناسی"],
            "Physics": ["physics", "فیزیک"],
            "Psychology": ["psychology", "روانشناسی"],
            "Therapy": ["therapy", "درمان"],
            "Development": ["development", "رشد"],
            "Ethics": ["ethics", "اخلاق"],
            "Prayer": ["prayer", "نماز"],
            "Science": ["science", "علم"],
        }
        for canonical, keywords in additional.items():
            if canonical not in registry:
                registry[canonical] = []
            for kw in keywords:
                if kw not in registry[canonical]:
                    registry[canonical].append(kw)

        self._registry = registry
        return registry

    def _detect_language(self, text: str) -> str:
        """Detect primary language of query text."""
        persian_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F')
        if persian_chars > len(text) * 0.1:
            return "fa"
        return "en"

    def _resolve_entities(self, text_lower: str) -> list[ResolvedEntity]:
        """Resolve named entities (authors, books, traditions) — separate from concepts."""
        entities = []
        for name, info in ENTITY_MAP.items():
            if any(kw in text_lower for kw in info["keywords"]):
                entities.append(ResolvedEntity(
                    name=name,
                    entity_type=info["type"],
                    confidence=0.9,
                ))
        return entities

    def _tier1_registry_lookup(self, text_lower: str, registry: dict[str, list[str]]) -> list[ResolvedConcept]:
        """Tier 1: Exact match against canonical registry.

        First check NORMALIZATIONS to resolve keywords to canonicals,
        then check registry for canonical matches.
        """
        concepts = []
        seen = set()

        # Build reverse map: keyword -> canonical from NORMALIZATIONS
        kw_to_canonical = {}
        for keyword, canonical in self._normalizer.NORMALIZATIONS.items():
            kw_to_canonical[keyword] = canonical

        # Check each keyword in text against NORMALIZATIONS first
        for keyword, canonical in kw_to_canonical.items():
            if keyword in text_lower and canonical not in seen:
                seen.add(canonical)
                keywords = registry.get(canonical, [keyword])
                concepts.append(ResolvedConcept(
                    canonical=canonical,
                    confidence=1.0,
                    source="registry",
                    aliases=keywords[:5],
                ))

        # Also check registry directly for canonicals not in NORMALIZATIONS
        for canonical, keywords in registry.items():
            if canonical not in seen and any(kw in text_lower for kw in keywords):
                seen.add(canonical)
                concepts.append(ResolvedConcept(
                    canonical=canonical,
                    confidence=1.0,
                    source="registry",
                    aliases=keywords[:5],
                ))

        return concepts

    # Persian keyword -> canonical English name (fallback for normalizer)
    _FA_TO_CANONICAL: dict[str, str] = {
        "خود": "Self", "هویت": "Self", "ذات": "Self", "خویشتن": "Self",
        "آگاهی": "Awareness", "حضور": "Presence", "شهود": "Witness",
        "فنا": "Fana", "توبه": "Repentance", "صبر": "Patience",
        "توکل": "Trust", "معرفت": "Knowledge", "ذکر": "Remembrance",
        "تمرین": "Practice", "مراقبه": "Meditation", "عبادت": "Practice",
        "زهد": "Zuhd", "توکل": "Trust", " علم": "Knowledge",
        " رحمت": "Compassion", " مهربانی": "Compassion",
        "افکار": "Thoughts", "عادت": "Habit", "ترس": "Fear",
        "درد": "Pain", "رنج": "Suffering", "اضطراب": "Anxiety",
        "ذن": "Zen", "بودیسم": "Buddhism", "بودا": "Buddhism",
        "عرفان": "Mysticism", "تصوف": "Sufism", "صوفی": "Sufism",
        "نماز": "Prayer", "عبادت": "Practice", "پذیرش": "Acceptance",
        "رضا": "Acceptance", "رضایت": "Acceptance",
        "meditation": "Meditation", "awareness": "Awareness",
        "consciousness": "Consciousness", "acceptance": "Acceptance",
        "mindfulness": "Mindfulness", "self": "Self",
    }

    # Case-insensitive dedup map: lowercase variant -> canonical
    _CASE_DEDUP: dict[str, str] = {
        "self": "Self", "awareness": "Awareness", "mindfulness": "Mindfulness",
        "meditation": "Meditation", "acceptance": "Acceptance", "suffering": "Suffering",
        "consciousness": "Consciousness", "compassion": "Compassion",
        "آگاهی": "Awareness", "خود": "Self", " هویت": "Self", "ذات": "Self",
        "فنا": "Fana", "صبر": "Patience", "توکل": "Trust", "معرفت": "Knowledge",
        "ذکر": "Remembrance", "مراقبه": "Meditation", "عبادت": "Practice",
        "زهد": "Zuhd", "رحمت": "Compassion", "مهربانی": "Compassion",
        "حضور": "Presence", "شهود": "Witness", "توبه": "Repentance",
        "درد": "Pain", "رنج": "Suffering", "ترس": "Fear", "اضطراب": "Anxiety",
    }

    def _tier2_normalize(self, text: str, text_lower: str, already_resolved: set[str]) -> list[ResolvedConcept]:
        """Tier 2: Resolve remaining terms via normalizer + FA fallback."""
        concepts = []
        seen = set()

        # Resolve terms via _FA_TO_CANONICAL (Persian keywords)
        for word in text_lower.split():
            if len(word) < 2 or word in already_resolved or word in seen:
                continue
            if word in self._FA_TO_CANONICAL:
                canonical = self._FA_TO_CANONICAL[word]
                if canonical not in seen and canonical not in already_resolved:
                    seen.add(canonical)
                    concepts.append(ResolvedConcept(
                        canonical=canonical,
                        confidence=0.85,
                        source="normalizer",
                    ))

        # Try CandidateNormalizer for English terms only
        try:
            en_text = ' '.join(w for w in text_lower.split() if all(c.isascii() for c in w))
            if en_text.strip():
                candidates = self._generator.generate(en_text, language="en")
                normalized = self._normalizer.normalize(candidates)
                for nc in normalized:
                    if nc.canonical not in seen and nc.canonical not in already_resolved:
                        seen.add(nc.canonical)
                        concepts.append(ResolvedConcept(
                            canonical=nc.canonical,
                            confidence=nc.confidence,
                            source="normalizer",
                        ))
        except Exception:
            pass

        return concepts

    def _tier3_discover(self, text: str, already_resolved: set[str]) -> list[ResolvedConcept]:
        """Tier 3: Use RuleBasedConceptDiscovery for unknown terms.
        Only returns concepts whose keywords actually appear in the text.
        """
        provenance = ConceptProvenance(
            book_id="query",
            chunk_id="query",
            language=self._detect_language(text),
        )

        try:
            discovered = self._discovery.discover(text, provenance)
        except Exception:
            return []

        text_lower = text.lower()
        concepts = []
        seen = set()
        for dc in discovered:
            if hasattr(dc, 'normalized') and dc.normalized:
                if hasattr(dc.normalized, 'canonical'):
                    name = dc.normalized.canonical
                else:
                    name = str(dc.normalized)
            else:
                name = dc.text if hasattr(dc, 'text') else str(dc)

            # Only include if the concept's text actually appears in the query
            if name.lower() not in text_lower and name not in text:
                continue

            if name not in seen and name not in already_resolved:
                seen.add(name)
                conf = 0.5
                if hasattr(dc, 'confidence') and dc.confidence:
                    if hasattr(dc.confidence, 'overall_confidence'):
                        conf = dc.confidence.overall_confidence
                concepts.append(ResolvedConcept(
                    canonical=name,
                    confidence=conf,
                    source="discovery",
                ))
        return concepts

    def _detect_ambiguities(self, concepts: list[ResolvedConcept]) -> list[AmbiguityItem]:
        """Detect ambiguous concept pairs using existing discovery pipeline."""
        if len(concepts) < 2:
            return []

        # Build DiscoveredConcept-like objects for ambiguity detection
        from ayeneh.knowledge_concepts.types import DiscoveredConcept, NormalizedConcept, CandidateEvidence

        dc_list = []
        for c in concepts:
            nc = NormalizedConcept(original=c.canonical, canonical=c.canonical, confidence=c.confidence)
            evidence = CandidateEvidence()
            dc_list.append(DiscoveredConcept(
                text=c.canonical,
                normalized=nc,
                confidence=None,
                evidence=evidence,
            ))

        try:
            raw_ambiguities = self._discovery.find_ambiguities(dc_list)
            return [
                AmbiguityItem(
                    term_a=a.concept_a,
                    term_b=a.concept_b,
                    similarity=a.similarity_score,
                    reason=a.reason,
                )
                for a in raw_ambiguities
            ]
        except Exception:
            return []

    def resolve(self, query: str, language: str = "auto") -> QueryConceptResolution:
        """Resolve concepts and entities from a user query.

        Public API — single entry point. Returns QueryConceptResolution.
        """
        text_lower = query.lower()
        lang = language if language != "auto" else self._detect_language(query)

        # Step 1: Resolve entities (separate from concepts)
        entities = self._resolve_entities(text_lower)

        # Step 2: Three-tier concept resolution
        registry = self._load_registry()

        # Tier 1: Registry lookup
        tier1 = self._tier1_registry_lookup(text_lower, registry)
        resolved_set = {c.canonical for c in tier1}

        # Tier 2: Normalizer
        tier2 = self._tier2_normalize(query, text_lower, resolved_set)
        resolved_set.update(c.canonical for c in tier2)

        # Tier 3: Discovery (only if fewer than 2 concepts found)
        tier3 = []
        if len(tier1) + len(tier2) < 2:
            tier3 = self._tier3_discover(query, resolved_set)
            resolved_set.update(c.canonical for c in tier3)

        all_concepts_raw = tier1 + tier2 + tier3

        # Dedup: merge lowercase duplicates into canonical form
        deduped = {}
        for c in all_concepts_raw:
            canonical = c.canonical
            # Check if this is a lowercase variant of an already-resolved canonical
            if canonical.lower() in self._CASE_DEDUP:
                canonical = self._CASE_DEDUP[canonical.lower()]
            if canonical not in deduped:
                deduped[canonical] = c
            elif c.confidence > deduped[canonical].confidence:
                deduped[canonical] = c
        all_concepts = list(deduped.values())

        # Remove entity names from concepts
        entity_names = {e.name for e in entities}
        all_concepts = [c for c in all_concepts if c.canonical not in entity_names]

        # Step 3: Detect ambiguities
        ambiguities = self._detect_ambiguities(all_concepts)

        # Step 4: Compute confidence
        concept_conf = 0.0
        if all_concepts:
            concept_conf = sum(c.confidence for c in all_concepts) / len(all_concepts)

        entity_conf = 0.0
        if entities:
            entity_conf = sum(e.confidence for e in entities) / len(entities)

        # Step 5: Identify unresolved terms
        resolved_names = {c.canonical.lower() for c in all_concepts}
        resolved_names.update(e.name.lower() for e in entities)
        stop_words = {"this", "that", "what", "how", "why", "when", "where", "which",
                      "does", "can", "the", "and", "or", "is", "are", "do", "in", "on",
                      "at", "to", "for", "of", "with", "by", "آیا", "همان", "چه", "که",
                      "از", "در", "با", "برای", "و", "یا", "است", "هستند", "می‌شود", "دارند"}
        unresolved = [w for w in text_lower.split() if len(w) > 2 and w not in stop_words and w not in resolved_names]

        resolution = QueryConceptResolution(
            resolved_concepts=all_concepts,
            resolved_entities=entities,
            unresolved_terms=unresolved[:10],
            ambiguities=ambiguities,
            concept_confidence=concept_conf,
            entity_confidence=entity_conf,
        )

        logger.debug(
            "query_concepts_resolved",
            concepts=[c.canonical for c in all_concepts],
            entities=[e.name for e in entities],
            unresolved_count=len(unresolved),
            ambiguities_count=len(ambiguities),
        )

        return resolution
