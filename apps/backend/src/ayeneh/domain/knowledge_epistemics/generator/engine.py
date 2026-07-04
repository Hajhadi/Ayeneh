"""Epistemic Generation Engine — protocol and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

import structlog

from ayeneh.domain.knowledge_epistemics.entities import EpistemicProfile
from ayeneh.domain.knowledge_epistemics.enums import (
    ClaimType,
    EvidenceLevel,
    EpistemicFramework,
    KnowledgeAuthority,
    KnowledgeDomain,
    KnowledgeSource,
    ReasoningStyle,
)
from ayeneh.domain.knowledge_epistemics.generator.types import (
    DocumentContext,
    GenerationMetadata,
    ValidationResult,
)
from ayeneh.domain.knowledge_epistemics.value_objects import (
    Applicability,
    CitationPolicy,
    Limitation,
    ScopeBoundary,
    SourceReliability,
    TranslationMetadata,
)

logger = structlog.get_logger(__name__)


@runtime_checkable
class EpistemicGenerationEngine(Protocol):
    """Protocol for interchangeable profile generation engines."""

    def generate(
        self,
        context: DocumentContext,
        book_id: str,
        user_id: str,
    ) -> tuple[EpistemicProfile, GenerationMetadata]:
        """Generate an epistemic profile from document context."""
        ...

    def validate(self, profile: EpistemicProfile) -> ValidationResult:
        """Validate a generated profile."""
        ...


class RuleBasedProfileGenerator:
    """Default rule-based profile generator.

    Works without any LLM. Generates profiles based on
    document structure, content analysis, and domain heuristics.
    Supports both English and Persian (Farsi) keyword detection.
    """

    @staticmethod
    def _has_keyword(text: str, keywords: list[str]) -> bool:
        """Check if text contains any keyword (handles Persian + English)."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)

    @staticmethod
    def _count_keywords(text: str, keywords: list[str]) -> int:
        """Count keyword matches in text."""
        text_lower = text.lower()
        return sum(1 for kw in keywords if kw in text_lower)

    def generate(
        self,
        context: DocumentContext,
        book_id: str,
        user_id: str,
    ) -> tuple[EpistemicProfile, GenerationMetadata]:
        """Generate an epistemic profile using rule-based analysis."""
        import uuid
        from datetime import UTC, datetime

        start = datetime.now(UTC)
        metadata = GenerationMetadata(
            engine_type="rule_based",
            chapters_analyzed=len(context.chapters),
            total_tokens_analyzed=sum(
                c.get("token_count", 0) for c in context.chapters
            ),
        )

        # Analyze content
        all_text = " ".join(c.get("content", "") for c in context.chapters)
        title_lower = context.title.lower()
        author_lower = context.author.lower()

        # Detect domain
        domain = self._detect_domain(all_text, title_lower)
        metadata.confidence_factors.append(f"domain_detected:{domain}")

        # Detect framework
        framework = self._detect_framework(all_text, domain)
        metadata.confidence_factors.append(f"framework_detected:{framework}")

        # Detect evidence level
        evidence_level = self._detect_evidence_level(all_text, domain)
        metadata.confidence_factors.append(f"evidence_level:{evidence_level}")

        # Detect authority
        authority = self._detect_authority(all_text, context)
        metadata.confidence_factors.append(f"authority:{authority}")

        # Detect reasoning style
        reasoning_style = self._detect_reasoning_style(all_text, domain)
        metadata.confidence_factors.append(f"reasoning_style:{reasoning_style}")

        # Detect claim types
        claim_types = self._detect_claim_types(all_text, domain)

        # Detect topics
        primary_topics, secondary_topics = self._detect_topics(all_text, domain)

        # Detect supported/unsupported questions
        supported, unsupported = self._detect_question_support(all_text, domain)

        # Detect limitations
        limitations = self._detect_limitations(all_text, domain, context)

        # Detect scope boundaries
        scope_boundary = self._detect_scope_boundary(all_text, domain)

        # Detect applicability
        applicability = self._detect_applicability(all_text, domain)

        # Estimate reliability
        reliability = self._estimate_reliability(context, authority, evidence_level)

        # Generate citation policy
        citation_policy = self._generate_citation_policy(evidence_level, authority)

        # Detect tradition
        tradition = self._detect_tradition(all_text, domain, author_lower)

        # Build profile
        profile = EpistemicProfile(
            id=uuid.uuid4(),
            book_id=uuid.UUID(book_id) if len(book_id) == 36 else uuid.uuid4(),
            user_id=uuid.UUID(user_id) if len(user_id) == 36 else uuid.uuid4(),
            source=KnowledgeSource.BOOK,
            tradition=tradition,
            framework=framework,
            discipline=domain,
            primary_topics=primary_topics,
            secondary_topics=secondary_topics,
            supported_questions=supported,
            unsupported_questions=unsupported,
            evidence_level=evidence_level,
            reasoning_style=reasoning_style,
            authority=authority,
            claim_types=claim_types,
            applicability=applicability,
            limitations=limitations,
            scope_boundary=scope_boundary,
            citation_policy=citation_policy,
            source_reliability=reliability,
            language=context.language,
            document_id=context.document_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        duration_ms = (datetime.now(UTC) - start).total_seconds() * 1000
        metadata.analysis_duration_ms = duration_ms

        logger.info(
            "profile_generated_rule_based",
            book_id=book_id,
            domain=domain,
            framework=framework,
            duration_ms=round(duration_ms, 2),
        )

        return profile, metadata

    def validate(self, profile: EpistemicProfile) -> ValidationResult:
        """Validate a generated profile."""
        errors: list[str] = []
        warnings: list[str] = []
        checks: dict[str, bool] = {}

        # Required fields
        if not profile.tradition:
            errors.append("tradition is required")
        checks["tradition"] = bool(profile.tradition)

        if not profile.discipline:
            errors.append("discipline is required")
        checks["discipline"] = bool(profile.discipline)

        # Confidence range
        if profile.source_reliability.score < 0.0 or profile.source_reliability.score > 1.0:
            errors.append("reliability score must be between 0.0 and 1.0")
        checks["reliability_range"] = 0.0 <= profile.source_reliability.score <= 1.0

        # Limitations should exist
        if not profile.limitations:
            warnings.append("no limitations detected")
        checks["limitations_exist"] = bool(profile.limitations)

        # Scope boundaries should exist
        if not profile.scope_boundary.included_topics and not profile.scope_boundary.excluded_topics:
            warnings.append("no scope boundaries detected")
        checks["scope_boundaries_exist"] = bool(
            profile.scope_boundary.included_topics or profile.scope_boundary.excluded_topics
        )

        # Supported/unsupported should not overlap
        overlap = set(profile.supported_questions) & set(profile.unsupported_questions)
        if overlap:
            errors.append(f"overlap in supported/unsupported: {overlap}")
        checks["no_overlap"] = len(overlap) == 0

        # Authority compatible with evidence
        if profile.authority == KnowledgeAuthority.PRIMARY and profile.evidence_level == EvidenceLevel.ANECDOTAL:
            warnings.append("primary authority with anecdotal evidence may be inconsistent")
        checks["authority_evidence_compatible"] = not (
            profile.authority == KnowledgeAuthority.PRIMARY
            and profile.evidence_level == EvidenceLevel.ANECDOTAL
        )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            consistency_checks=checks,
        )

    # ------------------------------------------------------------------
    # Detection methods
    # ------------------------------------------------------------------

    def _detect_domain(self, text: str, title: str) -> KnowledgeDomain:
        """Detect the primary knowledge domain."""
        text_lower = text.lower()
        title_lower = title.lower()

        domain_scores: dict[KnowledgeDomain, float] = {
            KnowledgeDomain.PHILOSOPHY: 0.0,
            KnowledgeDomain.PSYCHOLOGY: 0.0,
            KnowledgeDomain.SPIRITUALITY: 0.0,
            KnowledgeDomain.SCIENCE: 0.0,
            KnowledgeDomain.HISTORY: 0.0,
            KnowledgeDomain.LITERATURE: 0.0,
            KnowledgeDomain.SOCIAL_SCIENCE: 0.0,
            KnowledgeDomain.PRACTICAL: 0.0,
        }

        # Title keywords (high weight) — English + Persian
        title_keywords: dict[KnowledgeDomain, list[str]] = {
            KnowledgeDomain.PHILOSOPHY: [
                "philosophy", "philosophical", "metaphysics", "epistemology", "ontology", "ethics",
                "فلسفه", "فلسفی", "معرفت‌شناسی", "هستی‌شناسی", "اخلاق", "منطق",
            ],
            KnowledgeDomain.PSYCHOLOGY: [
                "psychology", "psychological", "cognitive", "behavior", "mental", "therapy", "clinical",
                "روانشناسی", "روانی", "شناختی", "رفتار", "درمان", "بالینی", "焦虑", "اضطراب",
            ],
            KnowledgeDomain.SPIRITUALITY: [
                "spiritual", "meditation", "mysticism", "contemplation", "zen", "sufi", "religious",
                "معنوی", "مراقبه", "ذکر", "تصوف", "صوفی", "عرفان", "冥想", "سیر و سلوک", "زهد", "عبادت",
            ],
            KnowledgeDomain.SCIENCE: [
                "science", "scientific", "research", "study", "data", "evidence", "neuroscience",
                "علم", "科学", "پژوهش", "مطالعه", "داده", "شواهد", "neuroscience", "مغز",
            ],
            KnowledgeDomain.HISTORY: [
                "history", "historical", "century", "ancient", "civilization",
                "تاریخ", "تاریخی", "قرن", "باستان", "تمدن",
            ],
            KnowledgeDomain.LITERATURE: [
                "literature", "literary", "novel", "poetry", "narrative",
                "ادبیات", "ادبی", "رمان", "شعر", "داستان",
            ],
            KnowledgeDomain.SOCIAL_SCIENCE: [
                "sociology", "social", "culture", "society", "political",
                "جامعه‌شناسی", "اجتماعی", "فرهنگ", "جامعه", "سیاسی",
            ],
            KnowledgeDomain.PRACTICAL: [
                "guide", "how to", "practice", "technique", "method", "workbook",
                "راهنما", "روش", "تکنیک", "تمرین", "کتاب کار",
            ],
        }

        for domain, keywords in title_keywords.items():
            for kw in keywords:
                if kw in title_lower or kw in text_lower:
                    domain_scores[domain] += 3.0

        # Content keywords (lower weight) — English + Persian
        content_keywords: dict[KnowledgeDomain, list[str]] = {
            KnowledgeDomain.PHILOSOPHY: [
                "truth", "reality", "existence", "meaning", "reason", "logic", "argument",
                "حقیقت", "واقعیت", "هستی", "معنا", "عقل", "منطق", "استدلال", "وجود",
            ],
            KnowledgeDomain.PSYCHOLOGY: [
                "mind", "brain", "behavior", "emotion", "cognition", "therapy", "disorder",
                "ذهن", "مغز", "رفتار", "احساس", "شناخت", "درمان", "اختلال", "اضطراب", "افسردگی",
            ],
            KnowledgeDomain.SPIRITUALITY: [
                "meditation", "prayer", "contemplation", "enlightenment", "awakening", "spirit",
                "مراقبه", "نماز", "ذکر", "تامل", "بیداری", "روح", "عرفان", "سیر و سلوک", " zen",
            ],
            KnowledgeDomain.SCIENCE: [
                "experiment", "hypothesis", "theory", "data", "empirical", "study", "research",
                "آزمایش", "فرضیه", "نظریه", "داده", "تجربی", "مطالعه", "پژوهش",
            ],
            KnowledgeDomain.HISTORY: [
                "century", "era", "period", "ancient", "medieval", "modern", "civilization",
                "قرن", "دوره", "باستان", "قرون وسطی", "مدرن", "تمدن",
            ],
            KnowledgeDomain.LITERATURE: [
                "story", "narrative", "character", "plot", "theme", "symbol", "metaphor",
                "داستان", "شخصیت", "طرح", "موضوع", "نماد", "استعاره",
            ],
            KnowledgeDomain.SOCIAL_SCIENCE: [
                "society", "culture", "community", "social", "power", "inequality",
                "جامعه", "فرهنگ", "اجتماعی", "قدرت", "نابرابری",
            ],
            KnowledgeDomain.PRACTICAL: [
                "practice", "exercise", "technique", "step", "method", "guide", "how to",
                "تمرین", "تکنیک", "مرحله", "روش", "راهنما",
            ],
        }

        for domain, keywords in content_keywords.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            domain_scores[domain] += matches * 0.5

        # Get highest scoring domain
        best_domain = max(domain_scores, key=lambda d: domain_scores[d])
        if domain_scores[best_domain] > 0:
            return best_domain

        return KnowledgeDomain.PHILOSOPHY  # Default

    def _detect_framework(self, text: str, domain: KnowledgeDomain) -> EpistemicFramework:
        """Detect the epistemological framework."""
        text_lower = text.lower()

        framework_scores: dict[EpistemicFramework, float] = {
            EpistemicFramework.RATIONALIST: 0.0,
            EpistemicFramework.EMPIRICIST: 0.0,
            EpistemicFramework.PHENOMENOLOGICAL: 0.0,
            EpistemicFramework.HERMENEUTIC: 0.0,
            EpistemicFramework.DIALECTICAL: 0.0,
            EpistemicFramework.PRAGMATIST: 0.0,
            EpistemicFramework.INTUITIONIST: 0.0,
            EpistemicFramework.NATURALISTIC: 0.0,
            EpistemicFramework.CONSTRUCTIVIST: 0.0,
            EpistemicFramework.CRITICAL: 0.0,
        }

        framework_keywords: dict[EpistemicFramework, list[str]] = {
            EpistemicFramework.RATIONALIST: [
                "reason", "logic", "argument", "proof", "deduction", "rational",
                "عقل", "منطق", "استدلال", "اثبات", "برهان", "عقلانی",
            ],
            EpistemicFramework.EMPIRICIST: [
                "evidence", "data", "observation", "experiment", "empirical", "measurement",
                "شواهد", "داده", "مشاهده", "آزمایش", "تجربی", "اندازه‌گیری",
            ],
            EpistemicFramework.PHENOMENOLOGICAL: [
                "experience", "lived", "phenomenon", "consciousness", "perception",
                "تجربه", "زیسته", "پدیدار", "آگاهی", "ادراک", "شعور",
            ],
            EpistemicFramework.HERMENEUTIC: [
                "interpret", "meaning", "text", "understanding", "hermeneutic",
                "تفسیر", "معنا", "متن", "فهم", "تأویل",
            ],
            EpistemicFramework.DIALECTICAL: [
                "contradiction", "tension", "thesis", "antithesis", "synthesis", "dialectic",
                "تناقض", "کشش", "تز", "آنتیتز", "سنتز", " dialectic",
            ],
            EpistemicFramework.PRAGMATIST: [
                "practical", "consequence", "action", "work", "function",
                "عملی", "نتیجه", "عمل", "کارکرد",
            ],
            EpistemicFramework.INTUITIONIST: [
                "intuition", "direct", "immediate", "inner", "contemplative",
                "شهود", "بی‌واسطه", "درونی", "تاملی", ".med",
            ],
            EpistemicFramework.NATURALISTIC: [
                "nature", "natural", "evolution", "biology", "ecology",
                "طبیعت", "طبیعی", "تکامل", "زیست‌شناسی", "بوم‌شناسی",
            ],
            EpistemicFramework.CONSTRUCTIVIST: [
                "construct", "build", "create", "social", "cultural",
                "ساختن", "ایجاد", "اجتماعی", "فرهنگی",
            ],
            EpistemicFramework.CRITICAL: [
                "power", "critique", "justice", "inequality", "oppression",
                "قدرت", "نقد", "عدالت", "نابرابری", "سرکوب",
            ],
        }

        for framework, keywords in framework_keywords.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            framework_scores[framework] += matches * 0.5

        # Domain-specific boosts
        if domain == KnowledgeDomain.SCIENCE:
            framework_scores[EpistemicFramework.EMPIRICIST] += 2.0
            framework_scores[EpistemicFramework.NATURALISTIC] += 1.0
        elif domain == KnowledgeDomain.PHILOSOPHY:
            framework_scores[EpistemicFramework.RATIONALIST] += 1.5
            framework_scores[EpistemicFramework.DIALECTICAL] += 1.0
        elif domain == KnowledgeDomain.SPIRITUALITY:
            framework_scores[EpistemicFramework.INTUITIONIST] += 2.0
            framework_scores[EpistemicFramework.PHENOMENOLOGICAL] += 1.5
        elif domain == KnowledgeDomain.PSYCHOLOGY:
            framework_scores[EpistemicFramework.EMPIRICIST] += 1.0
            framework_scores[EpistemicFramework.PHENOMENOLOGICAL] += 1.0

        best_framework = max(framework_scores, key=lambda f: framework_scores[f])
        if framework_scores[best_framework] > 0:
            return best_framework

        return EpistemicFramework.RATIONALIST  # Default

    def _detect_evidence_level(self, text: str, domain: KnowledgeDomain) -> EvidenceLevel:
        """Detect the expected evidence level."""
        text_lower = text.lower()

        # Domain defaults
        domain_evidence: dict[KnowledgeDomain, EvidenceLevel] = {
            KnowledgeDomain.SCIENCE: EvidenceLevel.EMPIRICAL,
            KnowledgeDomain.PSYCHOLOGY: EvidenceLevel.EMPIRICAL,
            KnowledgeDomain.PHILOSOPHY: EvidenceLevel.PHILOSOPHICAL,
            KnowledgeDomain.SPIRITUALITY: EvidenceLevel.EXPERIENTIAL,
            KnowledgeDomain.HISTORY: EvidenceLevel.TRADITIONAL,
            KnowledgeDomain.LITERATURE: EvidenceLevel.PHILOSOPHICAL,
            KnowledgeDomain.SOCIAL_SCIENCE: EvidenceLevel.EMPIRICAL,
            KnowledgeDomain.PRACTICAL: EvidenceLevel.ANECDOTAL,
        }

        # Check for empirical indicators (English + Persian)
        empirical_indicators = [
            "study", "research", "data", "experiment", "statistical", "empirical",
            "پژوهش", "مطالعه", "داده", "آزمایش", "آماری", "تجربی", "اندازه‌گیری",
        ]
        empirical_count = sum(1 for ind in empirical_indicators if ind in text_lower)

        # Check for experiential indicators (English + Persian)
        experiential_indicators = [
            "experience", "felt", "lived", "personal", "subjective",
            "تجربه", "احساس", "زیسته", "شخصی", "ذاتی", "مراقبه", "meditation",
        ]
        experiential_count = sum(1 for ind in experiential_indicators if ind in text_lower)

        # Check for traditional indicators (English + Persian)
        traditional_indicators = [
            "tradition", "traditional", "ancient", "classic", "heritage",
            "سنت", "سنتی", "باستانی", "کلاسیک", "میراث", "ance",
        ]
        traditional_count = sum(1 for ind in traditional_indicators if ind in text_lower)

        if empirical_count > 3:
            return EvidenceLevel.EMPIRICAL
        if experiential_count > 3:
            return EvidenceLevel.EXPERIENTIAL
        if traditional_count > 3:
            return EvidenceLevel.TRADITIONAL

        return domain_evidence.get(domain, EvidenceLevel.PHILOSOPHICAL)

    def _detect_authority(self, text: str, context: DocumentContext) -> KnowledgeAuthority:
        """Detect the authority level."""
        text_lower = text.lower()

        # Check for academic indicators (English + Persian)
        academic_indicators = [
            "professor", "university", "research", "peer-reviewed", "journal",
            "استاد", "دانشگاه", "پژوهش", "مجله", "علمی",
        ]
        academic_count = sum(1 for ind in academic_indicators if ind in text_lower)

        # Check for commentary indicators (English + Persian)
        commentary_indicators = [
            "commentary", "analysis", "interpretation", "critique",
            "تفسیر", "تحلیل", "نقد", "تبیین",
        ]
        commentary_count = sum(1 for ind in commentary_indicators if ind in text_lower)

        # Check for reference indicators (English + Persian)
        reference_indicators = [
            "reference", "handbook", "manual", "guide", "compendium",
            "مرجع", "کتاب مرجع", "راهنما",
        ]
        reference_count = sum(1 for ind in reference_indicators if ind in text_lower)

        if academic_count > 2:
            return KnowledgeAuthority.PRIMARY
        if commentary_count > 2:
            return KnowledgeAuthority.COMMENTARY
        if reference_count > 2:
            return KnowledgeAuthority.REFERENCE

        return KnowledgeAuthority.SECONDARY

    def _detect_reasoning_style(self, text: str, domain: KnowledgeDomain) -> ReasoningStyle:
        """Detect the reasoning style."""
        text_lower = text.lower()

        # Domain defaults
        domain_style: dict[KnowledgeDomain, ReasoningStyle] = {
            KnowledgeDomain.SCIENCE: ReasoningStyle.INDUCTIVE,
            KnowledgeDomain.PHILOSOPHY: ReasoningStyle.DEDUCTIVE,
            KnowledgeDomain.SPIRITUALITY: ReasoningStyle.CONTEMPLATIVE,
            KnowledgeDomain.PSYCHOLOGY: ReasoningStyle.INDUCTIVE,
            KnowledgeDomain.HISTORY: ReasoningStyle.NARRATIVE,
            KnowledgeDomain.LITERATURE: ReasoningStyle.ANALOGICAL,
            KnowledgeDomain.PRACTICAL: ReasoningStyle.NARRATIVE,
        }

        # Check for reasoning indicators (English + Persian)
        if any(w in text_lower for w in ["therefore", "thus", "consequently", "logically", "بنابراین", "لذا", "پس", "منطقاً"]):
            return ReasoningStyle.DEDUCTIVE
        if any(w in text_lower for w in ["pattern", "trend", "observe", "inductively", "الگو", "روند", "مشاهده"]):
            return ReasoningStyle.INDUCTIVE
        if any(w in text_lower for w in ["contemplat", "meditat", "inner", "silence", "مراقبه", "تامل", "درون", "سکوت", "meditation"]):
            return ReasoningStyle.CONTEMPLATIVE
        if any(w in text_lower for w in ["story", "narrative", "journey", "once", "داستان", "روایت", "سفر"]):
            return ReasoningStyle.NARRATIVE

        return domain_style.get(domain, ReasoningStyle.DEDUCTIVE)

    def _detect_claim_types(self, text: str, domain: KnowledgeDomain) -> list[ClaimType]:
        """Detect the types of claims made."""
        text_lower = text.lower()
        claim_types: list[ClaimType] = []

        if any(w in text_lower for w in ["is", "are", "fact", "reality", "truth", "واقعیت", "حقیقت", "fact"]):
            claim_types.append(ClaimType.FACTUAL)
        if any(w in text_lower for w in ["interpret", "meaning", "understand", "significance", "تفسیر", "معنا", "فهم"]):
            claim_types.append(ClaimType.INTERPRETIVE)
        if any(w in text_lower for w in ["should", "ought", "moral", "ethical", "right", "باید", "اخلاقی", "道德"]):
            claim_types.append(ClaimType.NORMATIVE)
        if any(w in text_lower for w in ["describe", "description", "observed", "phenomenon", "توصیف", "پدیده"]):
            claim_types.append(ClaimType.DESCRIPTIVE)
        if any(w in text_lower for w in ["like", "as if", "metaphor", "analogy", "استعاره", "تشبیه"]):
            claim_types.append(ClaimType.ANALOGICAL)
        if any(w in text_lower for w in ["might", "possibly", "hypothesis", "speculate", "شاید", "فرضیه"]):
            claim_types.append(ClaimType.SPECULATIVE)

        if not claim_types:
            claim_types.append(ClaimType.INTERPRETIVE)

        return claim_types

    def _detect_topics(self, text: str, domain: KnowledgeDomain) -> tuple[list[str], list[str]]:
        """Detect primary and secondary topics."""
        text_lower = text.lower()

        # Domain-specific topic detection (English + Persian)
        topic_keywords: dict[KnowledgeDomain, dict[str, list[str]]] = {
            KnowledgeDomain.PHILOSOPHY: {
                "metaphysics": ["reality", "existence", "being", "ontology", "واقعیت", "هستی", "وجود"],
                "epistemology": ["knowledge", "truth", "belief", "justification", "دانش", "حقیقت", "باور"],
                "ethics": ["moral", "virtue", "duty", "right", "wrong", "اخلاق", "فضیلت", "تکلیف"],
                "logic": ["reason", "argument", "valid", "sound", "عقل", "استدلال", "منطق"],
                "aesthetics": ["beauty", "art", "taste", "sublime", "زیبایی", "هنر"],
            },
            KnowledgeDomain.PSYCHOLOGY: {
                "cognition": ["mind", "brain", "cognitive", "mental", "ذهن", "مغز", "شناختی"],
                "behavior": ["behavior", "action", "habit", "response", "رفتار", "عمل", "عادت"],
                "emotion": ["emotion", "feeling", "affect", "mood", "احساس", "هیجان", "عاطفه"],
                "therapy": ["therapy", "treatment", "clinical", "disorder", "درمان", "بالینی", "اختلال"],
                "development": ["development", "growth", "change", "lifespan", "رشد", "تغییر"],
            },
            KnowledgeDomain.SPIRITUALITY: {
                "meditation": ["meditation", "contemplation", "mindfulness", "مراقبه", "تامل", "حضور ذهن"],
                "mysticism": ["mystical", "mysticism", "esoteric", "عرفان", "تصوف", "صوفی"],
                "prayer": ["prayer", "devotion", "worship", "نماز", "عبادت", "ذکر"],
                "awakening": ["enlightenment", "awakening", "liberation", "بیداری", "آزادی", "رستگاری"],
                "ethics": ["virtue", "compassion", "love", "wisdom", "فضی الفت", "مهربانی", "دانایی"],
            },
            KnowledgeDomain.SCIENCE: {
                "neuroscience": ["brain", "neural", "neuroscience", "cognitive", "مغز", "عصب", "شناختی"],
                "biology": ["biology", "evolution", "genetics", "organism", "زیست", "تکامل", "ژنتیک"],
                "physics": ["physics", "quantum", "energy", "matter", "فیزیک", "کوانتوم", "انرژی"],
                "psychology": ["psychology", "behavior", "cognition", "روانشناسی", "رفتار", "شناخت"],
                "methodology": ["method", "research", "experiment", "study", "روش", "پژوهش", "آزمایش"],
            },
        }

        domains_topics = topic_keywords.get(domain, {})
        primary: list[str] = []
        secondary: list[str] = []

        for topic, keywords in domains_topics.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches >= 2:
                primary.append(topic)
            elif matches >= 1:
                secondary.append(topic)

        return primary[:5], secondary[:5]

    def _detect_question_support(
        self, text: str, domain: KnowledgeDomain
    ) -> tuple[list[str], list[str]]:
        """Detect supported and unsupported question types."""
        text_lower = text.lower()

        supported: list[str] = []
        unsupported: list[str] = []

        # Domain-specific question support
        if domain == KnowledgeDomain.PHILOSOPHY:
            supported = ["What is the nature of reality?", "What is truth?", "What is the good life?"]
            unsupported = ["How do I fix my computer?", "What is the weather?"]
        elif domain == KnowledgeDomain.PSYCHOLOGY:
            supported = ["How do habits form?", "What causes anxiety?", "How does memory work?"]
            unsupported = ["What is the meaning of life?", "What is beauty?"]
        elif domain == KnowledgeDomain.SPIRITUALITY:
            supported = ["What is meditation?", "What is consciousness?", "What is enlightenment?"]
            unsupported = ["How do I invest money?", "What is the capital of France?"]
        elif domain == KnowledgeDomain.SCIENCE:
            supported = ["How does this mechanism work?", "What does the evidence show?"]
            unsupported = ["What is morally right?", "What is beautiful?"]
        else:
            supported = ["What is this about?", "How does this relate to other topics?"]
            unsupported = ["What should I do with my life?"]

        return supported, unsupported

    def _detect_limitations(
        self, text: str, domain: KnowledgeDomain, context: DocumentContext
    ) -> list[Limitation]:
        """Detect limitations of the source."""
        limitations: list[Limitation] = []

        # Domain-specific limitations
        if domain == KnowledgeDomain.PHILOSOPHY:
            limitations.append(Limitation(
                description="Philosophical arguments may not be empirically verifiable",
                severity="moderate",
                affected_domains=["science", "clinical"],
            ))
        elif domain == KnowledgeDomain.SPIRITUALITY:
            limitations.append(Limitation(
                description="Spiritual experiences are subjective and not universally replicable",
                severity="significant",
                affected_domains=["science", "clinical"],
            ))
        elif domain == KnowledgeDomain.SCIENCE:
            limitations.append(Limitation(
                description="Scientific findings may not generalize across all populations",
                severity="moderate",
                affected_domains=["spirituality", "philosophy"],
            ))

        # General limitations
        limitations.append(Limitation(
            description="Cultural and historical context may limit applicability",
            severity="minor",
            affected_domains=["cross-cultural"],
        ))

        return limitations

    def _detect_scope_boundary(self, text: str, domain: KnowledgeDomain) -> ScopeBoundary:
        """Detect scope boundaries."""
        included: list[str] = []
        excluded: list[str] = []

        if domain == KnowledgeDomain.PHILOSOPHY:
            included = ["metaphysics", "epistemology", "ethics", "logic"]
            excluded = ["clinical diagnosis", "medical treatment", "financial advice"]
        elif domain == KnowledgeDomain.PSYCHOLOGY:
            included = ["cognition", "behavior", "emotion", "therapy"]
            excluded = ["spiritual practice", "metaphysical claims"]
        elif domain == KnowledgeDomain.SPIRITUALITY:
            included = ["contemplation", "meditation", "inner experience"]
            excluded = ["clinical diagnosis", "scientific proof", "material analysis"]
        elif domain == KnowledgeDomain.SCIENCE:
            included = ["empirical research", "data analysis", "methodology"]
            excluded = ["spiritual claims", "moral prescriptions", "aesthetic judgments"]

        return ScopeBoundary(
            included_topics=included,
            excluded_topics=excluded,
            overlap_notes=[],
        )

    def _detect_applicability(self, text: str, domain: KnowledgeDomain) -> Applicability:
        """Detect applicability contexts."""
        contexts: list[str] = []
        conditions: list[str] = []
        contraindications: list[str] = []

        if domain == KnowledgeDomain.PHILOSOPHY:
            contexts = ["inquiry", "discussion", "study", "reflection"]
            conditions = ["willingness to think abstractly"]
            contraindications = ["seeking practical solutions only"]
        elif domain == KnowledgeDomain.PSYCHOLOGY:
            contexts = ["therapy", "self-understanding", "behavior change"]
            conditions = ["openness to self-examination"]
            contraindications = ["severe psychiatric emergency"]
        elif domain == KnowledgeDomain.SPIRITUALITY:
            contexts = ["meditation", "contemplation", "spiritual practice"]
            conditions = ["open mind", "willingness to explore"]
            contraindications = ["purely empirical inquiry", "clinical diagnosis"]
        elif domain == KnowledgeDomain.SCIENCE:
            contexts = ["research", "education", "evidence-based practice"]
            conditions = ["scientific literacy"]
            contraindications = ["non-empirical claims"]

        return Applicability(
            contexts=contexts,
            conditions=conditions,
            contraindications=contraindications,
        )

    def _estimate_reliability(
        self, context: DocumentContext, authority: KnowledgeAuthority, evidence: EvidenceLevel
    ) -> SourceReliability:
        """Estimate source reliability."""
        score = 0.5
        basis = "mixed"

        # Authority adjustment
        if authority == KnowledgeAuthority.PRIMARY:
            score += 0.2
            basis = "scholarly_consensus"
        elif authority == KnowledgeAuthority.SECONDARY:
            score += 0.1
        elif authority == KnowledgeAuthority.COMMENTARY:
            score += 0.05

        # Evidence adjustment
        if evidence == EvidenceLevel.EMPIRICAL:
            score += 0.15
            basis = "peer_reviewed"
        elif evidence == EvidenceLevel.PHILOSOPHICAL:
            score += 0.1
        elif evidence == EvidenceLevel.EXPERIENTIAL:
            score += 0.05

        return SourceReliability(
            score=min(1.0, score),
            basis=basis,
        )

    def _generate_citation_policy(
        self, evidence: EvidenceLevel, authority: KnowledgeAuthority
    ) -> CitationPolicy:
        """Generate citation policy."""
        required = authority in (KnowledgeAuthority.PRIMARY, KnowledgeAuthority.SECONDARY)
        fmt = "author-date" if evidence == EvidenceLevel.EMPIRICAL else "inline"
        min_confidence = 0.6 if authority == KnowledgeAuthority.PRIMARY else 0.4

        return CitationPolicy(
            required=required,
            format=fmt,
            min_confidence=min_confidence,
        )

    def _detect_tradition(self, text: str, domain: KnowledgeDomain, author: str) -> str:
        """Detect the intellectual tradition."""
        text_lower = text.lower()

        traditions: dict[str, list[str]] = {
            "analytic_philosophy": [
                "analytic", "logical", "language", "analysis",
                "تحلیلی", "منطقی", "زبان",
            ],
            "continental_philosophy": [
                "continental", "phenomenology", "existential", "hermeneutic",
                "پدیدارشناسی", "وجودگرایی", "تأویلی",
            ],
            "buddhist": [
                "buddhist", "buddhism", "dharma", "sangha", "zen", "vipassana",
                "بودایی", "بودا", "دارما", " zen", "ویپاسانا",
            ],
            "sufi": [
                "sufi", "sufism", "mystical", "islamic mysticism",
                "صوفی", "تصوف", "عرفان", "اسلامی",
            ],
            "cognitive_science": [
                "cognitive", "neural", "brain", "computation",
                "شناختی", "عصبی", "مغز", "پردازش",
            ],
            "behavioral": [
                "behavioral", "behavior", "conditioning", "skinner",
                "رفتاری", "شرطی‌سازی",
            ],
            "humanistic": [
                "humanistic", "person-centered", "rogers", "maslow",
                "انسان‌گرا", "شخص‌محور",
            ],
            "persian_mysticism": [
                "مولوی", "مولانا", "حافظ", "سعدی", "عطار", "صهبا",
                "عرفان ایرانی", "شعر عرفانی",
            ],
        }

        for tradition, keywords in traditions.items():
            if any(kw in text_lower for kw in keywords):
                return tradition

        return "general"
