from __future__ import annotations

import re
from typing import Any

from openai import OpenAI


SUPPORTED_EMBEDDING_PROVIDERS = {"local_hash", "dashscope"}


def normalize_embedding_provider(provider: str | None) -> str:
    normalized = (provider or "local_hash").strip().lower()
    aliases = {
        "hash": "local_hash",
        "local": "local_hash",
        "cloud": "dashscope",
        "bailian": "dashscope",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SUPPORTED_EMBEDDING_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_EMBEDDING_PROVIDERS))
        raise ValueError(f"不支持的 embedding provider: {provider!r}；可选值：{supported}")
    return normalized


def _safe_collection_token(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip()).strip("_").lower()
    return normalized or "default"


def collection_name_for_provider(
    base_name: str,
    provider: str,
    *,
    model: str = "text-embedding-v4",
    dimensions: int = 1024,
    local_dimensions: int = 64,
) -> str:
    provider = normalize_embedding_provider(provider)
    if provider == "local_hash":
        suffix = f"local_hash_{local_dimensions}"
    else:
        suffix = f"dashscope_{_safe_collection_token(model)}_{dimensions}"
    marker = f"__{suffix}"
    return base_name if base_name.endswith(marker) else f"{base_name}{marker}"


class LocalHashEmbeddingFunction:
    """Small deterministic embedding for offline demos and tests."""

    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions

    @staticmethod
    def name() -> str:
        return "local_hash_embedding"

    def get_config(self) -> dict[str, Any]:
        return {"dimensions": self.dimensions}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "LocalHashEmbeddingFunction":
        return LocalHashEmbeddingFunction(dimensions=int(config.get("dimensions", 64)))

    def __call__(self, input: list[str]) -> list[list[float]]:
        import hashlib
        import math

        vectors: list[list[float]] = []
        for text in input:
            vector = [0.0] * self.dimensions
            tokens = re.findall(
                r"[A-Za-z][A-Za-z0-9\-+/]*|\d+(?:\.\d+)?|[\u4e00-\u9fff]",
                text.lower(),
            )
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:4], "big") % self.dimensions
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vector[idx] += sign
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self(input)

    def embed_query(self, input: str | list[str]) -> list[float] | list[list[float]]:
        if isinstance(input, list):
            return self(input)
        return self([input])[0]


class DashScopeEmbeddingFunction:
    """OpenAI-compatible DashScope text embedding with explicit batching.

    The API key is intentionally excluded from Chroma's persisted config.
    Missing credentials or request failures are surfaced to callers; this
    provider never silently falls back to the local hash implementation.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str = "text-embedding-v4",
        dimensions: int = 1024,
        batch_size: int = 10,
        client: Any | None = None,
    ):
        if not api_key or api_key == "your_api_key_here":
            raise ValueError("DashScope embedding 需要有效的 DASHSCOPE_API_KEY")
        if not base_url:
            raise ValueError("DashScope embedding 需要 OPENAI_BASE_URL")
        if dimensions <= 0:
            raise ValueError("EMBEDDING_DIMENSIONS 必须大于 0")
        if batch_size <= 0:
            raise ValueError("EMBEDDING_BATCH_SIZE 必须大于 0")

        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.client = client or OpenAI(api_key=api_key, base_url=base_url)

    @staticmethod
    def name() -> str:
        return "dashscope_openai_embedding"

    def get_config(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "model": self.model,
            "dimensions": self.dimensions,
            "batch_size": self.batch_size,
        }

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "DashScopeEmbeddingFunction":
        from core.config import settings

        return DashScopeEmbeddingFunction(
            api_key=settings.OPENAI_API_KEY or "",
            base_url=str(config.get("base_url") or settings.OPENAI_BASE_URL or ""),
            model=str(config.get("model") or settings.EMBEDDING_MODEL),
            dimensions=int(config.get("dimensions") or settings.EMBEDDING_DIMENSIONS),
            batch_size=int(config.get("batch_size") or settings.EMBEDDING_BATCH_SIZE),
        )

    def __call__(self, input: list[str]) -> list[list[float]]:
        texts = list(input)
        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions,
                encoding_format="float",
            )
            ordered = sorted(response.data, key=lambda item: item.index)
            batch_vectors = [list(item.embedding) for item in ordered]
            if len(batch_vectors) != len(batch):
                raise RuntimeError(
                    f"DashScope embedding 返回数量异常：输入 {len(batch)}，输出 {len(batch_vectors)}"
                )
            vectors.extend(batch_vectors)
        return vectors

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self(input)

    def embed_query(self, input: str | list[str]) -> list[float] | list[list[float]]:
        if isinstance(input, list):
            return self(input)
        return self([input])[0]


def build_embedding_function(
    provider: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = "text-embedding-v4",
    dimensions: int = 1024,
    batch_size: int = 10,
    local_dimensions: int = 64,
) -> LocalHashEmbeddingFunction | DashScopeEmbeddingFunction:
    provider = normalize_embedding_provider(provider)
    if provider == "local_hash":
        return LocalHashEmbeddingFunction(dimensions=local_dimensions)
    return DashScopeEmbeddingFunction(
        api_key=api_key or "",
        base_url=base_url or "",
        model=model,
        dimensions=dimensions,
        batch_size=batch_size,
    )
