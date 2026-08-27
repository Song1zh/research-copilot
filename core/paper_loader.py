from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.document_loader import load_document
from core.literature_manifest import PaperRecord


@dataclass
class PaperDocument:
    paper_id: str
    title: str
    text: str
    metadata: dict[str, Any]


def load_paper_document(record: PaperRecord) -> PaperDocument:
    if record.has_pdf and record.resolved_file_path is not None:
        loaded = load_document(record.resolved_file_path)
        text = loaded.text
        metadata = {
            **loaded.metadata,
            "source_path": str(record.resolved_file_path),
        }
    else:
        text = "\n".join(
            part
            for part in [
                f"Title: {record.title}",
                f"Journal: {record.journal}" if record.journal else "",
                f"Year: {record.year}" if record.year else "",
                f"DOI: {record.doi}" if record.doi else "",
                f"Topic tags: {record.topic_tags}" if record.topic_tags else "",
                f"Notes: {record.notes}" if record.notes else "",
            ]
            if part
        )
        metadata = {
            "source_path": record.file_path or record.paper_id,
            "file_name": record.paper_id,
            "suffix": "",
        }

    return PaperDocument(
        paper_id=record.paper_id,
        title=record.title,
        text=text,
        metadata={
            **metadata,
            "paper_id": record.paper_id,
            "title": record.title,
            "year": record.year,
            "journal": record.journal,
            "doi": record.doi,
            "topic_tags": record.topic_tags,
            "source_group": record.source_group,
            "category": record.category,
            "ingestion_priority": record.ingestion_priority,
            "source_type": record.source_type,
        },
    )
