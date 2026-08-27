from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.graph_store import Neo4jGraphStore
from core.kg_retriever import retrieve_kg_evidence
from workflows.literature_agent_workflow import (
    MATERIAL_HINTS,
    METHOD_HINTS,
    PROPERTY_HINTS,
    question_analyzer,
)


DEFAULT_DATASET = PROJECT_ROOT / "docs" / "eval" / "graph_eval_v1.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "app_data" / "eval"
RELATION_TYPES = [
    "STUDIES",
    "USES_METHOD",
    "USES_FORCE_FIELD",
    "USES_SOFTWARE",
    "REPORTS",
]


def set_metrics(gold_ids: list[str], predicted_ids: list[str]) -> dict[str, float]:
    gold = set(gold_ids)
    predicted = set(predicted_ids)
    matched = gold & predicted
    precision = len(matched) / len(predicted) if predicted else 0.0
    recall = len(matched) / len(gold) if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "exact_match": 1.0 if gold == predicted else 0.0,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    return {
        "queries": len(rows),
        **{
            field: round(statistics.fmean(row[field] for row in rows), 4)
            if rows
            else 0.0
            for field in ("precision", "recall", "f1", "exact_match")
        },
        "mean_latency_ms": round(
            statistics.fmean(row["latency_ms"] for row in rows), 2
        ) if rows else 0.0,
    }


def _oracle_intersection(
    graph: Neo4jGraphStore,
    terms: list[str],
) -> list[str]:
    query = """
    MATCH (p:Paper)-[r]->(n)
    WHERE type(r) IN $relation_types
      AND toLower(coalesce(n.name, n.text, '')) = toLower($term)
    RETURN DISTINCT p.paper_id AS paper_id
    ORDER BY paper_id
    """
    paper_sets: list[set[str]] = []
    with graph.driver.session() as session:
        for term in terms:
            paper_sets.append(
                {
                    str(record["paper_id"])
                    for record in session.run(
                        query,
                        relation_types=RELATION_TYPES,
                        term=term,
                    )
                }
            )
    return sorted(set.intersection(*paper_sets)) if paper_sets else []


def _agent_retrieval(question: str) -> tuple[list[str], list[str], str | None]:
    analyzed = question_analyzer({"query": question, "trace": []})
    terms = analyzed.get("query_terms", [])
    result = retrieve_kg_evidence(terms, limit=8)
    paper_ids = list(
        dict.fromkeys(
            str(item.get("paper_id") or "")
            for item in result.get("items", [])
            if item.get("paper_id")
        )
    )
    return terms, paper_ids, result.get("error")


def _legacy_terms(question: str) -> list[str]:
    terms = [
        hint
        for hint in [*MATERIAL_HINTS, *METHOD_HINTS, *PROPERTY_HINTS]
        if hint.lower() in question.lower()
    ]
    if not terms:
        terms = re.findall(r"[A-Za-z][A-Za-z0-9\-+/]*", question)[:5]
    return list(dict.fromkeys(terms))


def _legacy_union_top8(
    graph: Neo4jGraphStore,
    question: str,
) -> tuple[list[str], list[str]]:
    terms = _legacy_terms(question)
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for term in terms:
        for item in graph.query_relations(term=term, limit=8):
            key = "|".join(
                str(item.get(field, ""))
                for field in ("paper_id", "relation", "entity_label", "entity_name")
            )
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
            if len(items) >= 8:
                break
        if len(items) >= 8:
            break
    paper_ids = list(
        dict.fromkeys(
            str(item.get("paper_id") or "")
            for item in items
            if item.get("paper_id")
        )
    )
    return terms, paper_ids


def run(dataset: Path) -> dict[str, Any]:
    questions = [
        json.loads(line)
        for line in dataset.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    graph = Neo4jGraphStore()
    graph.verify()
    legacy_rows: list[dict[str, Any]] = []
    agent_rows: list[dict[str, Any]] = []
    oracle_rows: list[dict[str, Any]] = []
    try:
        for question in questions:
            start = time.perf_counter()
            legacy_terms, legacy_ids = _legacy_union_top8(graph, question["question"])
            legacy_latency = (time.perf_counter() - start) * 1000
            legacy_rows.append(
                {
                    "question_id": question["question_id"],
                    "graph_task": question["graph_task"],
                    "gold_paper_ids": question["relevant_paper_ids"],
                    "parsed_terms": legacy_terms,
                    "predicted_paper_ids": legacy_ids,
                    "latency_ms": round(legacy_latency, 2),
                    **set_metrics(question["relevant_paper_ids"], legacy_ids),
                }
            )

            start = time.perf_counter()
            parsed_terms, agent_ids, error = _agent_retrieval(question["question"])
            agent_latency = (time.perf_counter() - start) * 1000
            agent_rows.append(
                {
                    "question_id": question["question_id"],
                    "graph_task": question["graph_task"],
                    "gold_paper_ids": question["relevant_paper_ids"],
                    "parsed_terms": parsed_terms,
                    "predicted_paper_ids": agent_ids,
                    "error": error,
                    "latency_ms": round(agent_latency, 2),
                    **set_metrics(question["relevant_paper_ids"], agent_ids),
                }
            )

            start = time.perf_counter()
            oracle_ids = _oracle_intersection(graph, question["entity_terms"])
            oracle_latency = (time.perf_counter() - start) * 1000
            oracle_rows.append(
                {
                    "question_id": question["question_id"],
                    "graph_task": question["graph_task"],
                    "gold_paper_ids": question["relevant_paper_ids"],
                    "entity_terms": question["entity_terms"],
                    "predicted_paper_ids": oracle_ids,
                    "latency_ms": round(oracle_latency, 2),
                    **set_metrics(question["relevant_paper_ids"], oracle_ids),
                }
            )
            print(f"graph {question['question_id']}", flush=True)
    finally:
        graph.close()

    def grouped(rows: list[dict[str, Any]]) -> dict[str, Any]:
        tasks = sorted({row["graph_task"] for row in rows})
        return {
            "summary": summarize(rows),
            "groups": {
                task: summarize([row for row in rows if row["graph_task"] == task])
                for task in tasks
            },
            "queries": rows,
        }

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": str(dataset),
        "question_count": len(questions),
        "legacy_rule_union_top8": grouped(legacy_rows),
        "agent_rule_and_top8_papers": grouped(agent_rows),
        "oracle_exact_intersection": grouped(oracle_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local Neo4j graph retrieval benchmark")
    parser.add_argument("--questions", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    report = run(args.questions)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"graph_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "legacy_rule_union_top8": report["legacy_rule_union_top8"]["summary"],
                "agent_rule_and_top8_papers": report["agent_rule_and_top8_papers"]["summary"],
                "oracle_exact_intersection": report["oracle_exact_intersection"]["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
