import pytest

import core.kg_retriever as kg_retriever_module
from scripts.run_kg_groundedness_ab import (
    drop_failed_pairs,
    evidence_signature,
    numeric_delta,
    run_ab,
)


def test_none_kg_provider_never_connects_to_neo4j(monkeypatch):
    class ExplodingStore:
        def __init__(self):
            raise AssertionError("Neo4j must not be touched when kg_provider=none")

    monkeypatch.setattr(kg_retriever_module, "Neo4jGraphStore", ExplodingStore)
    result = kg_retriever_module.retrieve_kg_evidence(
        ["RDX"], provider="none"
    )

    assert result == {
        "available": False,
        "disabled": True,
        "provider": "none",
        "items": [],
        "error": None,
    }


def test_unknown_kg_provider_is_rejected():
    with pytest.raises(ValueError, match="unsupported kg provider"):
        kg_retriever_module.normalize_kg_provider("automatic")


def test_evidence_signature_is_paper_and_chunk_stable():
    assert evidence_signature(
        [
            {"metadata": {"paper_id": "P1", "chunk_id": 2}},
            {"metadata": {"paper_id": "P2", "chunk_id": 4}},
        ]
    ) == ["P1:2", "P2:4"]


def test_numeric_delta_reports_neo4j_minus_none():
    enabled = {
        "claim_support_rate": 0.8,
        "weighted_claim_support_rate": 0.9,
        "citation_coverage": 1.0,
        "citation_precision": 1.0,
        "answer_correctness": 0.7,
        "refusal_accuracy": 1.0,
    }
    disabled = {key: 0.5 for key in enabled}
    delta = numeric_delta(enabled, disabled)
    assert delta["claim_support_rate"] == 0.3
    assert delta["answer_correctness"] == 0.2


def test_retry_failures_drops_both_sides_of_failed_pair():
    groups = {
        "none": [
            {"question_id": "Q1", "workflow_error": None, "groundedness": {"judge_error": None}},
            {"question_id": "Q2", "workflow_error": None, "groundedness": {"judge_error": None}},
        ],
        "neo4j": [
            {"question_id": "Q1", "workflow_error": None, "groundedness": {"judge_error": "quota"}},
            {"question_id": "Q2", "workflow_error": None, "groundedness": {"judge_error": None}},
        ],
    }
    filtered, failed_ids = drop_failed_pairs(groups)
    assert failed_ids == {"Q1"}
    assert [row["question_id"] for row in filtered["none"]] == ["Q2"]
    assert [row["question_id"] for row in filtered["neo4j"]] == ["Q2"]


def test_question_worker_count_must_be_positive():
    with pytest.raises(ValueError, match="question_workers"):
        run_ab(
            [],
            embedding_provider="local_hash",
            reranker_provider="none",
            judge_model="fake",
            question_workers=0,
        )
