"""EPUB document parser using ebooklib."""

from __future__ import annotations

import contextlib
import re
from html.parser import HTMLParser

import structlog

from ayeneh.ingestion.parsers.base import Chapter, DocumentParser, ParsedDocument

logger = structlog.get_logger(__name__)


class _HTMLTextExtractor(HTMLParser):
    """Strip HTML tags and extract plain text."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = False
        if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "li"):
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


class EPUBParser(DocumentParser):
    """Parse EPUB documents into structured text with chapter detection."""

    @property
    def supported_formats(self) -> list[str]:
        return ["epub"]

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        import io

        import ebooklib
        from ebooklib import epub

        book = epub.read_epub(io.BytesIO(content))

        title = ""
        try:
            title = book.get_metadata("DC", "title")[0][0]
        except Exception:
            title = filename.rsplit(".", 1)[0].replace("_", " ").title()

        author = ""
        with contextlib.suppress(Exception):
            author = book.get_metadata("DC", "creator")[0][0]

        chapters: list[Chapter] = []
        full_text_parts: list[str] = []
        sequence = 0

        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            html_content = item.get_content().decode("utf-8", errors="replace")
            extractor = _HTMLTextExtractor()
            extractor.feed(html_content)
            text = extractor.get_text().strip()

            if not text:
                continue

            heading = self._detect_heading(text)
            chapters.append(Chapter(
                title=heading or f"Section {sequence + 1}",
                sequence_number=sequence,
                content=text,
            ))
            full_text_parts.append(text)
            sequence += 1

        if not chapters:
            chapters = [Chapter(title="Full Document", sequence_number=0, content="\n".join(full_text_parts))]

        return ParsedDocument(
            title=title,
            author=author or None,
            source_format="epub",
            chapters=chapters,
            full_text="\n".join(full_text_parts),
            metadata={"item_count": sequence},
        )

    def _detect_heading(self, text: str) -> str | None:
        lines = text.strip().split("\n")
        if not lines:
            return None
        first_line = lines[0].strip()
        if len(first_line) < 80 and first_line:
            if any(kw in first_line.lower() for kw in ("chapter", "section", "part", "introduction", "conclusion")):
                return first_line
            if first_line.isupper() and len(first_line) > 3:
                return first_line
        return None
