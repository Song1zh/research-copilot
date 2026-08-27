from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import (
    CHROMA_DB_PATH,
    LITERATURE_CHROMA_COLLECTION,
    LITERATURE_CORPUS_DIR,
)
from core.hybrid_retriever import retrieve_hybrid_evidence
from core.keyword_retriever import retrieve_keyword_evidence
from core.literature_indexer import index_literature_corpus
from core.retriever import retrieve_evidence
from core.vector_store import ChromaVectorStore
from scripts.run_rag_benchmark import (
    percentile,
    retrieval_metrics,
    unique_paper_ids,
)


DEFAULT_DATASET = PROJECT_ROOT / "docs" / "eval" / "rag_eval_v1.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "app_data" / "eval"
STRATEGIES = ("bm25", "vector", "hybrid", "hybrid_rerank")


def load_questions(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def retrieve_for_strategy(
    *,
    strategy: str,
    query: str,
    top_k: int,
    embedding_provider: str,
    collection_name: str,
    db_path: str,
) -> list[dict[str, Any]]:
    if strategy == "vector":
        return retrieve_evidence(
            query=query,
            top_k=top_k,
            db_path=db_path,
            collection_name=collection_name,
            embedding_provider=embedding_provider,
        )
    if strategy == "bm25":
        return retrieve_keyword_evidence(
            query=query,
            top_k=top_k,
            db_path=db_path,
            collection_name=collection_name,
            embedding_provider=embedding_provider,
        )
    if strategy in {"hybrid", "hybrid_rerank"}:
        return retrieve_hybrid_evidence(
            query=query,
            top_k=top_k,
            db_path=db_path,
            collection_name=collection_name,
            embedding_provider=embedding_provider,
            reranker_provider=(
                "dashscope" if strategy == "hybrid_rerank" else "none"
            ),
            rerank_candidate_k=30,
        )
    raise ValueError(
        f"unsupported retrieval strategy: {strategy!r}; "
        f"supported values: {', '.join(STRATEGIES)}"
    )


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if not row.get("failure_reason")]
    latencies = [float(row["latency_ms"]) for row in valid]
    fields = ("hit_at_5", "recall_at_5", "mrr_at_5", "ndcg_at_5", "recall_at_20")
    return {
        "queries": len(valid),
        **{
            field: round(
                statistics.fmean(float(row[field]) for row in valid), 4
            )
            if valid
            else 0.0
            for field in fields
        },
        "mean_latency_ms": round(statistics.fmean(latencies), 2)
        if latencies
        else 0.0,
        "p50_latency_ms": round(percentile(latencies, 0.5), 2),
        "p95_latency_ms": round(percentile(latencies, 0.95), 2),
        "failures": len(rows) - len(valid),
    }


def ensure_collection(
    provider: str,
    *,
    collection_name: str,
    index_if_missing: bool,
) -> dict[str, Any]:
    store = ChromaVectorStore(
        db_path=str(CHROMA_DB_PATH),
        collection_name=collection_name,
        embedding_provider=provider,
    )
    count = store.count()
    if count == 0 and index_if_missing:
        result = index_literature_corpus(
            corpus_root=LITERATURE_CORPUS_DIR,
            db_path=CHROMA_DB_PATH,
            collection_name=collection_name,
            include_metadata_only=False,
            embedding_provider=provider,
        )
        count = result.chunk_count
    if count == 0:
        raise RuntimeError(
            f"collection for embedding provider {provider!r} is empty; "
            "rerun with --index-missing"
        )
    return {"resolved_collection": store.collection_name, "chunk_count": count}


def run_configuration(
    questions: list[dict[str, Any]],
    *,
    strategy: str,
    embedding_provider: str,
    collection_name: str,
    top_k: int = 20,
    retrieve: Callable[..., list[dict[str, Any]]] = retrieve_for_strategy,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    answerable = [row for row in questions if not row.get("should_refuse", False)]
    for index, question in enumerate(answerable, start=1):
        start = time.perf_counter()
        try:
            results = retrieve(
                strategy=strategy,
                query=question["question"],
                top_k=top_k,
                embedding_provider=embedding_provider,
                collection_name=collection_name,
                db_path=str(CHROMA_DB_PATH),
            )
            ranked = unique_paper_ids(results, top_k)
            metrics = retrieval_metrics(question["relevant_paper_ids"], ranked, 5)
            relevant = set(question["relevant_paper_ids"])
            recall20 = len(relevant.intersection(ranked[:20])) / len(relevant)
            rows.append(
                {
                    "question_id": question["question_id"],
                    "split": question.get("split"),
                    "category": question.get("category"),
                    "relevant_paper_ids": question["relevant_paper_ids"],
                    "retrieved_paper_ids": ranked,
                    **metrics,
                    "recall_at_20": recall20,
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                    "failure_reason": None,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "question_id": question["question_id"],
                    "split": question.get("split"),
                    "category": question.get("category"),
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
            f"ablation {embedding_provider}/{strategy} "
            f"{index}/{len(answerable)} {question['question_id']}",
            flush=True,
        )
    return {
        "embedding_provider": embedding_provider,
        "strategy": strategy,
        "summary": summarize(rows),
        "queries": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run BM25/vector/hybrid/reranker retrieval ablations"
    )
    parser.add_argument("--questions", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--embedding-providers",
        nargs="+",
        choices=["local_hash", "dashscope"],
        default=["local_hash"],
    )
    parser.add_argument(
        "--strategies", nargs="+", choices=STRATEGIES, default=list(STRATEGIES)
    )
    parser.add_argument("--collection", default=LITERATURE_CHROMA_COLLECTION)
    parser.add_argument("--index-missing", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    questions = load_questions(args.questions)
    if args.limit is not None:
        questions = questions[: args.limit]
    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": str(args.questions),
        "question_count": len(questions),
        "configurations": {},
        "collections": {},
    }
    for provider in args.embedding_providers:
        try:
            report["collections"][provider] = ensure_collection(
                provider,
                collection_name=args.collection,
                index_if_missing=args.index_missing,
            )
        except Exception as exc:
            report["collections"][provider] = {
                "error": f"{type(exc).__name__}: {exc}"
            }
            for strategy in args.strategies:
                label = f"{provider}/{strategy}"
                report["configurations"][label] = {
                    "embedding_provider": provider,
                    "strategy": strategy,
                    "error": report["collections"][provider]["error"],
                    "summary": summarize([]),
                    "queries": [],
                }
            continue

        for strategy in args.strategies:
            label = f"{provider}/{strategy}"
            report["configurations"][label] = run_configuration(
                questions,
                strategy=strategy,
                embedding_provider=provider,
                collection_name=args.collection,
            )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / (
        f"retrieval_ablation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "summary": {
                    key: value["summary"]
                    for key, value in report["configurations"].items()
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
