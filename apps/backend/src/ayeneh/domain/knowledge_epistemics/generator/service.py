"""EpistemicProfileGenerator — single owner of profile creation and validation."""

from __future__ import annotations

import time
from typing import Any

import structlog

from ayeneh.domain.knowledge_epistemics.entities import EpistemicProfile
from ayeneh.domain.knowledge_epistemics.generator.engine import (
    EpistemicGenerationEngine,
    RuleBasedProfileGenerator,
)
from ayeneh.domain.knowledge_epistemics.generator.types import (
    DocumentContext,
    GenerationMetadata,
    GenerationResult,
    GenerationStatus,
    ProfileVersion,
    ValidationResult,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Abstract ports
# ---------------------------------------------------------------------------


class ProfileStore:
    """Abstract persistence for epistemic profiles."""

    async def save_profile(self, profile: EpistemicProfile) -> EpistemicProfile:
        raise NotImplementedError

    async def get_profile_by_book(self, book_id: str) -> EpistemicProfile | None:
        raise NotImplementedError

    async def update_profile(self, profile: EpistemicProfile) -> None:
        raise NotImplementedError

    async def delete_profile(self, profile_id: str) -> None:
        raise NotImplementedError


class ProfileVersionStore:
    """Abstract persistence for profile versions."""

    async def save_version(self, version: ProfileVersion) -> ProfileVersion:
        raise NotImplementedError

    async def get_versions(self, profile_id: str) -> list[ProfileVersion]:
        raise NotImplementedError

    async def get_current_version(self, profile_id: str) -> ProfileVersion | None:
        raise NotImplementedError


class DocumentReader:
    """Abstract reader for document content."""

    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    async def get_chapters(self, document_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError


class EventPublisher:
    """Abstract event publishing interface."""

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# EpistemicProfileGenerator
# ---------------------------------------------------------------------------


class EpistemicProfileGenerator:
    """Single owner of epistemic profile creation and validation.

    Subscribes to DocumentImported events and generates profiles.
    Supports both rule-based and LLM-based generation.
    """

    def __init__(
        self,
        profile_store: ProfileStore,
        version_store: ProfileVersionStore,
        document_reader: DocumentReader,
        event_publisher: EventPublisher,
        engine: EpistemicGenerationEngine | None = None,
    ) -> None:
        self._profile_store = profile_store
        self._version_store = version_store
        self._doc_reader = document_reader
        self._events = event_publisher
        self._engine = engine or RuleBasedProfileGenerator()

    async def generate_profile(
        self,
        document_id: str,
        book_id: str,
        user_id: str,
    ) -> GenerationResult:
        """Generate an epistemic profile for a document."""
        start = time.monotonic()

        try:
            # Step 1: Load document context
            context = await self._load_document_context(document_id)
            if context is None:
                return GenerationResult(
                    status=GenerationStatus.FAILED,
                    error="Document not found",
                )

            # Step 2: Generate profile
            profile, metadata = self._engine.generate(context, book_id, user_id)

            # Step 3: Validate
            validation = self._engine.validate(profile)
            if not validation.is_valid:
                logger.warning(
                    "profile_validation_failed",
                    book_id=book_id,
                    errors=validation.errors,
                )

            # Step 4: Persist profile
            profile = await self._profile_store.save_profile(profile)

            # Step 5: Create version
            version = ProfileVersion(
                profile_id=str(profile.id),
                version=1,
                book_id=book_id,
                user_id=user_id,
                profile_data=self._profile_to_dict(profile),
                validation_result=validation,
                generation_metadata=metadata,
                is_current=True,
            )
            await self._version_store.save_version(version)

            # Step 6: Publish event
            await self._events.publish("EpistemicProfileGenerated", {
                "profile_id": str(profile.id),
                "book_id": book_id,
                "document_id": document_id,
                "domain": profile.discipline,
                "framework": profile.framework,
                "confidence": profile.source_reliability.score,
                "engine_type": metadata.engine_type,
            })

            duration_ms = (time.monotonic() - start) * 1000

            logger.info(
                "profile_generation_complete",
                profile_id=str(profile.id),
                book_id=book_id,
                domain=profile.discipline,
                duration_ms=round(duration_ms, 2),
            )

            return GenerationResult(
                status=GenerationStatus.COMPLETED,
                profile_id=str(profile.id),
                version=1,
                validation=validation,
                metadata=metadata,
            )

        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            error_msg = str(exc)
            logger.exception("profile_generation_failed", book_id=book_id, error=error_msg)

            return GenerationResult(
                status=GenerationStatus.FAILED,
                error=error_msg,
                metadata=GenerationMetadata(analysis_duration_ms=duration_ms),
            )

    async def regenerate_profile(
        self,
        book_id: str,
        user_id: str,
    ) -> GenerationResult:
        """Regenerate an existing profile without re-importing."""
        start = time.monotonic()

        try:
            # Get existing profile
            existing = await self._profile_store.get_profile_by_book(book_id)
            if existing is None:
                return GenerationResult(
                    status=GenerationStatus.FAILED,
                    error="No existing profile found",
                )

            # Get document context - use the document_id from the profile
            doc_id = existing.document_id or book_id
            context = await self._load_document_context(doc_id)
            if context is None:
                return GenerationResult(
                    status=GenerationStatus.FAILED,
                    error="Document not found",
                )

            # Generate new profile
            profile, metadata = self._engine.generate(context, book_id, user_id)

            # Validate
            validation = self._engine.validate(profile)

            # Update existing profile
            profile.id = existing.id
            profile.created_at = existing.created_at
            await self._profile_store.update_profile(profile)

            # Get next version number
            versions = await self._version_store.get_versions(str(profile.id))
            next_version = max((v.version for v in versions), default=0) + 1

            # Create new version
            version = ProfileVersion(
                profile_id=str(profile.id),
                version=next_version,
                book_id=book_id,
                user_id=user_id,
                profile_data=self._profile_to_dict(profile),
                validation_result=validation,
                generation_metadata=metadata,
                is_current=True,
            )

            # Mark previous versions as not current (make a copy to avoid mutating during iteration)
            for v in list(versions):
                v.is_current = False
                await self._version_store.save_version(v)

            await self._version_store.save_version(version)

            # Publish event
            await self._events.publish("EpistemicProfileRegenerated", {
                "profile_id": str(profile.id),
                "book_id": book_id,
                "version": next_version,
                "domain": profile.discipline,
                "framework": profile.framework,
            })

            duration_ms = (time.monotonic() - start) * 1000

            logger.info(
                "profile_regeneration_complete",
                profile_id=str(profile.id),
                version=next_version,
                duration_ms=round(duration_ms, 2),
            )

            return GenerationResult(
                status=GenerationStatus.COMPLETED,
                profile_id=str(profile.id),
                version=next_version,
                validation=validation,
                metadata=metadata,
            )

        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            error_msg = str(exc)
            logger.exception("profile_regeneration_failed", book_id=book_id, error=error_msg)

            return GenerationResult(
                status=GenerationStatus.FAILED,
                error=error_msg,
                metadata=GenerationMetadata(analysis_duration_ms=duration_ms),
            )

    async def get_profile(self, book_id: str) -> EpistemicProfile | None:
        """Get the current epistemic profile for a book."""
        return await self._profile_store.get_profile_by_book(book_id)

    async def get_profile_history(self, profile_id: str) -> list[ProfileVersion]:
        """Get the version history of a profile."""
        return await self._version_store.get_versions(profile_id)

    async def validate_profile(self, profile: EpistemicProfile) -> ValidationResult:
        """Validate an existing profile."""
        return self._engine.validate(profile)

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    async def _load_document_context(self, document_id: str) -> DocumentContext | None:
        """Load document context for profile generation."""
        doc = await self._doc_reader.get_document(document_id)
        if doc is None:
            return None

        chapters = await self._doc_reader.get_chapters(document_id)

        return DocumentContext(
            document_id=document_id,
            title=doc.get("title", ""),
            author=doc.get("author", ""),
            language=doc.get("language", "en"),
            chapters=chapters,
            total_pages=doc.get("page_count", 0),
            total_chunks=doc.get("chunk_count", 0),
            metadata=doc.get("metadata", {}),
        )

    def _profile_to_dict(self, profile: EpistemicProfile) -> dict[str, Any]:
        """Convert profile to dictionary for storage."""
        return {
            "id": str(profile.id),
            "book_id": str(profile.book_id),
            "user_id": str(profile.user_id),
            "source": profile.source,
            "tradition": profile.tradition,
            "framework": profile.framework,
            "discipline": profile.discipline,
            "primary_topics": profile.primary_topics,
            "secondary_topics": profile.secondary_topics,
            "supported_questions": profile.supported_questions,
            "unsupported_questions": profile.unsupported_questions,
            "evidence_level": profile.evidence_level,
            "reasoning_style": profile.reasoning_style,
            "authority": profile.authority,
            "claim_types": profile.claim_types,
            "limitations": [
                {"description": l.description, "severity": l.severity, "affected_domains": l.affected_domains}
                for l in profile.limitations
            ],
            "scope_boundary": {
                "included_topics": profile.scope_boundary.included_topics,
                "excluded_topics": profile.scope_boundary.excluded_topics,
                "overlap_notes": profile.scope_boundary.overlap_notes,
            },
            "citation_policy": {
                "required": profile.citation_policy.required,
                "format": profile.citation_policy.format,
                "min_confidence": profile.citation_policy.min_confidence,
            },
            "source_reliability": {
                "score": profile.source_reliability.score,
                "basis": profile.source_reliability.basis,
            },
            "language": profile.language,
        }
