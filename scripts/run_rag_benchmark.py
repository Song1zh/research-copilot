from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import CHROMA_DB_PATH, LITERATURE_CHROMA_COLLECTION, settings
from core.groundedness_evaluator import evaluate_groundedness
from core.hybrid_retriever import retrieve_hybrid_evidence
from core.llm_client import LLMClient
from workflows.literature_agent_workflow import run_literature_agent_workflow


DEFAULT_DATASET = PROJECT_ROOT / "docs" / "eval" / "rag_eval_v1.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "app_data" / "eval"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def unique_paper_ids(results: list[dict[str, Any]], limit: int) -> list[str]:
    values = []
    for item in results:
        paper_id = str((item.get("metadata") or {}).get("paper_id") or "")
        if paper_id and paper_id not in values:
            values.append(paper_id)
        if len(values) >= limit:
            break
    return values


def ndcg_at_k(relevant_ids: list[str], ranked_ids: list[str], k: int = 5) -> float:
    relevant = set(relevant_ids)
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, paper_id in enumerate(ranked_ids[:k], start=1)
        if paper_id in relevant
    )
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def retrieval_metrics(
    relevant_ids: list[str], ranked_ids: list[str], k: int = 5
) -> dict[str, float]:
    relevant = set(relevant_ids)
    top = ranked_ids[:k]
    matched = relevant.intersection(top)
    first_rank = next(
        (rank for rank, paper_id in enumerate(top, start=1) if paper_id in relevant),
        None,
    )
    return {
        f"hit_at_{k}": 1.0 if matched else 0.0,
        f"recall_at_{k}": len(matched) / len(relevant) if relevant else 0.0,
        f"mrr_at_{k}": 1.0 / first_rank if first_rank else 0.0,
        f"ndcg_at_{k}": ndcg_at_k(relevant_ids, ranked_ids, k),
    }


def percentile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize_retrieval(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if not row.get("failure_reason")]
    latencies = [float(row["latency_ms"]) for row in valid]
    fields = ["hit_at_5", "recall_at_5", "mrr_at_5", "ndcg_at_5", "recall_at_20"]
    result = {
        "queries": len(valid),
        **{
            field: round(statistics.fmean(float(row[field]) for row in valid), 4)
            if valid
            else 0.0
            for field in fields
        },
        "mean_latency_ms": round(statistics.fmean(latencies), 2) if latencies else 0.0,
        "p50_latency_ms": round(percentile(latencies, 0.50), 2),
        "p95_latency_ms": round(percentile(latencies, 0.95), 2),
        "failures": len(rows) - len(valid),
    }
    return result


def run_retrieval(
    questions: list[dict[str, Any]], reranker_provider: str
) -> dict[str, Any]:
    rows = []
    answerable = [row for row in questions if not row["should_refuse"]]
    for index, question in enumerate(answerable, start=1):
        start = time.perf_counter()
        try:
            results = retrieve_hybrid_evidence(
                query=question["question"],
                top_k=20,
                db_path=str(CHROMA_DB_PATH),
                collection_name=LITERATURE_CHROMA_COLLECTION,
                embedding_provider="local_hash",
                reranker_provider=reranker_provider,
                rerank_candidate_k=30,
            )
            ranked = unique_paper_ids(results, 20)
            metrics5 = retrieval_metrics(question["relevant_paper_ids"], ranked, 5)
            recall20 = (
                len(set(question["relevant_paper_ids"]).intersection(ranked[:20]))
                / len(question["relevant_paper_ids"])
            )
            rows.append(
                {
                    "question_id": question["question_id"],
                    "split": question["split"],
                    "category": question["category"],
                    "relevant_paper_ids": question["relevant_paper_ids"],
                    "retrieved_paper_ids": ranked,
                    **metrics5,
                    "recall_at_20": recall20,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                    "failure_reason": None,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "question_id": question["question_id"],
                    "split": question["split"],
                    "category": question["category"],
                    "relevant_paper_ids": question["relevant_paper_ids"],
                    "retrieved_paper_ids": [],
                    "hit_at_5": 0.0,
                    "recall_at_5": 0.0,
                    "mrr_at_5": 0.0,
                    "ndcg_at_5": 0.0,
                    "recall_at_20": 0.0,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                    "failure_reason": f"{type(exc).__name__}: {exc}",
                }
            )
        print(
            f"retrieval {reranker_provider} {index}/{len(answerable)} "
            f"{question['question_id']}",
            flush=True,
        )

    groups = {}
    for key in sorted({row["category"] for row in rows}):
        groups[key] = summarize_retrieval([row for row in rows if row["category"] == key])
    for key in ("dev", "test"):
        groups[f"split:{key}"] = summarize_retrieval([row for row in rows if row["split"] == key])
    return {
        "reranker_provider": reranker_provider,
        "summary": summarize_retrieval(rows),
        "groups": groups,
        "queries": rows,
    }


