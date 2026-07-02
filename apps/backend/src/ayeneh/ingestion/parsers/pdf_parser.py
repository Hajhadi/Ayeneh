"""PDF document parser using PyMuPDF (fitz)."""

from __future__ import annotations

import structlog

from ayeneh.ingestion.parsers.base import Chapter, DocumentParser, ParsedDocument

logger = structlog.get_logger(__name__)


class PDFParser(DocumentParser):
    """Parse PDF documents into structured text with chapter detection."""

    @property
    def supported_formats(self) -> list[str]:
        return ["pdf"]

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        import fitz

        doc = fitz.open(stream=content, filetype="pdf")
        page_count = len(doc)
        chapters: list[Chapter] = []
        full_text_parts: list[str] = []
        current_chapter_title = "Untitled"
        current_chapter_text: list[str] = []
        sequence = 0

        for page_num in range(page_count):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            if not text.strip():
                continue

            heading = self._detect_heading(text)
            if heading and (not current_chapter_text or heading != current_chapter_title):
                if current_chapter_text:
                    chapters.append(Chapter(
                        title=current_chapter_title,
                        sequence_number=sequence,
                        content="\n".join(current_chapter_text),
                        page_start=page_num - len(current_chapter_text) + 1,
                        page_end=page_num,
                    ))
                    sequence += 1
                current_chapter_title = heading
                current_chapter_text = []

            current_chapter_text.append(text)
            full_text_parts.append(text)

        if current_chapter_text:
            chapters.append(Chapter(
                title=current_chapter_title,
                sequence_number=sequence,
                content="\n".join(current_chapter_text),
            ))

        doc.close()

        if not chapters:
            chapters = [Chapter(title="Full Document", sequence_number=0, content="\n".join(full_text_parts))]

        return ParsedDocument(
            title=self._extract_title(filename, chapters),
            source_format="pdf",
            chapters=chapters,
            full_text="\n".join(full_text_parts),
            metadata={"page_count": page_count},
        )

    def _detect_heading(self, text: str) -> str | None:
        lines = text.strip().split("\n")
        if not lines:
            return None
        first_line = lines[0].strip()
        if len(first_line) < 80 and first_line and not first_line[0].isdigit():
            if any(kw in first_line.lower() for kw in ("chapter", "section", "part", "introduction", "conclusion", "appendix")):
                return first_line
            if first_line.isupper() and len(first_line) > 3:
                return first_line
        return None

    def _extract_title(self, filename: str, chapters: list[Chapter]) -> str:
        if chapters and chapters[0].title != "Full Document":
            return chapters[0].title
        return filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
