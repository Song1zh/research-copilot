from __future__ import annotations

import csv
import json
from pathlib import Path

from core.config import CHROMA_DB_PATH, LITERATURE_CHROMA_COLLECTION, PROJECT_ROOT
from workflows.literature_agent_workflow import run_literature_agent_workflow


QUESTION_PATH = PROJECT_ROOT / "docs" / "eval_literature_questions.csv"
OUT_PATH = PROJECT_ROOT / "app_data" / "eval" / "literature_eval_results.jsonl"


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with QUESTION_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        questions = list(csv.DictReader(f))

    rows = []
    for question in questions:
        result = run_literature_agent_workflow(
            query=question["question"],
            collection_name=LITERATURE_CHROMA_COLLECTION,
            db_path=str(CHROMA_DB_PATH),
        )
        final_output = result.get("final_output", {})
        rows.append(
            {
                "question_id": question["question_id"],
                "question": question["question"],
                "question_type": result.get("question_type"),
                "schema_ok": isinstance(final_output.get("summary"), str),
                "evidence_count": len(final_output.get("evidence", [])),
                "alignment_ok": result.get("alignment_check", {}).get("is_aligned", False),
                "has_limitations": bool(final_output.get("limitations", [])),
                "trace_nodes": [item.get("node") for item in result.get("trace", [])],
            }
        )

    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    total = len(rows)
    aligned = sum(1 for row in rows if row["alignment_ok"])
    with_evidence = sum(1 for row in rows if row["evidence_count"] > 0)
    print(
        json.dumps(
            {
                "total": total,
                "alignment_rate": aligned / total if total else 0,
                "retrieval_hit_rate": with_evidence / total if total else 0,
                "output": str(OUT_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
