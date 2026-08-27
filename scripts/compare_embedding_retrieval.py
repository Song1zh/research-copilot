from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(SCRIPT_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_PROJECT_ROOT))

from core.config import CHROMA_DB_PATH, LITERATURE_CHROMA_COLLECTION, LITERATURE_CORPUS_DIR, PROJECT_ROOT
from core.hybrid_retriever import retrieve_hybrid_evidence
from core.literature_indexer import index_literature_corpus


DEFAULT_QUESTION_PATH = PROJECT_ROOT / "docs" / "eval_literature_questions.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "app_data" / "eval"


@dataclass
class QueryEvaluation:
    question_id: str
    question: str
    relevant_paper_ids: list[str]
    retrieved_paper_ids: list[str]
    hit_at_5: float
    recall_at_5: float
    reciprocal_rank_at_5: float
    latency_ms: float
    failure_reason: str | None = None


def parse_ids(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def unique_paper_ids(results: list[dict[str, Any]], limit: int = 5) -> list[str]:
    paper_ids: list[str] = []
    for item in results:
        paper_id = str(item.get("metadata", {}).get("paper_id", "")).strip()
        if paper_id and paper_id not in paper_ids:
            paper_ids.append(paper_id)
        if len(paper_ids) >= limit:
            break
    return paper_ids


def retrieval_metrics(
    relevant_paper_ids: list[str],
    retrieved_paper_ids: list[str],
    *,
    k: int = 5,
) -> tuple[float, float, float]:
    relevant = set(relevant_paper_ids)
    ranked = retrieved_paper_ids[:k]
    if not relevant:
        return 0.0, 0.0, 0.0

    matched = relevant.intersection(ranked)
    hit = 1.0 if matched else 0.0
    recall = len(matched) / len(relevant)
    reciprocal_rank = 0.0
    for rank, paper_id in enumerate(ranked, start=1):
        if paper_id in relevant:
            reciprocal_rank = 1.0 / rank
            break
    return hit, recall, reciprocal_rank


def summarize(rows: list[QueryEvaluation]) -> dict[str, Any]:
    scored = [row for row in rows if row.relevant_paper_ids and row.failure_reason is None]
    failures = [row for row in rows if row.failure_reason]
    if not scored:
        return {
            "scored_queries": 0,
            "hit_at_5": 0.0,
            "recall_at_5": 0.0,
            "mrr_at_5": 0.0,
            "mean_latency_ms": 0.0,
            "failures": len(failures),
        }
    return {
        "scored_queries": len(scored),
        "hit_at_5": round(statistics.fmean(row.hit_at_5 for row in scored), 4),
        "recall_at_5": round(statistics.fmean(row.recall_at_5 for row in scored), 4),
        "mrr_at_5": round(statistics.fmean(row.reciprocal_rank_at_5 for row in scored), 4),
        "mean_latency_ms": round(statistics.fmean(row.latency_ms for row in scored), 2),
        "failures": len(failures),
    }


def evaluate_provider(
    provider: str,
    reranker_provider: str,
    questions: list[dict[str, str]],
    *,
    collection_name: str,
    skip_index: bool,
) -> dict[str, Any]:
    if not skip_index:
        index_result = index_literature_corpus(
            corpus_root=LITERATURE_CORPUS_DIR,
            db_path=CHROMA_DB_PATH,
            collection_name=collection_name,
            include_metadata_only=False,
            embedding_provider=provider,
        )
        resolved_collection = index_result.collection_name
    else:
        resolved_collection = collection_name

    rows: list[QueryEvaluation] = []
    for question in questions:
        relevant_ids = parse_ids(question.get("relevant_paper_ids"))
        if not relevant_ids:
            continue

        start = time.perf_counter()
        try:
            results = retrieve_hybrid_evidence(
                query=question["question"],
                top_k=12,
                db_path=str(CHROMA_DB_PATH),
                collection_name=collection_name,
                embedding_provider=provider,
                reranker_provider=reranker_provider,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            retrieved_ids = unique_paper_ids(results, limit=5)
            hit, recall, reciprocal_rank = retrieval_metrics(relevant_ids, retrieved_ids)
            rows.append(
                QueryEvaluation(
                    question_id=question["question_id"],
                    question=question["question"],
                    relevant_paper_ids=relevant_ids,
                    retrieved_paper_ids=retrieved_ids,
                    hit_at_5=hit,
                    recall_at_5=recall,
                    reciprocal_rank_at_5=reciprocal_rank,
                    latency_ms=round(latency_ms, 2),
                )
            )
        except Exception as exc:
            rows.append(
                QueryEvaluation(
                    question_id=question["question_id"],
                    question=question["question"],
                    relevant_paper_ids=relevant_ids,
                    retrieved_paper_ids=[],
                    hit_at_5=0.0,
                    recall_at_5=0.0,
                    reciprocal_rank_at_5=0.0,
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                    failure_reason=f"{type(exc).__name__}: {exc}",
                )
            )

    return {
        "provider": provider,
        "reranker_provider": reranker_provider,
        "collection": resolved_collection,
        "summary": summarize(rows),
        "queries": [asdict(row) for row in rows],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="对比 local hash 与 DashScope embedding 的检索表现")
    parser.add_argument(
        "--providers",
        nargs="+",
        default=["local_hash", "dashscope"],
        choices=["local_hash", "dashscope"],
    )
    parser.add_argument(
        "--reranker-providers",
        nargs="+",
        default=["none", "dashscope"],
        choices=["none", "dashscope"],
        help="Run an explicit no-rerank versus DashScope rerank comparison",
    )
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTION_PATH)
    parser.add_argument("--collection", default=LITERATURE_CHROMA_COLLECTION)
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    with args.questions.open("r", encoding="utf-8-sig", newline="") as handle:
        questions = list(csv.DictReader(handle))

    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "question_file": str(args.questions),
        "providers": {},
    }
    for provider in args.providers:
        for reranker_provider in args.reranker_providers:
            label = f"{provider}+reranker:{reranker_provider}"
            try:
                report["providers"][label] = evaluate_provider(
                    provider,
                    reranker_provider,
                    questions,
                    collection_name=args.collection,
                    skip_index=args.skip_index,
                )
            except Exception as exc:
                report["providers"][label] = {
                    "provider": provider,
                    "reranker_provider": reranker_provider,
                    "error": f"{type(exc).__name__}: {exc}",
                    "summary": {
                        "scored_queries": 0,
                        "hit_at_5": 0.0,
                        "recall_at_5": 0.0,
                        "mrr_at_5": 0.0,
                        "mean_latency_ms": 0.0,
                        "failures": 1,
                    },
                    "queries": [],
                }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output_dir / f"embedding_comparison_{timestamp}.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_path), **report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
