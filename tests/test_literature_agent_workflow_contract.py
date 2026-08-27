from pathlib import Path

from workflows.literature_agent_workflow import run_literature_agent_workflow


def test_literature_agent_empty_collection_returns_structured_fallback():
    db_path = Path("dummy_db") / "literature_agent_empty_contract"
    result = run_literature_agent_workflow(
        query="哪些论文涉及 RDX/HTPB 热分解？",
        collection_name="empty_literature_contract_test",
        db_path=str(db_path),
    )

    assert "trace" in result
    assert "final_output" in result
    assert "alignment_check" in result
    assert result["final_output"]["evidence"] == []
    assert result["final_output"]["generation_mode"] == "no_evidence"
    assert result["final_output"]["limitations"]
