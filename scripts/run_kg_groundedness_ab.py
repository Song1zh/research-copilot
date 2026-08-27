from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import CHROMA_DB_PATH, LITERATURE_CHROMA_COLLECTION, settings
from core.groundedness_evaluator import evaluate_groundedness
from core.hybrid_retriever import retrieve_hybrid_evidence
from core.llm_client import LLMClient
from scripts.run_rag_benchmark import load_jsonl, summarize_generation
from workflows.literature_agent_workflow import run_literature_agent_workflow


DEFAULT_DATASET = PROJECT_ROOT / "docs" / "eval" / "rag_eval_v1.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "app_data" / "eval"
_CHROMA_RETRIEVAL_LOCK = Lock()


def evidence_signature(items: list[dict[str, Any]]) -> list[str]:
    return [
        f"{(item.get('metadata') or {}).get('paper_id', '')}:"
        f"{(item.get('metadata') or {}).get('chunk_id', '')}"
        for item in items
    ]


def failed_groundedness(message: str) -> dict[str, Any]:
    return {
        "claim_support_rate": 0.0,
        "weighted_claim_support_rate": 0.0,
        "citation_coverage": 0.0,
        "citation_precision": 0.0,
        "answer_correctness": 0.0,
        "refusal_correct": None,
        "judge_error": message,
    }


def numeric_delta(
    enabled: dict[str, Any], disabled: dict[str, Any]
) -> dict[str, float]:
    fields = (
        "claim_support_rate",
        "weighted_claim_support_rate",
        "citation_coverage",
        "citation_precision",
        "answer_correctness",
        "refusal_accuracy",
    )
    return {
        field: round(float(enabled.get(field, 0.0)) - float(disabled.get(field, 0.0)), 4)
        for field in fields
    }


def drop_failed_pairs(
    groups: dict[str, list[dict[str, Any]]]
) -> tuple[dict[str, list[dict[str, Any]]], set[str]]:
    failed_ids = {
        row["question_id"]
        for rows in groups.values()
        for row in rows
        if row.get("workflow_error")
        or (row.get("groundedness") or {}).get("judge_error")
    }
    filtered = {
        provider: [row for row in rows if row["question_id"] not in failed_ids]
        for provider, rows in groups.items()
    }
    return filtered, failed_ids