def summarize_generation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if not row["groundedness"].get("judge_error")]
    refusal_rows = [row for row in valid if row["should_refuse"]]
    return {
        "queries": len(valid),
        "claim_support_rate": round(
            statistics.fmean(row["groundedness"]["claim_support_rate"] for row in valid), 4
        ) if valid else 0.0,
        "weighted_claim_support_rate": round(
            statistics.fmean(row["groundedness"]["weighted_claim_support_rate"] for row in valid), 4
        ) if valid else 0.0,
        "citation_coverage": round(
            statistics.fmean(row["groundedness"]["citation_coverage"] for row in valid), 4
        ) if valid else 0.0,
        "citation_precision": round(
            statistics.fmean(row["groundedness"]["citation_precision"] for row in valid), 4
        ) if valid else 0.0,
        "answer_correctness": round(
            statistics.fmean(row["groundedness"]["answer_correctness"] for row in valid), 4
        ) if valid else 0.0,
        "refusal_accuracy": round(
            sum(row["groundedness"]["refusal_correct"] is True for row in refusal_rows)
            / len(refusal_rows),
            4,
        ) if refusal_rows else 0.0,
        "judge_failures": len(rows) - len(valid),
    }


def run_generation(
    questions: list[dict[str, Any]], *, judge_model: str
) -> dict[str, Any]:
    rows = []
    judge_client = LLMClient(model=judge_model)
    judge = lambda system, user: judge_client.chat(system_prompt=system, user_prompt=user)
    for index, question in enumerate(questions, start=1):
        start = time.perf_counter()
        try:
            workflow_result = run_literature_agent_workflow(
                query=question["question"],
                collection_name=LITERATURE_CHROMA_COLLECTION,
                db_path=str(CHROMA_DB_PATH),
                embedding_provider="local_hash",
                reranker_provider="dashscope",
            )
            answer = workflow_result.get("final_output", {})
            groundedness = evaluate_groundedness(
                question=question["question"],
                answer=answer,
                reference_answer=question["reference_answer"],
                required_claims=question["required_claims"],
                should_refuse=question["should_refuse"],
                judge=judge,
            ).to_dict()
            rows.append(
                {
                    "question_id": question["question_id"],
                    "split": question["split"],
                    "category": question["category"],
                    "should_refuse": question["should_refuse"],
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                    "workflow_error": workflow_result.get("error"),
                    "generation_mode": answer.get("generation_mode"),
                    "answer": answer,
                    "groundedness": groundedness,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "question_id": question["question_id"],
                    "split": question["split"],
                    "category": question["category"],
                    "should_refuse": question["should_refuse"],
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                    "workflow_error": f"{type(exc).__name__}: {exc}",
                    "generation_mode": "failed",
                    "answer": {},
                    "groundedness": {
                        "claim_support_rate": 0.0,
                        "weighted_claim_support_rate": 0.0,
                        "citation_coverage": 0.0,
                        "citation_precision": 0.0,
                        "answer_correctness": 0.0,
                        "refusal_correct": None,
                        "judge_error": f"workflow failed: {type(exc).__name__}: {exc}",
                    },
                }
            )
        print(f"generation {index}/{len(questions)} {question['question_id']}", flush=True)
    return {"summary": summarize_generation(rows), "queries": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 50-query retrieval and groundedness benchmark")
    parser.add_argument("--questions", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--reranker-providers",
        nargs="+",
        choices=["none", "dashscope"],
        default=["none", "dashscope"],
    )
    parser.add_argument("--run-generation", action="store_true")
    parser.add_argument("--generation-model", default=settings.OPENAI_MODEL)
    parser.add_argument("--judge-model", default=settings.GROUNDEDNESS_MODEL)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    questions = load_jsonl(args.questions)
    if args.limit is not None:
        questions = questions[: args.limit]
    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": str(args.questions),
        "question_count": len(questions),
        "retrieval": {},
    }
    for provider in args.reranker_providers:
        report["retrieval"][provider] = run_retrieval(questions, provider)
    if args.run_generation:
        settings.OPENAI_MODEL = args.generation_model
        report["generation_models"] = {
            "answer": args.generation_model,
            "judge": args.judge_model,
        }
        report["generation"] = run_generation(
            questions,
            judge_model=args.judge_model,
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"rag_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "summary": {
        "retrieval": {key: value["summary"] for key, value in report["retrieval"].items()},
        "generation": report.get("generation", {}).get("summary"),
    }}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
