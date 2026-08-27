from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUESTION_FILE = PROJECT_ROOT / "docs" / "eval" / "blind_questions.csv"
DEFAULT_GOLD_FILE = PROJECT_ROOT / "docs" / "eval" / "blind_gold.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "eval" / "frozen"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")


def parse_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def build_frozen_rows(
    question_rows: list[dict[str, str]],
    gold_rows: list[dict[str, str]],
    *,
    minimum_questions: int = 30,
) -> list[dict[str, Any]]:
    if len(question_rows) < minimum_questions:
        raise ValueError(
            f"blind evaluation requires at least {minimum_questions} questions; "
            f"received {len(question_rows)}"
        )
    question_ids = [row.get("question_id", "").strip() for row in question_rows]
    if any(not value for value in question_ids):
        raise ValueError("every blind question requires question_id")
    if len(set(question_ids)) != len(question_ids):
        raise ValueError("blind question_id values must be unique")

    gold_by_id = {row.get("question_id", "").strip(): row for row in gold_rows}
    if len(gold_by_id) != len(gold_rows):
        raise ValueError("blind gold question_id values must be unique")
    if set(question_ids) != set(gold_by_id):
        missing = sorted(set(question_ids) - set(gold_by_id))
        extra = sorted(set(gold_by_id) - set(question_ids))
        raise ValueError(f"question/gold id mismatch; missing={missing}, extra={extra}")

    frozen: list[dict[str, Any]] = []
    for question in question_rows:
        question_id = question["question_id"].strip()
        text = question.get("question", "").strip()
        category = question.get("category", "").strip()
        difficulty = question.get("difficulty", "").strip()
        if not text or not category or not difficulty:
            raise ValueError(
                f"{question_id} requires question, category, and difficulty"
            )
        gold = gold_by_id[question_id]
        should_refuse = parse_bool(gold.get("should_refuse", ""))
        relevant_paper_ids = parse_list(gold.get("relevant_paper_ids", ""))
        if not should_refuse and not relevant_paper_ids:
            raise ValueError(
                f"{question_id} is answerable but has no relevant_paper_ids"
            )
        if should_refuse and relevant_paper_ids:
            raise ValueError(
                f"{question_id} is refusal but has relevant_paper_ids"
            )
        if gold.get("evidence_reviewed", "").strip().lower() not in {
            "true",
            "1",
            "yes",
            "y",
        }:
            raise ValueError(f"{question_id} gold evidence is not reviewed")
        frozen.append(
            {
                "question_id": question_id,
                "split": "blind_test",
                "category": category,
                "difficulty": difficulty,
                "question": text,
                "relevant_paper_ids": relevant_paper_ids,
                "relevant_chunk_ids": parse_list(
                    gold.get("relevant_chunk_ids", "")
                ),
                "reference_answer": gold.get("reference_answer", "").strip(),
                "required_claims": parse_list(gold.get("required_claims", "")),
                "expected_terms": parse_list(gold.get("expected_terms", "")),
                "should_refuse": should_refuse,
                "annotation_basis": "independent_lab_annotation_v1",
                "annotator_id": gold.get("annotator_id", "").strip(),
            }
        )
    return frozen


def freeze_dataset(
    *,
    questions_path: Path,
    gold_path: Path,
    output_dir: Path,
    minimum_questions: int = 30,
) -> tuple[Path, Path, str]:
    rows = build_frozen_rows(
        read_csv(questions_path),
        read_csv(gold_path),
        minimum_questions=minimum_questions,
    )
    canonical = (
        "\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows
        )
        + "\n"
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / f"blind_eval_{digest[:12]}.jsonl"
    manifest_path = output_dir / f"blind_eval_{digest[:12]}.manifest.json"
    if dataset_path.exists() or manifest_path.exists():
        raise FileExistsError(
            f"frozen blind dataset already exists: {dataset_path.name}"
        )
    dataset_path.write_text(canonical, encoding="utf-8")
    manifest = {
        "frozen_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": str(dataset_path),
        "sha256": digest,
        "question_count": len(rows),
        "questions_source": str(questions_path),
        "gold_source": str(gold_path),
        "policy": "no tuning on blind_test; never overwrite this artifact",
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return dataset_path, manifest_path, digest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate and freeze an independently authored blind eval set"
    )
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTION_FILE)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--minimum-questions", type=int, default=30)
    args = parser.parse_args()
    dataset, manifest, digest = freeze_dataset(
        questions_path=args.questions,
        gold_path=args.gold,
        output_dir=args.output_dir,
        minimum_questions=args.minimum_questions,
    )
    print(
        json.dumps(
            {
                "dataset": str(dataset),
                "manifest": str(manifest),
                "sha256": digest,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