def evaluate_question_pair(
    question: dict[str, Any],
    *,
    embedding_provider: str,
    reranker_provider: str,
    judge_model: str,
) -> dict[str, dict[str, Any]]:
    retrieval_start = time.perf_counter()
    try:
        # Chroma's local Rust client is not safe to initialize concurrently in
        # this process. Serialize only retrieval; cloud generation and judging
        # can still overlap across questions.
        with _CHROMA_RETRIEVAL_LOCK:
            frozen_evidence = retrieve_hybrid_evidence(
                query=question["question"],
                top_k=6,
                db_path=str(CHROMA_DB_PATH),
                collection_name=LITERATURE_CHROMA_COLLECTION,
                embedding_provider=embedding_provider,
                reranker_provider=reranker_provider,
                rerank_candidate_k=settings.RERANK_CANDIDATE_K,
            )
        retrieval_error = None
    except Exception as exc:
        frozen_evidence = []
        retrieval_error = f"{type(exc).__name__}: {exc}"
    retrieval_latency = round((time.perf_counter() - retrieval_start) * 1000, 2)
    signature = evidence_signature(frozen_evidence)

    def evaluate_arm(kg_provider: str) -> dict[str, Any]:
        start = time.perf_counter()
        if retrieval_error:
            return {
                "question_id": question["question_id"],
                "split": question.get("split"),
                "category": question.get("category"),
                "should_refuse": question["should_refuse"],
                "evidence_signature": signature,
                "retrieval_latency_ms": retrieval_latency,
                "latency_ms": retrieval_latency,
                "workflow_error": retrieval_error,
                "kg_error": None,
                "generation_mode": "failed",
                "answer": {},
                "groundedness": failed_groundedness(
                    f"retrieval failed: {retrieval_error}"
                ),
            }
        try:
            workflow_result = run_literature_agent_workflow(
                query=question["question"],
                collection_name=LITERATURE_CHROMA_COLLECTION,
                db_path=str(CHROMA_DB_PATH),
                embedding_provider=embedding_provider,
                reranker_provider=reranker_provider,
                kg_provider=kg_provider,
                text_evidence_override=frozen_evidence,
            )
            answer = workflow_result.get("final_output", {})
            kg_context = answer.get("kg_context", {})
            kg_error = kg_context.get("error")
            if kg_provider == "neo4j" and kg_error not in {None, "no query terms"}:
                raise RuntimeError(f"Neo4j A/B arm failed: {kg_error}")
            judge_client = LLMClient(model=judge_model)
            judge = lambda system, user: judge_client.chat(
                system_prompt=system, user_prompt=user
            )
            groundedness = evaluate_groundedness(
                question=question["question"],
                answer=answer,
                reference_answer=question["reference_answer"],
                required_claims=question["required_claims"],
                should_refuse=question["should_refuse"],
                judge=judge,
            ).to_dict()
            return {
                "question_id": question["question_id"],
                "split": question.get("split"),
                "category": question.get("category"),
                "should_refuse": question["should_refuse"],
                "evidence_signature": signature,
                "retrieval_latency_ms": retrieval_latency,
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                "workflow_error": workflow_result.get("error"),
                "kg_error": kg_error,
                "kg_item_count": len(kg_context.get("items", [])),
                "generation_mode": answer.get("generation_mode"),
                "answer": answer,
                "groundedness": groundedness,
            }
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            return {
                "question_id": question["question_id"],
                "split": question.get("split"),
                "category": question.get("category"),
                "should_refuse": question["should_refuse"],
                "evidence_signature": signature,
                "retrieval_latency_ms": retrieval_latency,
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                "workflow_error": message,
                "kg_error": message if kg_provider == "neo4j" else None,
                "generation_mode": "failed",
                "answer": {},
                "groundedness": failed_groundedness(message),
            }

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            provider: executor.submit(evaluate_arm, provider)
            for provider in ("none", "neo4j")
        }
        return {provider: futures[provider].result() for provider in futures}


