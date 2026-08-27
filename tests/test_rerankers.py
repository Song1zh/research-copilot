from __future__ import annotations

from types import SimpleNamespace

import pytest

import core.hybrid_retriever as hybrid_module
from core.hybrid_retriever import retrieve_hybrid_evidence
from core.evidence_formatter import build_evidence_items
from core.rerankers import DashScopeReranker, normalize_reranker_provider


def _candidate(chunk_id: str, score: float) -> dict:
    return {
        "text": f"passage {chunk_id}",
        "metadata": {
            "paper_id": "P1",
            "chunk_id": chunk_id,
            "title": "RDX decomposition",
            "section": "results",
        },
        "hybrid_score": score,
        "score": score,
        "rank": int(chunk_id[-1]),
    }


class FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, payload: dict):
        self.payload = payload

    def json(self) -> dict:
        return self.payload


class FakeHttpClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls = []

    def post(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payload)


def test_dashscope_reranker_maps_indexes_and_preserves_first_stage_scores():
    client = FakeHttpClient(
        {
            "results": [
                {"index": 1, "relevance_score": 0.91},
                {"index": 0, "relevance_score": 0.42},
            ]
        }
    )
    reranker = DashScopeReranker(
        api_key="test-key",
        base_url="https://workspace.example/compatible-api/v1",
        http_client=client,
    )

    results = reranker.rerank(
        "Which passage reports RDX decomposition results?",
        [_candidate("C1", 0.8), _candidate("C2", 0.6)],
        top_n=2,
    )

    assert [item["metadata"]["chunk_id"] for item in results] == ["C2", "C1"]
    assert results[0]["rerank_score"] == 0.91
    assert results[0]["pre_rerank_score"] == 0.6
    assert results[0]["reranker_provider"] == "dashscope"
    assert results[0]["rerank_candidate_count"] == 2
    assert client.calls[0][0].endswith("/compatible-api/v1/reranks")
    request = client.calls[0][1]["json"]
    assert request["model"] == "qwen3-rerank"
    assert request["top_n"] == 2
    assert "Title: RDX decomposition" in request["documents"][0]


def test_dashscope_reranker_rejects_missing_credentials_without_fallback():
    with pytest.raises(ValueError, match="DASHSCOPE_API_KEY"):
        DashScopeReranker(
            api_key="",
            base_url="https://workspace.example/compatible-api/v1",
        )


def test_dashscope_reranker_rejects_malformed_indexes():
    reranker = DashScopeReranker(
        api_key="test-key",
        base_url="https://workspace.example/compatible-api/v1",
        http_client=FakeHttpClient(
            {"results": [{"index": 9, "relevance_score": 0.7}]}
        ),
    )
    with pytest.raises(RuntimeError, match="invalid index"):
        reranker.rerank("query", [_candidate("C1", 0.8)], top_n=1)


def test_hybrid_retriever_passes_fused_candidates_to_explicit_reranker(monkeypatch):
    vector = [
        {
            "text": "vector one",
            "metadata": {"paper_id": "P1", "chunk_id": "C1"},
            "score": 0.9,
        },
        {
            "text": "vector two",
            "metadata": {"paper_id": "P2", "chunk_id": "C2"},
            "score": 0.5,
        },
    ]
    keyword = [
        {
            "text": "vector two",
            "metadata": {"paper_id": "P2", "chunk_id": "C2"},
            "score": 2.0,
        }
    ]
    monkeypatch.setattr(hybrid_module, "retrieve_evidence", lambda **_: vector)
    monkeypatch.setattr(
        hybrid_module, "retrieve_keyword_evidence", lambda **_: keyword
    )

    class FakeReranker:
        def __init__(self):
            self.call = None

        def rerank(self, query, candidates, *, top_n):
            self.call = SimpleNamespace(
                query=query, candidates=candidates, top_n=top_n
            )
            return [{**candidates[-1], "rerank_score": 0.99, "rank": 1}]

    fake = FakeReranker()
    results = retrieve_hybrid_evidence(
        "RDX",
        top_k=1,
        reranker_provider="dashscope",
        rerank_candidate_k=30,
        reranker=fake,
    )

    assert results[0]["rerank_score"] == 0.99
    assert fake.call.query == "RDX"
    assert fake.call.top_n == 1
    assert len(fake.call.candidates) == 2


def test_reranker_provider_is_explicit():
    assert normalize_reranker_provider("bailian") == "dashscope"
    assert normalize_reranker_provider("off") == "none"
    with pytest.raises(ValueError, match="Unsupported reranker provider"):
        normalize_reranker_provider("automatic")


def test_rerank_metadata_is_preserved_in_formatted_evidence():
    item = _candidate("C1", 0.8)
    item.update(
        {
            "pre_rerank_rank": 3,
            "pre_rerank_score": 0.8,
            "rerank_score": 0.93,
            "reranker_model": "qwen3-rerank",
            "rerank_candidate_count": 30,
            "rerank_latency_ms": 18.5,
            "rank": 1,
        }
    )

    evidence = build_evidence_items([item])[0]

    assert evidence["paper_id"] == "P1"
    assert evidence["rerank_score"] == 0.93
    assert evidence["pre_rerank_rank"] == 3
    assert evidence["reranker_model"] == "qwen3-rerank"
