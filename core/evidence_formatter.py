import re
from typing import Any


def _clean_snippet(text: str, max_len: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


def build_evidence_items(
    retrieved_evidence: list[dict[str, Any]],
    snippet_len: int = 180,
) -> list[dict[str, Any]]:
    formatted = []

    for idx, item in enumerate(retrieved_evidence, start=1):
        item_metadata = item.get("metadata", {})

        formatted.append(
            {
                "evidence_id": f"E{idx}",
                "chunk_id": item_metadata.get("chunk_id", "unknown"),
                "source_path": item_metadata.get("source_path", "unknown"),
                "snippet": _clean_snippet(item.get("text", ""), max_len=snippet_len),
                "paper_id": item_metadata.get("paper_id", ""),
                "title": item_metadata.get("title", ""),
                "section": item_metadata.get("section", ""),
                "rank": item.get("rank"),
                "hybrid_score": item.get("hybrid_score"),
                "pre_rerank_rank": item.get("pre_rerank_rank"),
                "pre_rerank_score": item.get("pre_rerank_score"),
                "rerank_score": item.get("rerank_score"),
                "reranker_model": item.get("reranker_model"),
                "rerank_candidate_count": item.get("rerank_candidate_count"),
                "rerank_latency_ms": item.get("rerank_latency_ms"),
            }
        )

    return formatted
