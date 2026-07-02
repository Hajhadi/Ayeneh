"""Base parser contract and shared document structures."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chapter:
    """A detected chapter within a document."""

    title: str
    sequence_number: int
    content: str
    page_start: int | None = None
    page_end: int | None = None
    text_source: str = "native"  # "native" | "ocr" | "mixed"


@dataclass
class ParsedDocument:
    """Result of parsing a document — raw text organized by chapters."""

    title: str
    author: str | None = None
    source_format: str = "unknown"
    chapters: list[Chapter] = field(default_factory=list)
    full_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    text_source: str = "native"  # "native" | "ocr" | "mixed"


class DocumentParser(ABC):
    """Abstract base for document parsers."""

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """Return list of supported file extensions."""

    @abstractmethod
    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        """Parse raw document bytes into a ParsedDocument."""
