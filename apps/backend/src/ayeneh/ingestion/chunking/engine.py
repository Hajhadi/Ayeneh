"""Chunking engine — splits documents into semantically coherent chunks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from ayeneh.ingestion.parsers.base import Chapter

logger = structlog.get_logger(__name__)


@dataclass
class ChunkingConfig:
    """Configuration for the chunking engine."""

    max_chunk_tokens: int = 512
    overlap_tokens: int = 64
    min_chunk_tokens: int = 50
    preserve_semantic_boundaries: bool = True
    sentence_boundary_tokens: int = 20


@dataclass
class Chunk:
    """A single chunk produced by the chunking engine."""

    content: str
    sequence_number: int
    chapter_title: str = ""
    page_start: int | None = None
    page_end: int | None = None
    token_count: int = 0
    section_heading: str | None = None


class ChunkingEngine:
    """Splits parsed documents into semantically coherent chunks."""

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self._config = config or ChunkingConfig()

    def chunk_document(self, chapters: list[Chapter]) -> list[Chunk]:
        """Split chapters into chunks respecting semantic boundaries."""
        all_chunks: list[Chunk] = []
        sequence = 0

        for chapter in chapters:
            chapter_chunks = self._chunk_text(
                chapter.content,
                chapter.title,
                chapter.page_start,
                chapter.page_end,
                start_sequence=sequence,
            )
            all_chunks.extend(chapter_chunks)
            sequence += len(chapter_chunks)

        return all_chunks

    def _chunk_text(
        self,
        text: str,
        chapter_title: str,
        page_start: int | None,
        page_end: int | None,
        start_sequence: int = 0,
    ) -> list[Chunk]:
        """Split text into chunks respecting token limits and semantic boundaries."""
        if not text.strip():
            return []

        words = text.split()
        if len(words) <= self._config.max_chunk_tokens:
            return [Chunk(
                content=text.strip(),
                sequence_number=start_sequence,
                chapter_title=chapter_title,
                page_start=page_start,
                page_end=page_end,
                token_count=len(words),
                section_heading=chapter_title,
            )]

        chunks: list[Chunk] = []
        sequence = start_sequence
        i = 0

        while i < len(words):
            end = min(i + self._config.max_chunk_tokens, len(words))

            if end < len(words) and self._config.preserve_semantic_boundaries:
                end = self._find_sentence_boundary(words, i, end)

            chunk_words = words[i:end]
            chunk_text = " ".join(chunk_words)

            chunks.append(Chunk(
                content=chunk_text.strip(),
                sequence_number=sequence,
                chapter_title=chapter_title,
                page_start=page_start,
                page_end=page_end,
                token_count=len(chunk_words),
                section_heading=chapter_title,
            ))
            sequence += 1

            advance = max(1, len(chunk_words) - self._config.overlap_tokens)
            i += advance

        return chunks

    def _find_sentence_boundary(self, words: list[str], start: int, end: int) -> int:
        """Find the nearest sentence boundary before end position."""
        sentence_enders = {".", "!", "?"}
        search_range = min(self._config.sentence_boundary_tokens, end - start)

        for j in range(end - 1, end - search_range - 1, -1):
            if j < start:
                break
            if words[j] and words[j][-1] in sentence_enders:
                return j + 1

        return end
