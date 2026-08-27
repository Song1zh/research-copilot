import json
from pathlib import Path


DATASET = Path(__file__).resolve().parents[1] / "docs" / "eval" / "graph_eval_v1.jsonl"


def _load_rows() -> list[dict]:
    return [
        json.loads(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_graph_eval_dataset_has_balanced_tasks_and_unique_ids():
    rows = _load_rows()
    assert len(rows) == 20
    assert len({row["question_id"] for row in rows}) == 20
    assert sum(row["graph_task"] == "single_hop" for row in rows) == 8
    assert sum(row["graph_task"] == "two_constraint" for row in rows) == 8
    assert sum(row["graph_task"] == "multi_constraint" for row in rows) == 4


def test_graph_eval_gold_relations_cover_every_paper_and_term():
    for row in _load_rows():
        assert row["category"] == "graph_relation"
        assert row["should_refuse"] is False
        assert row["gold_relations"]
        for paper_id in row["relevant_paper_ids"]:
            matched_terms = {
                item["matched_term"].lower()
                for item in row["gold_relations"]
                if item["paper_id"] == paper_id
            }
            assert matched_terms == {term.lower() for term in row["entity_terms"]}
