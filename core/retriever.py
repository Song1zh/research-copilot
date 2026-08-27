from typing import Any

from core.vector_store import ChromaVectorStore

# 将distance（越小越相似）转换成score（越大越相似）
def _distance_to_store(distance:float | None) -> float | None:
    if distance is None:
        return None
    return 1.0/(1.0 + distance)

# 统一检索接口
def retrieve_evidence(
        query: str,
        top_k: int = 3,
        db_path: str = "./chroma_db",
        collection_name: str = "demo_chunks",
        metadata_filter: dict[str, Any] | None = None,
        embedding_provider: str | None = None,
) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("query 不能为空")
    if top_k <= 0:
        raise ValueError("top_k 必须大于0")

    store = ChromaVectorStore(
        db_path=db_path,
        collection_name=collection_name,
        embedding_provider=embedding_provider,
    )

    results = store.query(query_text=query, top_k=top_k, where=metadata_filter)

    evidence_list = []
    for rank, item in enumerate(results, start=1):
        raw_distance = item.get("distance")
        score = _distance_to_store(raw_distance)

        evidence_list.append(
            {
                "rank": rank,
                "score": score,
                "raw_distance": raw_distance,
                "text": item.get("text",""),
                "metadata": item.get("metadata",{}),
            }
        )
    return evidence_list
