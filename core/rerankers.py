from __future__ import annotations

import time
from typing import Any, Protocol

import httpx


SUPPORTED_RERANKER_PROVIDERS = {"none", "dashscope"}
DEFAULT_RERANK_INSTRUCT = (
    "Given a scientific literature question, retrieve passages that directly "
    "answer the question with methods, conditions, results, or conclusions."
)


class Reranker(Protocol):
    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        top_n: int,
    ) -> list[dict[str, Any]]: ...


def normalize_reranker_provider(provider: str | None) -> str:
    normalized = (provider or "none").strip().lower()
    aliases = {
        "off": "none",
        "disabled": "none",
        "cloud": "dashscope",
        "bailian": "dashscope",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SUPPORTED_RERANKER_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_RERANKER_PROVIDERS))
        raise ValueError(
            f"Unsupported reranker provider: {provider!r}; supported values: {supported}"
        )
    return normalized


def _candidate_document(item: dict[str, Any], max_chars: int) -> str:
    metadata = item.get("metadata") or {}
    title = str(metadata.get("title") or "").strip()
    section = str(metadata.get("section") or "").strip()
    text = str(item.get("text") or "").strip()
    if not text:
        raise ValueError("Reranker candidate text must not be empty")

    parts = []
    if title:
        parts.append(f"Title: {title}")
    if section:
        parts.append(f"Section: {section}")
    parts.append(f"Passage: {text}")
    return "\n".join(parts)[:max_chars]


class DashScopeReranker:
    """DashScope qwen3-rerank provider with no silent fallback."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str = "qwen3-rerank",
        instruct: str = DEFAULT_RERANK_INSTRUCT,
        timeout_seconds: float = 30.0,
        max_documents: int = 500,
        max_document_chars: int = 8000,
        http_client: Any | None = None,
    ):
        if not api_key or api_key == "your_api_key_here":
            raise ValueError("DashScope reranker requires a valid DASHSCOPE_API_KEY")
        if not base_url:
            raise ValueError("DashScope reranker requires DASHSCOPE_RERANK_BASE_URL")
        if timeout_seconds <= 0:
            raise ValueError("RERANK_TIMEOUT_SECONDS must be greater than 0")
        if max_documents <= 0 or max_documents > 500:
            raise ValueError("RERANK_MAX_DOCUMENTS must be between 1 and 500")
        if max_document_chars <= 0:
            raise ValueError("RERANK_MAX_DOCUMENT_CHARS must be greater than 0")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.instruct = instruct
        self.timeout_seconds = timeout_seconds
        self.max_documents = max_documents
        self.max_document_chars = max_document_chars
        self.http_client = http_client

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_kwargs = {
            "headers": {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            "json": payload,
            "timeout": self.timeout_seconds,
        }
        url = f"{self.base_url}/reranks"
        if self.http_client is None:
            response = httpx.post(url, **request_kwargs)
        else:
            response = self.http_client.post(url, **request_kwargs)

        if response.status_code >= 400:
            detail = str(getattr(response, "text", ""))[:500]
            raise RuntimeError(
                f"DashScope rerank request failed with HTTP {response.status_code}: {detail}"
            )
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("DashScope rerank response must be a JSON object")
        return data

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        top_n: int,
    ) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError("Reranker query must not be empty")
        if top_n <= 0:
            raise ValueError("Reranker top_n must be greater than 0")
        if not candidates:
            return []

        selected = candidates[: self.max_documents]
        documents = [
            _candidate_document(item, self.max_document_chars) for item in selected
        ]
        requested_top_n = min(top_n, len(documents))
        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": requested_top_n,
            "instruct": self.instruct,
        }

        start = time.perf_counter()
        response = self._post(payload)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        raw_results = response.get("results")
        if not isinstance(raw_results, list):
            raise RuntimeError("DashScope rerank response is missing results")
        if len(raw_results) != requested_top_n:
            raise RuntimeError(
                "DashScope rerank returned an unexpected number of results: "
                f"expected {requested_top_n}, got {len(raw_results)}"
            )

        reranked: list[dict[str, Any]] = []
        seen_indexes: set[int] = set()
        for rank, result in enumerate(raw_results, start=1):
            if not isinstance(result, dict):
                raise RuntimeError("DashScope rerank result must be a JSON object")
            index = result.get("index")
            score = result.get("relevance_score")
            if not isinstance(index, int) or not 0 <= index < len(selected):
                raise RuntimeError(f"DashScope rerank returned invalid index: {index!r}")
            if index in seen_indexes:
                raise RuntimeError(f"DashScope rerank returned duplicate index: {index}")
            if not isinstance(score, (int, float)):
                raise RuntimeError(
                    f"DashScope rerank returned invalid relevance_score: {score!r}"
                )
            seen_indexes.add(index)
            original = selected[index]
            reranked.append(
                {
                    **original,
                    "pre_rerank_rank": original.get("rank"),
                    "pre_rerank_score": original.get(
                        "hybrid_score", original.get("score")
                    ),
                    "rerank_score": float(score),
                    "score": float(score),
                    "rank": rank,
                    "reranker_provider": "dashscope",
                    "reranker_model": self.model,
                    "rerank_candidate_count": len(selected),
                    "rerank_latency_ms": latency_ms,
                }
            )
        return reranked


def build_reranker(
    provider: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    instruct: str | None = None,
    timeout_seconds: float | None = None,
    max_documents: int | None = None,
    max_document_chars: int | None = None,
) -> Reranker | None:
    provider = normalize_reranker_provider(provider)
    if provider == "none":
        return None

    from core.config import settings

    return DashScopeReranker(
        api_key=api_key if api_key is not None else (settings.OPENAI_API_KEY or ""),
        base_url=base_url if base_url is not None else settings.RERANK_BASE_URL,
        model=model or settings.RERANK_MODEL,
        instruct=instruct or settings.RERANK_INSTRUCT,
        timeout_seconds=(
            timeout_seconds
            if timeout_seconds is not None
            else settings.RERANK_TIMEOUT_SECONDS
        ),
        max_documents=(
            max_documents
            if max_documents is not None
            else settings.RERANK_MAX_DOCUMENTS
        ),
        max_document_chars=(
            max_document_chars
            if max_document_chars is not None
            else settings.RERANK_MAX_DOCUMENT_CHARS
        ),
    )
