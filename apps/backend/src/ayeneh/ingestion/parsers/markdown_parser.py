"""Markdown document parser."""

from __future__ import annotations

import re

import structlog

from ayeneh.ingestion.parsers.base import Chapter, DocumentParser, ParsedDocument

logger = structlog.get_logger(__name__)


class MarkdownParser(DocumentParser):
    """Parse Markdown documents with heading-based chapter detection."""

    @property
    def supported_formats(self) -> list[str]:
        return ["md", "markdown"]

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        text = content.decode("utf-8", errors="replace")
        title = self._extract_title(text, filename)
        chapters = self._split_by_headings(text)

        if not chapters:
            chapters = [Chapter(title="Full Document", sequence_number=0, content=text)]

        return ParsedDocument(
            title=title,
            source_format="markdown",
            chapters=chapters,
            full_text=text,
            metadata={"heading_count": len(chapters)},
        )

    def _extract_title(self, text: str, filename: str) -> str:
        match = re.match(r"^#\s+(.+)", text, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()

    def _split_by_headings(self, text: str) -> list[Chapter]:
        chapters: list[Chapter] = []
        heading_pattern = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
        matches = list(heading_pattern.finditer(text))

        if not matches:
            return []

        for i, match in enumerate(matches):
            title = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            chapter_text = text[start:end].strip()
            if chapter_text:
                chapters.append(Chapter(
                    title=title,
                    sequence_number=i,
                    content=chapter_text,
                ))

        if not chapters:
            pre_content = text[: matches[0].start()].strip()
            if pre_content:
                chapters.insert(0, Chapter(title="Introduction", sequence_number=0, content=pre_content))

        return chapters
