from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.config import CHROMA_DB_PATH, LITERATURE_CHROMA_COLLECTION, LITERATURE_CORPUS_DIR
from core.literature_manifest import PaperRecord, load_paper_records, summarize_records
from core.paper_loader import load_paper_document
from core.section_splitter import PaperChunk, split_paper_document
from core.vector_store import ChromaVectorStore


@dataclass
class LiteratureIndexResult:
    paper_count: int
    full_text_count: int
    metadata_only_count: int
    skipped_metadata_only_count: int
    chunk_count: int
    collection_name: str
    embedding_provider: str


def chunks_to_vector_records(chunks: list[PaperChunk]) -> list[dict[str, Any]]:
    return [
        {
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
            "metadata": chunk.metadata,
        }
        for chunk in chunks
    ]


def build_paper_chunks(
    records: list[PaperRecord],
    max_papers: int | None = None,
    include_metadata_only: bool = False,
) -> list[PaperChunk]:
    selected = records[:max_papers] if max_papers else records
    chunks: list[PaperChunk] = []
    for record in selected:
        if not record.has_pdf:
            continue
        doc = load_paper_document(record)
        chunks.extend(split_paper_document(doc))
    return chunks


def index_literature_corpus(
    corpus_root: Path | str = LITERATURE_CORPUS_DIR,
    db_path: Path | str = CHROMA_DB_PATH,
    collection_name: str = LITERATURE_CHROMA_COLLECTION,
    max_papers: int | None = None,
    include_metadata_only: bool = False,
    categories: set[str] | None = None,
    priorities: set[str] | None = None,
    embedding_provider: str | None = None,
) -> LiteratureIndexResult:
    # The active literature knowledge base is intentionally PDF-only.
    # include_metadata_only is kept for backward-compatible callers, but
    # metadata-only records are counted as skipped candidates, not indexed.
    all_records = load_paper_records(
        corpus_root=corpus_root,
        include_metadata_only=True,
        categories=categories,
        priorities=priorities,
    )
    records = load_paper_records(
        corpus_root=corpus_root,
        include_metadata_only=False,
        categories=categories,
        priorities=priorities,
    )
    skipped_metadata_only_count = max(len(all_records) - len(records), 0)
    if max_papers:
        records = records[:max_papers]

    chunks = build_paper_chunks(records, include_metadata_only=include_metadata_only)

    if chunks:
        store = ChromaVectorStore(
            db_path=str(db_path),
            collection_name=collection_name,
            embedding_provider=embedding_provider,
        )
        store.upsert_chunks(chunks_to_vector_records(chunks))
        resolved_collection_name = store.collection_name
        resolved_provider = store.embedding_provider
    else:
        empty_store = ChromaVectorStore(
            db_path=str(db_path),
            collection_name=collection_name,
            embedding_provider=embedding_provider,
        )
        resolved_collection_name = empty_store.collection_name
        resolved_provider = empty_store.embedding_provider

    summary = summarize_records(records)
    return LiteratureIndexResult(
        paper_count=summary["total"],
        full_text_count=summary["full_text_pdf"],
        metadata_only_count=skipped_metadata_only_count,
        skipped_metadata_only_count=skipped_metadata_only_count,
        chunk_count=len(chunks),
        collection_name=resolved_collection_name,
        embedding_provider=resolved_provider,
    )
