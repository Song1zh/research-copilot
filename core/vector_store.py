from pathlib import Path
from typing import Any

import chromadb

from core.config import settings
from core.embedding_providers import (
    build_embedding_function,
    collection_name_for_provider,
    normalize_embedding_provider,
)

_FALLBACK_CLIENTS: dict[str, Any] = {}

class ChromaVectorStore:
    def __init__(
        self,
        db_path: str = "./chroma_db",
        collection_name: str = "demo_chunks",
        embedding_provider: str | None = None,
    ):
        self.db_path = db_path
        self.embedding_provider = normalize_embedding_provider(
            embedding_provider or settings.EMBEDDING_PROVIDER
        )
        self.collection_base_name = collection_name
        self.collection_name = collection_name_for_provider(
            collection_name,
            self.embedding_provider,
            model=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
            local_dimensions=settings.LOCAL_HASH_DIMENSIONS,
        )
        self.is_persistent = True

        try:
            self.client = chromadb.PersistentClient(path=self.db_path)
        except Exception:
            self.is_persistent = False
            if self.db_path not in _FALLBACK_CLIENTS:
                _FALLBACK_CLIENTS[self.db_path] = chromadb.Client()
            self.client = _FALLBACK_CLIENTS[self.db_path]
        embedding_function = build_embedding_function(
            self.embedding_provider,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            local_dimensions=settings.LOCAL_HASH_DIMENSIONS,
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=embedding_function,
        )

    def upsert_chunks(self, chunks: list[dict[str, Any]]) -> None:
        if not chunks:
            raise ValueError("chunks 不能为空。")

        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            source_path = chunk["metadata"].get("source_path", "unknown")
            paper_id = chunk["metadata"].get("paper_id")
            if paper_id:
                unique_id = f"{paper_id}::chunk_{chunk_id}"
            else:
                unique_id = f"{Path(source_path).name}::chunk_{chunk_id}"

            ids.append(unique_id)
            documents.append(chunk["text"])

            metadata = {
                key: value
                for key, value in dict(chunk["metadata"]).items()
                if value is not None and isinstance(value, (str, int, float, bool))
            }
            metadata["chunk_id"] = chunk_id
            metadatas.append(metadata)

        # 用 upsert 避免重复运行时报 ID 冲突
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    # 调试
    def peek(self, limit: int = 5) -> dict[str, Any]:
        return self.collection.peek(limit=limit)

    def query(
        self,
        query_text: str,
        top_k: int = 3,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not query_text.strip():
            raise ValueError("query_text 不能为空。")
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0。")

        kwargs: dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where

        results = self.collection.query(**kwargs)

        documents = results.get("documents", [[]])[0]
        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        parsed_results = []
        for idx, doc in enumerate(documents):
            parsed_results.append(
                {
                    "id": ids[idx] if idx < len(ids) else None,
                    "text": doc,
                    "metadata": metadatas[idx] if idx < len(metadatas) else {},
                    "distance": distances[idx] if idx < len(distances) else None,
                }
            )

        return parsed_results

    def count(self) -> int:
        return self.collection.count()

    def get_all(self, limit: int | None = None) -> list[dict[str, Any]]:
        total = self.count()
        if total == 0:
            return []
        result_limit = limit or total
        results = self.collection.get(
            limit=result_limit,
            include=["documents", "metadatas"],
        )

        ids = results.get("ids", [])
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])

        return [
            {
                "id": ids[idx],
                "text": documents[idx] if idx < len(documents) else "",
                "metadata": metadatas[idx] if idx < len(metadatas) else {},
            }
            for idx in range(len(ids))
        ]
