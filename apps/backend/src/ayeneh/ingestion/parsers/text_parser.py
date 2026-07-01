"""Plain text document parser."""

from __future__ import annotations

import re

import structlog

from ayeneh.ingestion.parsers.base import Chapter, DocumentParser, ParsedDocument

logger = structlog.get_logger(__name__)


class TextParser(DocumentParser):
    """Parse plain text documents with heuristic chapter detection."""

    @property
    def supported_formats(self) -> list[str]:
        return ["txt", "text"]

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        text = content.decode("utf-8", errors="replace")
        title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
        chapters = self._split_by_paragraphs(text)

        if not chapters:
            chapters = [Chapter(title="Full Document", sequence_number=0, content=text)]

        return ParsedDocument(
            title=title,
            source_format="text",
            chapters=chapters,
            full_text=text,
            metadata={"line_count": len(text.splitlines())},
        )

    def _split_by_paragraphs(self, text: str) -> list[Chapter]:
        chapters: list[Chapter] = []
        paragraphs = re.split(r"\n\s*\n", text)
        sequence = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            heading = self._detect_heading(para)
            chapters.append(Chapter(
                title=heading or f"Section {sequence + 1}",
                sequence_number=sequence,
                content=para,
            ))
            sequence += 1

        return chapters

    def _detect_heading(self, text: str) -> str | None:
        lines = text.split("\n")
        if not lines:
            return None
        first_line = lines[0].strip()
        if len(first_line) < 80 and first_line and first_line.isupper():
            return first_line
        return None
