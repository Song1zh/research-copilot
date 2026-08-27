from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from core.config import LITERATURE_CORPUS_DIR


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    year: str = ""
    journal: str = ""
    doi: str = ""
    file_path: str = ""
    topic_tags: str = ""
    source_group: str = ""
    category: str = ""
    ingestion_priority: str = ""
    access_status: str = ""
    notes: str = ""

    @property
    def tag_list(self) -> list[str]:
        return [tag.strip() for tag in self.topic_tags.split(";") if tag.strip()]

    @property
    def resolved_file_path(self) -> Path | None:
        if not self.file_path:
            return None
        path = Path(self.file_path)
        if path.is_absolute():
            return path
        return LITERATURE_CORPUS_DIR / path

    @property
    def has_pdf(self) -> bool:
        path = self.resolved_file_path
        return bool(path and path.exists() and path.suffix.lower() == ".pdf" and path.stat().st_size > 0)

    @property
    def source_type(self) -> str:
        return "full_text_pdf" if self.has_pdf else "metadata_only"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _first(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""


def _record_from_manifest(row: dict[str, str]) -> PaperRecord:
    return PaperRecord(
        paper_id=_first(row, "paper_id"),
        title=_first(row, "title"),
        year=_first(row, "year"),
        journal=_first(row, "journal"),
        doi=_first(row, "doi"),
        file_path="",
        topic_tags=_first(row, "topic_tags"),
        source_group="curated_manifest",
        category="curated_seed",
        access_status=_first(row, "access_status"),
        notes=_first(row, "notes", "corpus_role"),
    )


def _record_from_core_inventory(row: dict[str, str]) -> PaperRecord:
    return PaperRecord(
        paper_id=_first(row, "core_id"),
        title=_first(row, "title"),
        year=_first(row, "year"),
        journal=_first(row, "journal"),
        doi=_first(row, "doi"),
        file_path=_first(row, "file_path"),
        topic_tags=_first(row, "topic_tags"),
        source_group=_first(row, "source_group"),
        category=_first(row, "source_group"),
        ingestion_priority="high",
        access_status="local_pdf" if _first(row, "file_path") else "metadata_only",
        notes=_first(row, "notes"),
    )


def _record_from_local_reaxff(row: dict[str, str]) -> PaperRecord:
    return PaperRecord(
        paper_id=_first(row, "local_id"),
        title=_first(row, "title_or_description"),
        file_path=_first(row, "file_path"),
        topic_tags=_first(row, "topic_tags"),
        source_group="local_reaxff",
        category=_first(row, "category"),
        ingestion_priority=_first(row, "ingestion_priority"),
        access_status="local_pdf" if _first(row, "file_path") else "metadata_only",
        notes=_first(row, "notes"),
    )


def _dedupe(records: Iterable[PaperRecord]) -> list[PaperRecord]:
    seen_ids: set[str] = set()
    seen_dois: set[str] = set()
    deduped: list[PaperRecord] = []

    for record in records:
        if not record.paper_id:
            continue
        doi_key = record.doi.lower()
        if record.paper_id in seen_ids:
            continue
        if doi_key and doi_key in seen_dois:
            continue
        seen_ids.add(record.paper_id)
        if doi_key:
            seen_dois.add(doi_key)
        deduped.append(record)
    return deduped


def load_paper_records(
    corpus_root: Path | str = LITERATURE_CORPUS_DIR,
    include_metadata_only: bool = False,
    categories: set[str] | None = None,
    priorities: set[str] | None = None,
) -> list[PaperRecord]:
    root = Path(corpus_root)
    metadata = root / "metadata"

    records: list[PaperRecord] = []
    records.extend(
        _record_from_local_reaxff(row)
        for row in _read_csv(metadata / "local_reaxff" / "local_reaxff_manifest.csv")
    )
    records.extend(_record_from_core_inventory(row) for row in _read_csv(metadata / "core_paper_inventory.csv"))
    records.extend(_record_from_manifest(row) for row in _read_csv(metadata / "paper_manifest.csv"))

    filtered = _dedupe(records)

    if not include_metadata_only:
        filtered = [record for record in filtered if record.has_pdf]
    if categories:
        filtered = [record for record in filtered if record.category in categories or record.source_group in categories]
    if priorities:
        filtered = [record for record in filtered if record.ingestion_priority in priorities]
    return filtered


def summarize_records(records: list[PaperRecord]) -> dict[str, int]:
    return {
        "total": len(records),
        "full_text_pdf": sum(1 for record in records if record.has_pdf),
        "metadata_only": sum(1 for record in records if not record.has_pdf),
        "high_priority": sum(1 for record in records if record.ingestion_priority == "high"),
    }
