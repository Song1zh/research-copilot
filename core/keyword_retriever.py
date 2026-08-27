from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from core.vector_store import ChromaVectorStore


TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9\-+/]*|\d+(?:\.\d+)?")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def metadata_matches(metadata: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    for key, expected in filters.items():
        actual = metadata.get(key)
        if actual is None:
            return False
        if str(expected).lower() not in str(actual).lower():
            return False
    return True


def keyword_search_chunks(
    query: str,
    chunks: list[dict[str, Any]],
    top_k: int = 5,
    metadata_filter: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("query 不能为空")
    if top_k <= 0:
        raise ValueError("top_k 必须大于 0")

    filtered_chunks = [
        chunk
        for chunk in chunks
        if metadata_matches(chunk.get("metadata", {}), metadata_filter)
    ]
    if not filtered_chunks:
        return []

    query_terms = tokenize(query)
    if not query_terms:
        return []

    doc_tokens = [tokenize(chunk.get("text", "")) for chunk in filtered_chunks]
    doc_freq: Counter[str] = Counter()
    for tokens in doc_tokens:
        doc_freq.update(set(tokens))

    avg_doc_len = sum(len(tokens) for tokens in doc_tokens) / max(len(doc_tokens), 1)
    k1 = 1.5
    b = 0.75
    total_docs = len(doc_tokens)

    scored: list[dict[str, Any]] = []
    for chunk, tokens in zip(filtered_chunks, doc_tokens):
        term_freq = Counter(tokens)
        doc_len = len(tokens) or 1
        score = 0.0
        for term in query_terms:
            if term_freq[term] == 0:
                continue
            idf = math.log(1 + (total_docs - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            denom = term_freq[term] + k1 * (1 - b + b * doc_len / max(avg_doc_len, 1))
            score += idf * (term_freq[term] * (k1 + 1)) / denom
        if score <= 0:
            continue
        scored.append({**chunk, "keyword_score": score})

    scored.sort(key=lambda item: item["keyword_score"], reverse=True)
    return scored[:top_k]


def retrieve_keyword_evidence(
    query: str,
    top_k: int = 5,
    db_path: str = "./chroma_db",
    collection_name: str = "demo_chunks",
    metadata_filter: dict[str, Any] | None = None,
    embedding_provider: str | None = None,
) -> list[dict[str, Any]]:
    store = ChromaVectorStore(
        db_path=db_path,
        collection_name=collection_name,
        embedding_provider=embedding_provider,
    )
    chunks = store.get_all()
    results = keyword_search_chunks(
        query=query,
        chunks=chunks,
        top_k=top_k,
        metadata_filter=metadata_filter,
    )
    return [
        {
            "rank": rank,
            "score": item["keyword_score"],
            "raw_distance": None,
            "text": item.get("text", ""),
            "metadata": item.get("metadata", {}),
            "retrieval_source": "keyword",
            "id": item.get("id"),
        }
        for rank, item in enumerate(results, start=1)
    ]
