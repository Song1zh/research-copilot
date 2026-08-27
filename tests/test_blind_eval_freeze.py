import pytest

from scripts.freeze_blind_eval import build_frozen_rows


def question(question_id="B01"):
    return {
        "question_id": question_id,
        "question": "Which paper studies RDX?",
        "category": "lookup",
        "difficulty": "medium",
    }


def gold(question_id="B01"):
    return {
        "question_id": question_id,
        "relevant_paper_ids": "P1",
        "relevant_chunk_ids": "P1:1",
        "reference_answer": "P1 studies RDX.",
        "required_claims": "P1;RDX",
        "expected_terms": "rdx",
        "should_refuse": "false",
        "annotator_id": "lab-1",
        "evidence_reviewed": "true",
    }


def test_blind_eval_requires_independent_gold_for_every_question():
    with pytest.raises(ValueError, match="id mismatch"):
        build_frozen_rows([question()], [], minimum_questions=1)


def test_refusal_gold_cannot_contain_relevant_papers():
    row = gold()
    row["should_refuse"] = "true"
    with pytest.raises(ValueError, match="refusal"):
        build_frozen_rows([question()], [row], minimum_questions=1)


def test_blind_eval_builds_frozen_blind_test_rows():
    rows = build_frozen_rows([question()], [gold()], minimum_questions=1)
    assert rows[0]["split"] == "blind_test"
    assert rows[0]["annotation_basis"] == "independent_lab_annotation_v1"
    assert rows[0]["relevant_paper_ids"] == ["P1"]
