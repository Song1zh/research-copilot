import pytest

from scripts.run_retrieval_ablation import (
    retrieve_for_strategy,
    run_configuration,
)


@pytest.mark.parametrize(
    ("strategy", "expected"),
    [
        ("vector", "vector"),
        ("bm25", "bm25"),
        ("hybrid", "hybrid"),
        ("hybrid_rerank", "hybrid_rerank"),
    ],
)
def test_run_configuration_routes_each_strategy(strategy, expected):
    calls = []

    def fake_retrieve(**kwargs):
        calls.append(kwargs)
        return [
            {
                "metadata": {"paper_id": "P1", "chunk_id": 1},
                "text": "evidence",
            }
        ]

    questions = [
        {
            "question_id": "Q1",
            "question": "question",
            "relevant_paper_ids": ["P1"],
            "should_refuse": False,
            "split": "test",
            "category": "fact",
        }
    ]
    report = run_configuration(
        questions,
        strategy=strategy,
        embedding_provider="local_hash",
        collection_name="test",
        retrieve=fake_retrieve,
    )

    assert calls[0]["strategy"] == expected
    assert report["summary"]["hit_at_5"] == 1.0
    assert report["summary"]["recall_at_5"] == 1.0
    assert report["summary"]["failures"] == 0


def test_unknown_retrieval_strategy_is_rejected():
    with pytest.raises(ValueError, match="unsupported retrieval strategy"):
        retrieve_for_strategy(
            strategy="automatic",
            query="RDX",
            top_k=5,
            embedding_provider="local_hash",
            collection_name="test",
            db_path=":memory:",
        )


def test_refusal_questions_are_not_scored_as_retrieval_failures():
    report = run_configuration(
        [
            {
                "question_id": "R1",
                "question": "unknown",
                "relevant_paper_ids": [],
                "should_refuse": True,
            }
        ],
        strategy="bm25",
        embedding_provider="local_hash",
        collection_name="test",
        retrieve=lambda **_: [],
    )
    assert report["summary"]["queries"] == 0
    assert report["summary"]["failures"] == 0
