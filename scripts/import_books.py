#!/usr/bin/env python3
"""Import books from ~/Downloads/book/ayneh/ using RuleBasedProfileGenerator."""

import os
import sys
import uuid
import sqlite3
import re
import subprocess
import json
from pathlib import Path
from datetime import datetime, UTC

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend', 'src'))

from ayeneh.domain.knowledge_epistemics.generator.engine import RuleBasedProfileGenerator
from ayeneh.domain.knowledge_epistemics.generator.types import DocumentContext

BOOKS_DIR = Path.home() / "Downloads" / "book" / "ayneh"
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'ayeneh.db')
VENV_PYTHON = os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend', '.venv', 'bin', 'python')
DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001'


def extract_text_from_pdf(filepath: Path) -> str:
    try:
        result = subprocess.run(
            [VENV_PYTHON, '-c', f"""
from pypdf import PdfReader
reader = PdfReader('{filepath}')
parts = []
for p in reader.pages:
    t = p.extract_text()
    if t: parts.append(t)
print('\\n\\n'.join(parts))
"""],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except Exception as e:
        print(f"  PDF error: {e}")
        return ""


def extract_text_from_doc(filepath: Path) -> str:
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()[:10000]
    except Exception:
        return ""


def extract_text(filepath: Path) -> str:
    ext = filepath.suffix.lower()
    if ext == '.pdf':
        return extract_text_from_pdf(filepath)
    elif ext in ('.doc', '.docx'):
        return extract_text_from_doc(filepath)
    return ""


def parse_book_title(filepath: Path) -> tuple[str, str]:
    name = filepath.stem
    for suffix in [' - libgen.li', ' - libgen.li (1)', '(1)', '(2)']:
        name = name.replace(suffix, '')
    if ' - ' in name:
        parts = name.split(' - ', 1)
        title, author = parts[0].strip(), parts[1].strip() if len(parts) > 1 else ''
    elif ' by ' in name:
        parts = name.split(' by ', 1)
        title, author = parts[0].strip(), parts[1].strip()
    else:
        title, author = name.strip(), ''
    title = title.replace('_', ' ').replace('.', ' ').strip()
    author = author.replace('_', ' ').replace('.', ' ').strip()
    title = re.sub(r'\[\d+\]', '', title).strip()
    title = re.sub(r'\(\d{4}\)', '', title).strip()
    return title, author


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    if not text:
        return []
    chunks, words = [], text.split()
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if len(chunk.strip()) > 50:
            chunks.append(chunk.strip())
    return chunks


def profile_to_db_params(profile, book_id: str, user_id: str) -> tuple:
    """Convert EpistemicProfile entity to DB insert parameters."""
    def to_str(val) -> str:
        if val is None:
            return ''
        if hasattr(val, 'value'):
            return val.value
        if isinstance(val, list):
            return json.dumps([v.value if hasattr(v, 'value') else str(v) for v in val])
        return str(val)

    def to_list_str(val) -> str:
        if isinstance(val, list):
            items = []
            for v in val:
                if hasattr(v, 'value'):
                    items.append(v.value)
                elif isinstance(v, dict):
                    items.append({k: (v2.value if hasattr(v2, 'value') else v2) for k, v2 in v.items()})
                else:
                    items.append(str(v))
            return json.dumps(items)
        return str(val) if val else '[]'

    limitations = []
    for lim in (profile.limitations or []):
        limitations.append({
            'description': lim.description,
            'severity': lim.severity,
            'affected_domains': lim.affected_domains,
        })

    scope = profile.scope_boundary
    scope_boundary = json.dumps({
        'included_topics': scope.included_topics if scope else [],
        'excluded_topics': scope.excluded_topics if scope else [],
        'overlap_notes': scope.overlap_notes if scope else [],
    })

    citation = profile.citation_policy
    citation_policy = json.dumps({
        'required': citation.required if citation else True,
        'format': citation.format if citation else 'inline',
        'min_confidence': citation.min_confidence if citation else 0.5,
    })

    reliability = profile.source_reliability
    source_reliability = json.dumps({
        'score': reliability.score if reliability else 0.5,
        'basis': reliability.basis if reliability else 'mixed',
    })

    applicability = profile.applicability
    applicability_str = json.dumps({
        'contexts': applicability.contexts if applicability else [],
        'conditions': applicability.conditions if applicability else [],
        'contraindications': applicability.contraindications if applicability else [],
    })

    return (
        str(profile.id) if isinstance(profile.id, uuid.UUID) else str(profile.id),
        book_id,
        user_id,
        to_str(profile.source),
        to_str(profile.tradition),
        to_str(profile.framework),
        to_str(profile.discipline),
        json.dumps(profile.primary_topics or []),
        json.dumps(profile.secondary_topics or []),
        json.dumps(profile.supported_questions or []),
        json.dumps(profile.unsupported_questions or []),
        to_str(profile.evidence_level),
        to_str(profile.reasoning_style),
        to_str(profile.authority),
        to_list_str(profile.claim_types),
        applicability_str,
        json.dumps(limitations),
        scope_boundary,
        citation_policy,
        'standard',
        'negotiate',
        json.dumps([]),
        source_reliability,
        profile.historical_period or 'modern',
        profile.language or 'en',
        '',
    )


def main():
    print("=" * 60)
    print("Ayeneh Book Import (RuleBasedProfileGenerator)")
    print("=" * 60)

    if not BOOKS_DIR.exists():
        print(f"ERROR: {BOOKS_DIR} not found")
        return

    book_files = list(BOOKS_DIR.glob("*.pdf")) + list(BOOKS_DIR.glob("*.doc")) + list(BOOKS_DIR.glob("*.docx"))
    print(f"Found {len(book_files)} book files\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM books WHERE deleted_at IS NULL")
    print(f"Existing books: {cursor.fetchone()[0]}\n")

    generator = RuleBasedProfileGenerator()
    imported, skipped = 0, 0

    for filepath in sorted(book_files):
        title, author = parse_book_title(filepath)
        if not title:
            print(f"  SKIP: {filepath.name}")
            skipped += 1
            continue

        cursor.execute("SELECT id FROM books WHERE title = ? AND deleted_at IS NULL", (title,))
        if cursor.fetchone():
            print(f"  SKIP: {title[:50]}...")
            skipped += 1
            continue

        print(f"  {title[:60]}...")
        text = extract_text(filepath)
        chunks = chunk_text(text)

        book_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            INSERT INTO books (id, user_id, title, author, source_format, status, chunk_count, metadata, imported_at, created_at, deleted_at)
            VALUES (?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?, NULL)
        """, (book_id, DEFAULT_USER_ID, title, author or 'Unknown',
              filepath.suffix.lower().replace('.', ''), len(chunks),
              json.dumps({"file": filepath.name}),
              now, now))

        chapters_for_generator = []
        for i, ct in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            chapter_id = str(uuid.uuid4())
            tc = len(ct.split())

            cursor.execute("""
                INSERT INTO book_chapters (id, book_id, title, sequence_number, page_start, page_end, created_at, deleted_at)
                VALUES (?, ?, ?, ?, 0, 0, ?, NULL)
            """, (chapter_id, book_id, f"Chapter {i+1}", i+1, now))

            cursor.execute("""
                INSERT INTO book_chunks (id, book_id, chapter_id, content, sequence_number, page_start, page_end, section_heading, token_count, created_at, deleted_at)
                VALUES (?, ?, ?, ?, ?, 0, 0, '', ?, ?, NULL)
            """, (chunk_id, book_id, chapter_id, ct, i+1, tc, now))

            chapters_for_generator.append({
                "content": ct,
                "token_count": tc,
                "chapter_id": chapter_id,
                "sequence_number": i + 1,
            })

        doc_context = DocumentContext(
            document_id=book_id,
            title=title,
            author=author or 'Unknown',
            language='en',
            chapters=chapters_for_generator,
            total_chunks=len(chunks),
        )

        profile, metadata = generator.generate(doc_context, book_id, DEFAULT_USER_ID)
        validation = generator.validate(profile)

        profile_id = str(profile.id) if isinstance(profile.id, uuid.UUID) else str(profile.id)
        db_params = profile_to_db_params(profile, book_id, DEFAULT_USER_ID)

        cursor.execute("""
            INSERT INTO epistemic_profiles (
                id, book_id, user_id, source, tradition, framework, discipline,
                primary_topics, secondary_topics, supported_questions, unsupported_questions,
                evidence_level, reasoning_style, authority, claim_types, applicability,
                limitations, scope_boundary, citation_policy, confidence_policy,
                conflict_policy, priority_hints, source_reliability, historical_period,
                language, translation_metadata, created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """, (*db_params, now, now))

        fw = profile.framework.value if hasattr(profile.framework, 'value') else str(profile.framework)
        dm = profile.discipline.value if hasattr(profile.discipline, 'value') else str(profile.discipline)
        ev = profile.evidence_level.value if hasattr(profile.evidence_level, 'value') else str(profile.evidence_level)
        rs = profile.reasoning_style.value if hasattr(profile.reasoning_style, 'value') else str(profile.reasoning_style)

        valid_str = "✓" if validation.is_valid else f"✗ ({', '.join(validation.errors[:2])})"
        print(f"    -> {len(chunks)} chunks | {fw}/{dm} | {ev}/{rs} | {valid_str}")
        imported += 1

    conn.commit()
    conn.close()
    print(f"\n{'='*60}\nDone! Imported: {imported} | Skipped: {skipped}\n{'='*60}")


if __name__ == "__main__":
    main()
