import json

from core.groundedness_evaluator import evaluate_groundedness
from scripts.run_rag_benchmark import ndcg_at_k, retrieval_metrics


def test_groundedness_combines_semantic_and_citation_metrics():
    answer = {
        "summary": "RDX used ReaxFF [E1]. A dosage was proven [E9].",
        "methods": [],
        "findings": [],
        "mechanisms": [],
        "comparison_table": [],
        "evidence": [
            {
                "evidence_id": "E1",
                "paper_id": "P1",
                "chunk_id": 1,
                "snippet": "ReaxFF reactive MD was used for RDX.",
            }
        ],
    }

    def fake_judge(system: str, user: str) -> str:
        assert "strict RAG groundedness" in system
        assert "reference_answer" in user
        return json.dumps(
            {
                "claims": [
                    {
                        "claim": "RDX used ReaxFF",
                        "label": "supported",
                        "evidence_ids": ["E1"],
                        "reason": "direct",
                    },
                    {
                        "claim": "A dosage was proven",
                        "label": "unsupported",
                        "evidence_ids": [],
                        "reason": "missing",
                    },
                ],
                "answer_correctness": 0.5,
                "refusal_correct": None,
            }
        )

    result = evaluate_groundedness(
        question="method?",
        answer=answer,
        reference_answer="ReaxFF",
        required_claims=["ReaxFF"],
        should_refuse=False,
        judge=fake_judge,
    )

    assert result.claim_support_rate == 0.5
    assert result.weighted_claim_support_rate == 0.5
    assert result.citation_coverage == 1.0
    assert result.citation_precision == 0.5
    assert result.answer_correctness == 0.5


def test_groundedness_retries_judge_when_claim_count_mismatches():
    answer = {
        "summary": "RDX used ReaxFF [E1]. CL-20 was compared [E1].",
        "methods": [],
        "findings": [],
        "mechanisms": [],
        "comparison_table": [],
        "evidence": [
            {
                "evidence_id": "E1",
                "paper_id": "P1",
                "chunk_id": 1,
                "snippet": "ReaxFF reactive MD was used for RDX and CL-20.",
            }
        ],
    }
    calls = {"count": 0}

    def flaky_judge(system: str, user: str) -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            return json.dumps(
                {
                    "claims": [
                        {
                            "claim": "RDX used ReaxFF",
                            "label": "supported",
                            "evidence_ids": ["E1"],
                            "reason": "direct",
                        }
                    ],
                    "answer_correctness": 0.25,
                    "refusal_correct": None,
                }
            )
        assert "EXPECTED_CLAIMS" in user
        return json.dumps(
            {
                "claims": [
                    {
                        "claim_index": 0,
                        "claim": "RDX used ReaxFF",
                        "label": "supported",
                        "evidence_ids": ["E1"],
                        "reason": "direct",
                    },
                    {
                        "claim_index": 1,
                        "claim": "CL-20 was compared",
                        "label": "partial",
                        "evidence_ids": ["E1"],
                        "reason": "mentioned but comparison is weak",
                    },
                ],
                "answer_correctness": 0.75,
                "refusal_correct": None,
            }
        )

    result = evaluate_groundedness(
        question="method?",
        answer=answer,
        reference_answer="ReaxFF",
        required_claims=["ReaxFF"],
        should_refuse=False,
        judge=flaky_judge,
    )

    assert calls["count"] == 2
    assert result.supported_claims == 1
    assert result.partial_claims == 1
    assert result.weighted_claim_support_rate == 0.75


def test_retrieval_metrics_include_ndcg():
    ranked = ["P2", "P1", "P4", "P3"]
    metrics = retrieval_metrics(["P1", "P3"], ranked, 5)

    assert metrics["hit_at_5"] == 1.0
    assert metrics["recall_at_5"] == 1.0
    assert metrics["mrr_at_5"] == 0.5
    assert 0.0 < ndcg_at_k(["P1", "P3"], ranked, 5) < 1.0
