from __future__ import annotations

from dataclasses import dataclass

from core.graph_store import Neo4jGraphStore
from core.literature_manifest import PaperRecord
from core.literature_indexer import build_paper_chunks
from core.simulation_extractor import extract_from_chunks


@dataclass
class GraphBuildResult:
    ok: bool
    extraction_count: int
    error: str | None = None


def build_literature_graph(
    records: list[PaperRecord],
    max_papers: int | None = None,
    replace_existing: bool = False,
) -> GraphBuildResult:
    selected = records[:max_papers] if max_papers else records
    chunks = build_paper_chunks(selected, include_metadata_only=False)
    extractions = extract_from_chunks(chunks)

    graph = None
    try:
        graph = Neo4jGraphStore()
        graph.verify()
        if replace_existing:
            graph.clear_project_graph()
        graph.init_constraints()
        record_by_id = {record.paper_id: record for record in selected}
        for extraction in extractions:
            record = record_by_id.get(extraction.paper_id)
            if record is None:
                continue
            graph.upsert_extraction(
                {
                    "paper_id": record.paper_id,
                    "title": record.title,
                    "doi": record.doi,
                    "year": record.year,
                    "journal": record.journal,
                },
                extraction,
            )
        return GraphBuildResult(ok=True, extraction_count=len(extractions))
    except Exception as exc:
        return GraphBuildResult(ok=False, extraction_count=len(extractions), error=str(exc))
    finally:
        if graph is not None:
            graph.close()
