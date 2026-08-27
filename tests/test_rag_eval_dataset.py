import json
from collections import Counter
from pathlib import Path


DATASET = Path(__file__).resolve().parent.parent / "docs" / "eval" / "rag_eval_v1.jsonl"


def test_rag_eval_v1_has_expected_shape_and_distribution():
    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]

    assert len(rows) == 50
    assert len({row["question_id"] for row in rows}) == 50
    assert Counter(row["split"] for row in rows) == {"dev": 30, "test": 20}
    assert Counter(row["category"] for row in rows) == {
        "exact_lookup": 8,
        "method": 10,
        "mechanism_finding": 10,
        "comparison": 10,
        "graph_relation": 6,
        "refusal": 6,
    }
    for row in rows:
        assert row["question"]
        assert row["reference_answer"]
        assert row["required_claims"]
        if row["should_refuse"]:
            assert row["relevant_paper_ids"] == []
            assert row["relevant_chunk_ids"] == []
        else:
            assert row["relevant_paper_ids"]
            assert len(row["relevant_chunk_ids"]) == len(row["relevant_paper_ids"])
            assert all(":" in value for value in row["relevant_chunk_ids"])
