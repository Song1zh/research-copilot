from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from core.paper_loader import PaperDocument
from core.text_splitter import split_text


SECTION_PATTERNS = [
    ("abstract", r"^\s*(abstract|摘要)\s*$"),
    ("introduction", r"^\s*(\d+\.?\s*)?(introduction|引言|绪论)\s*$"),
    ("methods", r"^\s*(\d+\.?\s*)?(methods?|methodology|experimental|computational methods?|simulation details?|方法|计算方法|模拟方法)\s*$"),
    ("results", r"^\s*(\d+\.?\s*)?(results?( and discussion)?|discussion|结果.*讨论|结果|讨论)\s*$"),
    ("conclusion", r"^\s*(\d+\.?\s*)?(conclusions?|summary|结论|总结)\s*$"),
    ("references", r"^\s*(references|bibliography|参考文献)\s*$"),
]


@dataclass
class PaperChunk:
    chunk_id: int
    paper_id: str
    title: str
    section: str
    text: str
    metadata: dict[str, Any]


def _detect_section(line: str) -> str | None:
    compact = line.strip()
    if len(compact) > 80:
        return None
    for section, pattern in SECTION_PATTERNS:
        if re.match(pattern, compact, flags=re.IGNORECASE):
            return section
    return None


def split_into_sections(text: str) -> list[tuple[str, str]]:
    current_section = "unknown"
    current_lines: list[str] = []
    sections: list[tuple[str, str]] = []

    for raw_line in text.splitlines():
        detected = _detect_section(raw_line)
        if detected:
            if current_lines:
                sections.append((current_section, "\n".join(current_lines).strip()))
            current_section = detected
            current_lines = [raw_line.strip()]
            continue
        current_lines.append(raw_line)

    if current_lines:
        sections.append((current_section, "\n".join(current_lines).strip()))

    return [(section, body) for section, body in sections if body]


def split_paper_document(
    doc: PaperDocument,
    chunk_size: int = 900,
    chunk_overlap: int = 120,
) -> list[PaperChunk]:
    chunks: list[PaperChunk] = []
    sections = split_into_sections(doc.text)

    for section, section_text in sections:
        if section == "references":
            continue
        raw_chunks = split_text(
            section_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        for raw_chunk in raw_chunks:
            chunk_id = len(chunks)
            metadata = {
                **doc.metadata,
                "chunk_id": chunk_id,
                "paper_id": doc.paper_id,
                "title": doc.title,
                "section": section,
            }
            chunks.append(
                PaperChunk(
                    chunk_id=chunk_id,
                    paper_id=doc.paper_id,
                    title=doc.title,
                    section=section,
                    text=raw_chunk,
                    metadata=metadata,
                )
            )
    return chunks
