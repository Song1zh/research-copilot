from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "docs" / "pilot" / "lab_pilot_sessions.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "app_data" / "pilot"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def parse_rating(value: str, *, field: str) -> int:
    try:
        rating = int(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an integer from 1 to 5") from exc
    if rating not in range(1, 6):
        raise ValueError(f"{field} must be an integer from 1 to 5")
    return rating


def parse_yes_no(value: str, *, field: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"yes", "y", "true", "1"}:
        return True
    if normalized in {"no", "n", "false", "0"}:
        return False
    raise ValueError(f"{field} must be yes or no")


def summarize_pilot(rows: list[dict[str, str]]) -> dict[str, Any]:
    if not rows:
        return {
            "status": "no_completed_sessions",
            "participants": 0,
            "sessions": 0,
            "questions": 0,
            "message": "No real participant data has been submitted.",
        }

    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        required = ("session_id", "participant_id", "role", "question_id", "question")
        missing = [field for field in required if not row.get(field, "").strip()]
        if missing:
            raise ValueError(f"CSV row {index} missing required fields: {missing}")
        consent = parse_yes_no(row.get("consent", ""), field="consent")
        if not consent:
            raise ValueError(f"CSV row {index} does not have participant consent")
        solved = parse_yes_no(row.get("solved", ""), field="solved")
        answer_rating = parse_rating(
            row.get("answer_usefulness", ""), field="answer_usefulness"
        )
        evidence_rating = parse_rating(
            row.get("evidence_usefulness", ""), field="evidence_usefulness"
        )
        try:
            completion_seconds = float(row.get("completion_seconds", ""))
        except ValueError as exc:
            raise ValueError(
                f"CSV row {index} completion_seconds must be numeric"
            ) from exc
        if completion_seconds < 0:
            raise ValueError(
                f"CSV row {index} completion_seconds must be non-negative"
            )
        normalized.append(
            {
                "session_id": row["session_id"].strip(),
                "participant_id": row["participant_id"].strip(),
                "role": row["role"].strip(),
                "question_id": row["question_id"].strip(),
                "solved": solved,
                "answer_usefulness": answer_rating,
                "evidence_usefulness": evidence_rating,
                "completion_seconds": completion_seconds,
                "failure_type": row.get("failure_type", "").strip() or "none",
            }
        )

    return {
        "status": "completed",
        "participants": len({row["participant_id"] for row in normalized}),
        "sessions": len({row["session_id"] for row in normalized}),
        "questions": len(normalized),
        "task_success_rate": round(
            sum(row["solved"] for row in normalized) / len(normalized), 4
        ),
        "mean_answer_usefulness": round(
            statistics.fmean(row["answer_usefulness"] for row in normalized), 2
        ),
        "mean_evidence_usefulness": round(
            statistics.fmean(row["evidence_usefulness"] for row in normalized), 2
        ),
        "mean_completion_seconds": round(
            statistics.fmean(row["completion_seconds"] for row in normalized), 2
        ),
        "roles": dict(Counter(row["role"] for row in normalized)),
        "failure_types": dict(Counter(row["failure_type"] for row in normalized)),
    }


def markdown_report(summary: dict[str, Any]) -> str:
    if summary["status"] != "completed":
        return (
            "# 实验室试用报告\n\n"
            "当前没有真实参与者完成数据，不能生成成功率或满意度。\n"
        )
    return "\n".join(
        [
            "# 实验室试用报告",
            "",
            f"- 参与者：{summary['participants']}",
            f"- 会话：{summary['sessions']}",
            f"- 真实问题：{summary['questions']}",
            f"- 任务解决率：{summary['task_success_rate']:.2%}",
            f"- 回答有用性：{summary['mean_answer_usefulness']:.2f}/5",
            f"- 证据有用性：{summary['mean_evidence_usefulness']:.2f}/5",
            f"- 平均完成时间：{summary['mean_completion_seconds']:.2f} 秒",
            "",
            "## 失败类型",
            "",
            *[
                f"- {key}: {value}"
                for key, value in summary["failure_types"].items()
            ],
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize real lab pilot feedback without fabricating empty results"
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    summary = summarize_pilot(read_rows(args.input))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = args.output_dir / f"lab_pilot_{timestamp}.json"
    md_path = args.output_dir / f"lab_pilot_{timestamp}.md"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path.write_text(markdown_report(summary), encoding="utf-8")
    print(
        json.dumps(
            {"json": str(json_path), "markdown": str(md_path), **summary},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