def run_ab(
    questions: list[dict[str, Any]],
    *,
    embedding_provider: str,
    reranker_provider: str,
    judge_model: str,
    initial_groups: dict[str, list[dict[str, Any]]] | None = None,
    checkpoint_path: Path | None = None,
    checkpoint_meta: dict[str, Any] | None = None,
    question_workers: int = 1,
) -> dict[str, Any]:
    if question_workers <= 0:
        raise ValueError("question_workers must be greater than 0")
    groups: dict[str, list[dict[str, Any]]] = {
        "none": list((initial_groups or {}).get("none", [])),
        "neo4j": list((initial_groups or {}).get("neo4j", [])),
    }
    completed = {
        row["question_id"] for row in groups["none"]
    }.intersection(row["question_id"] for row in groups["neo4j"])
    pending: list[tuple[int, dict[str, Any]]] = []
    for index, question in enumerate(questions, start=1):
        if question["question_id"] in completed:
            print(
                f"kg-ab resume-skip {index}/{len(questions)} "
                f"{question['question_id']}",
                flush=True,
            )
        else:
            pending.append((index, question))

    def save_pair(index: int, question: dict[str, Any], pair: dict[str, dict[str, Any]]) -> None:
        for provider in ("none", "neo4j"):
            groups[provider].append(pair[provider])
        print(f"kg-ab {index}/{len(questions)} {question['question_id']}", flush=True)
        if checkpoint_path is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_path.write_text(
                json.dumps(
                    {
                        "meta": checkpoint_meta or {},
                        "updated_at": datetime.now().isoformat(timespec="seconds"),
                        "groups": groups,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    with ThreadPoolExecutor(max_workers=question_workers) as executor:
        futures = {
            executor.submit(
                evaluate_question_pair,
                question,
                embedding_provider=embedding_provider,
                reranker_provider=reranker_provider,
                judge_model=judge_model,
            ): (index, question)
            for index, question in pending
        }
        for future in as_completed(futures):
            index, question = futures[future]
            save_pair(index, question, future.result())

    question_order = {
        question["question_id"]: index for index, question in enumerate(questions)
    }
    for provider in groups:
        groups[provider].sort(
            key=lambda row: question_order.get(row["question_id"], len(questions))
        )

    summaries = {
        provider: summarize_generation(rows) for provider, rows in groups.items()
    }
    none_by_id = {row["question_id"]: row for row in groups["none"]}
    neo4j_by_id = {row["question_id"]: row for row in groups["neo4j"]}
    evidence_mismatches = [
        question["question_id"]
        for question in questions
        if question["question_id"] in none_by_id
        and question["question_id"] in neo4j_by_id
        and none_by_id[question["question_id"]]["evidence_signature"]
        != neo4j_by_id[question["question_id"]]["evidence_signature"]
    ]
    return {
        "invariant": {
            "same_questions": True,
            "same_text_evidence": not evidence_mismatches,
            "evidence_mismatch_question_ids": evidence_mismatches,
            "only_intended_variable": "kg_provider",
        },
        "groups": {
            provider: {"summary": summaries[provider], "queries": rows}
            for provider, rows in groups.items()
        },
        "delta_neo4j_minus_none": numeric_delta(
            summaries["neo4j"], summaries["none"]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run frozen-text-evidence Neo4j on/off Groundedness A/B"
    )
    parser.add_argument("--questions", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--embedding-provider",
        choices=["local_hash", "dashscope"],
        default="local_hash",
    )
    parser.add_argument(
        "--reranker-provider",
        choices=["none", "dashscope"],
        default="dashscope",
    )
    parser.add_argument("--generation-model", default=settings.OPENAI_MODEL)
    parser.add_argument("--judge-model", default=settings.GROUNDEDNESS_MODEL)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--question-workers",
        type=int,
        default=1,
        help="Number of questions evaluated concurrently; each question runs two A/B arms",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Write both A/B arms after every question for safe resume",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--retry-failures",
        action="store_true",
        help="On resume, rerun both A/B arms when either arm has judge/workflow failure",
    )
    args = parser.parse_args()

    questions = load_jsonl(args.questions)
    if args.limit is not None:
        questions = questions[: args.limit]
    settings.OPENAI_MODEL = args.generation_model
    run_config = {
        "dataset": str(args.questions.resolve()),
        "question_ids": [question["question_id"] for question in questions],
        "answer_model": args.generation_model,
        "judge_model": args.judge_model,
        "embedding_provider": args.embedding_provider,
        "reranker_provider": args.reranker_provider,
    }
    initial_groups = None
    if args.checkpoint and args.checkpoint.exists():
        if not args.resume:
            raise FileExistsError(
                f"checkpoint already exists: {args.checkpoint}; pass --resume"
            )
        checkpoint = json.loads(args.checkpoint.read_text(encoding="utf-8"))
        if checkpoint.get("meta") != run_config:
            raise ValueError("checkpoint configuration does not match this run")
        initial_groups = checkpoint.get("groups")
        if args.retry_failures and initial_groups:
            initial_groups, failed_ids = drop_failed_pairs(initial_groups)
            print(
                f"kg-ab retry-failures removed {len(failed_ids)} paired rows",
                flush=True,
            )
    elif args.resume:
        raise FileNotFoundError(f"checkpoint does not exist: {args.checkpoint}")
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": str(args.questions),
        "question_count": len(questions),
        "models": {
            "answer": args.generation_model,
            "judge": args.judge_model,
            "embedding_provider": args.embedding_provider,
            "reranker_provider": args.reranker_provider,
        },
        **run_ab(
            questions,
            embedding_provider=args.embedding_provider,
            reranker_provider=args.reranker_provider,
            judge_model=args.judge_model,
            initial_groups=initial_groups,
            checkpoint_path=args.checkpoint,
            checkpoint_meta=run_config,
            question_workers=args.question_workers,
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / (
        f"kg_groundedness_ab_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "invariant": report["invariant"],
                "summary": {
                    key: value["summary"]
                    for key, value in report["groups"].items()
                },
                "delta_neo4j_minus_none": report["delta_neo4j_minus_none"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
