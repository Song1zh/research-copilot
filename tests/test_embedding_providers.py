from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.main import LiteratureAskRequest, LiteratureIndexRequest
from core.embedding_providers import (
    DashScopeEmbeddingFunction,
    LocalHashEmbeddingFunction,
    collection_name_for_provider,
    normalize_embedding_provider,
)
from scripts.compare_embedding_retrieval import retrieval_metrics, unique_paper_ids


def test_provider_aliases_and_collection_names_are_explicit():
    assert normalize_embedding_provider("hash") == "local_hash"
    assert normalize_embedding_provider("cloud") == "dashscope"
    assert (
        collection_name_for_provider("literature", "local_hash")
        == "literature__local_hash_64"
    )
    assert (
        collection_name_for_provider(
            "literature",
            "dashscope",
            model="text-embedding-v4",
            dimensions=1024,
        )
        == "literature__dashscope_text_embedding_v4_1024"
    )


def test_local_hash_embedding_is_deterministic_and_has_expected_dimension():
    embedding = LocalHashEmbeddingFunction(dimensions=64)
    first = embedding(["RDX ReaxFF"])[0]
    second = embedding(["RDX ReaxFF"])[0]

    assert first == second
    assert len(first) == 64


def test_dashscope_embedding_batches_and_preserves_response_order():
    calls = []

    class FakeEmbeddings:
        def create(self, **kwargs):
            calls.append(kwargs)
            data = [
                SimpleNamespace(index=index, embedding=[float(index), 1.0])
                for index, _ in enumerate(kwargs["input"])
            ]
            return SimpleNamespace(data=list(reversed(data)))

    fake_client = SimpleNamespace(embeddings=FakeEmbeddings())
    embedding = DashScopeEmbeddingFunction(
        api_key="test-key",
        base_url="https://example.test/v1",
        dimensions=2,
        batch_size=2,
        client=fake_client,
    )

    vectors = embedding(["a", "b", "c"])

    assert len(calls) == 2
    assert calls[0]["model"] == "text-embedding-v4"
    assert calls[0]["dimensions"] == 2
    assert vectors == [[0.0, 1.0], [1.0, 1.0], [0.0, 1.0]]


def test_dashscope_embedding_rejects_missing_key_without_fallback():
    with pytest.raises(ValueError, match="DASHSCOPE_API_KEY"):
        DashScopeEmbeddingFunction(
            api_key="",
            base_url="https://example.test/v1",
        )


def test_retrieval_metrics_are_paper_level_at_five():
    results = [
        {"metadata": {"paper_id": "P2"}},
        {"metadata": {"paper_id": "P2"}},
        {"metadata": {"paper_id": "P1"}},
        {"metadata": {"paper_id": "P3"}},
    ]
    ranked = unique_paper_ids(results, limit=5)
    hit, recall, reciprocal_rank = retrieval_metrics(["P1", "P4"], ranked)

    assert ranked == ["P2", "P1", "P3"]
    assert hit == 1.0
    assert recall == 0.5
    assert reciprocal_rank == 0.5


def test_api_embedding_provider_is_explicit_and_validated():
    index_request = LiteratureIndexRequest()
    ask_request = LiteratureAskRequest(query="RDX")

    assert index_request.embedding_provider == "local_hash"
    assert ask_request.embedding_provider == "local_hash"
    assert ask_request.reranker_provider == "dashscope"
    with pytest.raises(ValidationError):
        LiteratureAskRequest(query="RDX", embedding_provider="automatic")
    with pytest.raises(ValidationError):
        LiteratureAskRequest(query="RDX", reranker_provider="automatic")
