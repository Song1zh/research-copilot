from __future__ import annotations

from typing import Any

from core.keyword_retriever import retrieve_keyword_evidence
from core.retriever import retrieve_evidence
from core.rerankers import Reranker, build_reranker, normalize_reranker_provider


def _evidence_key(item: dict[str, Any]) -> str:
    metadata = item.get("metadata", {})
    paper_id = metadata.get("paper_id", "")
    chunk_id = metadata.get("chunk_id", "")
    if paper_id or chunk_id != "":
        return f"{paper_id}::{chunk_id}"
    return item.get("id") or item.get("text", "")[:80]


def _normalize(items: list[dict[str, Any]], score_key: str = "score") -> dict[str, float]:
    scores = [float(item.get(score_key) or 0.0) for item in items]
    if not scores:
        return {}
    max_score = max(scores)
    min_score = min(scores)
    if max_score == min_score:
        return {_evidence_key(item): 1.0 for item in items}
    return {
        _evidence_key(item): (float(item.get(score_key) or 0.0) - min_score) / (max_score - min_score)
        for item in items
    }


def retrieve_hybrid_evidence(
    query: str,
    top_k: int = 5,
    db_path: str = "./chroma_db",
    collection_name: str = "demo_chunks",
    metadata_filter: dict[str, Any] | None = None,
    vector_weight: float = 0.6,
    keyword_weight: float = 0.4,
    embedding_provider: str | None = None,
    reranker_provider: str = "none",
    rerank_candidate_k: int = 30,
    reranker: Reranker | None = None,
) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("query must not be empty")
    if top_k <= 0:
        raise ValueError("top_k must be greater than 0")
    if rerank_candidate_k <= 0:
        raise ValueError("rerank_candidate_k must be greater than 0")

    reranker_provider = normalize_reranker_provider(reranker_provider)
    first_stage_k = (
        max(rerank_candidate_k, top_k)
        if reranker_provider != "none"
        else max(top_k * 2, top_k)
    )
    vector_results = retrieve_evidence(
        query=query,
        top_k=first_stage_k,
        db_path=db_path,
        collection_name=collection_name,
        metadata_filter=metadata_filter,
        embedding_provider=embedding_provider,
    )
    keyword_results = retrieve_keyword_evidence(
        query=query,
        top_k=first_stage_k,
        db_path=db_path,
        collection_name=collection_name,
        metadata_filter=metadata_filter,
        embedding_provider=embedding_provider,
    )

    vector_scores = _normalize(vector_results)
    keyword_scores = _normalize(keyword_results)
    merged: dict[str, dict[str, Any]] = {}

    for item in vector_results:
        key = _evidence_key(item)
        merged[key] = {
            **item,
            "retrieval_source": "vector",
            "vector_score": vector_scores.get(key, 0.0),
            "keyword_score": 0.0,
        }

    for item in keyword_results:
        key = _evidence_key(item)
        if key in merged:
            merged[key]["keyword_score"] = keyword_scores.get(key, 0.0)
            merged[key]["retrieval_source"] = "hybrid"
        else:
            merged[key] = {
                **item,
                "vector_score": 0.0,
                "keyword_score": keyword_scores.get(key, 0.0),
            }

    results = []
    for item in merged.values():
        hybrid_score = vector_weight * item.get("vector_score", 0.0) + keyword_weight * item.get("keyword_score", 0.0)
        results.append({**item, "hybrid_score": hybrid_score, "score": hybrid_score})

    results.sort(key=lambda item: item["hybrid_score"], reverse=True)
    for rank, item in enumerate(results, start=1):
        item["rank"] = rank

    if reranker_provider != "none" and results:
        active_reranker = reranker or build_reranker(reranker_provider)
        if active_reranker is None:
            raise RuntimeError(
                f"Reranker provider {reranker_provider!r} did not build a reranker"
            )
        return active_reranker.rerank(
            query,
            results[:rerank_candidate_k],
            top_n=top_k,
        )

    for item in results[:top_k]:
        item["reranker_provider"] = "none"
    return results[:top_k]
