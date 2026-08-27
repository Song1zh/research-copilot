import pytest

from scripts.summarize_lab_pilot import markdown_report, summarize_pilot


def pilot_row(**updates):
    row = {
        "session_id": "S1",
        "participant_id": "U1",
        "role": "graduate_student",
        "submitted_at": "2026-08-25T12:00:00",
        "question_id": "Q1",
        "question": "Which paper studies RDX?",
        "solved": "yes",
        "answer_usefulness": "4",
        "evidence_usefulness": "5",
        "completion_seconds": "30",
        "failure_type": "none",
        "notes": "",
        "consent": "yes",
    }
    row.update(updates)
    return row


def test_empty_pilot_never_fabricates_success_metrics():
    summary = summarize_pilot([])
    assert summary["status"] == "no_completed_sessions"
    assert "task_success_rate" not in summary
    assert "不能生成成功率" in markdown_report(summary)


def test_real_pilot_summary_uses_submitted_rows():
    summary = summarize_pilot(
        [pilot_row(), pilot_row(question_id="Q2", solved="no", failure_type="retrieval")]
    )
    assert summary["participants"] == 1
    assert summary["sessions"] == 1
    assert summary["questions"] == 2
    assert summary["task_success_rate"] == 0.5
    assert summary["failure_types"] == {"none": 1, "retrieval": 1}


def test_pilot_requires_consent_and_valid_ratings():
    with pytest.raises(ValueError, match="consent"):
        summarize_pilot([pilot_row(consent="no")])
    with pytest.raises(ValueError, match="1 to 5"):
        summarize_pilot([pilot_row(answer_usefulness="6")])
