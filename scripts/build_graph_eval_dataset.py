from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.graph_store import Neo4jGraphStore, format_graph_relation_row


OUTPUT_PATH = PROJECT_ROOT / "docs" / "eval" / "graph_eval_v1.jsonl"
RELATION_TYPES = [
    "STUDIES",
    "USES_METHOD",
    "USES_FORCE_FIELD",
    "USES_SOFTWARE",
    "REPORTS",
]


SEEDS: list[dict[str, Any]] = [
    {
        "id": "KG01", "task": "single_hop", "question": "哪篇文献关联ReaxFF-lg力场？",
        "terms": ["ReaxFF-lg"], "papers": ["LRX-METHOD-004"],
        "answer": "LRX-METHOD-004关联ReaxFF-lg力场。",
    },
    {
        "id": "KG02", "task": "single_hop", "question": "哪些文献关联热导率？",
        "terms": ["thermal conductivity"], "papers": ["ARXIV-001", "ARXIV-003", "LRX-METHOD-004"],
        "answer": "ARXIV-001、ARXIV-003和LRX-METHOD-004关联thermal conductivity。",
    },
    {
        "id": "KG03", "task": "single_hop", "question": "哪篇文献报告了扩散系数？",
        "terms": ["diffusion coefficient"], "papers": ["LRX-METHOD-010"],
        "answer": "LRX-METHOD-010报告了diffusion coefficient。",
    },
    {
        "id": "KG04", "task": "single_hop", "question": "哪篇文献使用量子分子动力学方法？",
        "terms": ["quantum molecular dynamics"], "papers": ["LRX-METHOD-008"],
        "answer": "LRX-METHOD-008关联quantum molecular dynamics方法。",
    },
    {
        "id": "KG05", "task": "single_hop", "question": "哪些文献关联Dreiding力场？",
        "terms": ["Dreiding"], "papers": ["ARXIV-005", "LRX-METHOD-009"],
        "answer": "ARXIV-005和LRX-METHOD-009关联Dreiding力场。",
    },
    {
        "id": "KG06", "task": "single_hop", "question": "哪篇论文研究TKX-50？",
        "terms": ["TKX-50"], "papers": ["CORE-DL-002"],
        "answer": "CORE-DL-002研究TKX-50。",
    },
    {
        "id": "KG07", "task": "single_hop", "question": "哪些论文报告了内聚能密度？",
        "terms": ["cohesive energy density"], "papers": ["CORE-DL-002", "CORE-DL-003"],
        "answer": "CORE-DL-002和CORE-DL-003报告了cohesive energy density。",
    },
    {
        "id": "KG08", "task": "single_hop", "question": "哪些文献关联从头算分子动力学？",
        "terms": ["ab initio molecular dynamics"], "papers": ["LRX-CORE-002", "LRX-SI-002"],
        "answer": "LRX-CORE-002和LRX-SI-002关联ab initio molecular dynamics。",
    },
    {
        "id": "KG09", "task": "two_constraint", "question": "哪些论文同时关联HMX与热导率？",
        "terms": ["HMX", "thermal conductivity"], "papers": ["ARXIV-001", "ARXIV-003"],
        "answer": "ARXIV-001和ARXIV-003同时关联HMX与thermal conductivity。",
    },
    {
        "id": "KG10", "task": "two_constraint", "question": "哪些论文同时关联CL-20与结合能？",
        "terms": ["CL-20", "binding energy"], "papers": ["CORE-DL-001", "CORE-DL-002", "EMMD-016"],
        "answer": "CORE-DL-001、CORE-DL-002和EMMD-016同时关联CL-20与binding energy。",
    },
    {
        "id": "KG11", "task": "two_constraint", "question": "哪些论文同时关联PBX与力学性能？",
        "terms": ["PBX", "mechanical properties"], "papers": ["ARXIV-007", "CORE-DL-003", "EMMD-016"],
        "answer": "ARXIV-007、CORE-DL-003和EMMD-016同时关联PBX与mechanical properties。",
    },
    {
        "id": "KG12", "task": "two_constraint", "question": "哪些文献关联RDX与反应分子动力学？",
        "terms": ["RDX", "reactive molecular dynamics"], "papers": ["ARXIV-005", "ARXIV-011", "LRX-CORE-004", "LRX-CORE-005", "LRX-METHOD-004"],
        "answer": "ARXIV-005、ARXIV-011、LRX-CORE-004、LRX-CORE-005和LRX-METHOD-004关联RDX与reactive molecular dynamics。",
    },
    {
        "id": "KG13", "task": "two_constraint", "question": "哪些论文同时关联CL-20与COMPASS力场？",
        "terms": ["CL-20", "COMPASS"], "papers": ["CORE-DL-001", "CORE-DL-002"],
        "answer": "CORE-DL-001和CORE-DL-002同时关联CL-20与COMPASS。",
    },
    {
        "id": "KG14", "task": "two_constraint", "question": "哪些文献同时关联HMX与DFT？",
        "terms": ["HMX", "DFT"], "papers": ["ARXIV-009", "LRX-CORE-002", "LRX-CORE-004", "LRX-CORE-007"],
        "answer": "ARXIV-009、LRX-CORE-002、LRX-CORE-004和LRX-CORE-007同时关联HMX与DFT。",
    },
    {
        "id": "KG15", "task": "two_constraint", "question": "哪些文献关联CL-20与分子动力学？",
        "terms": ["CL-20", "molecular dynamics"], "papers": ["CORE-DL-001", "CORE-DL-002", "EMMD-016", "LRX-CORE-004"],
        "answer": "CORE-DL-001、CORE-DL-002、EMMD-016和LRX-CORE-004关联CL-20与molecular dynamics。",
    },
    {
        "id": "KG16", "task": "two_constraint", "question": "哪篇论文同时关联PBX与内聚能密度？",
        "terms": ["PBX", "cohesive energy density"], "papers": ["CORE-DL-003"],
        "answer": "CORE-DL-003同时关联PBX与cohesive energy density。",
    },
    {
        "id": "KG17", "task": "multi_constraint", "question": "哪些论文同时关联HMX、LAMMPS与热导率？",
        "terms": ["HMX", "LAMMPS", "thermal conductivity"], "papers": ["ARXIV-001", "ARXIV-003"],
        "answer": "ARXIV-001和ARXIV-003同时关联HMX、LAMMPS与thermal conductivity。",
    },
    {
        "id": "KG18", "task": "multi_constraint", "question": "哪篇论文在RDX聚合物孔洞热点体系中关联Dreiding力场？",
        "terms": ["RDX", "Dreiding", "hotspot"], "papers": ["ARXIV-005"],
        "answer": "ARXIV-005在RDX聚合物孔洞热点研究中关联Dreiding力场。",
    },
    {
        "id": "KG19", "task": "multi_constraint", "question": "哪些论文同时关联CL-20、HMX与结合能？",
        "terms": ["CL-20", "HMX", "binding energy"], "papers": ["CORE-DL-001", "EMMD-016"],
        "answer": "CORE-DL-001和EMMD-016同时关联CL-20、HMX与binding energy。",
    },
    {
        "id": "KG20", "task": "multi_constraint", "question": "哪篇论文同时关联TKX-50、CL-20、COMPASS与结合能？",
        "terms": ["TKX-50", "CL-20", "COMPASS", "binding energy"], "papers": ["CORE-DL-002"],
        "answer": "CORE-DL-002同时关联TKX-50、CL-20、COMPASS与binding energy。",
    },
]


def _collect_gold_relations(
    graph: Neo4jGraphStore,
    entity_terms: list[str],
    paper_ids: list[str],
) -> list[dict[str, Any]]:
    query = """
    MATCH (p:Paper)-[r]->(n)
    WHERE type(r) IN $relation_types
      AND p.paper_id IN $paper_ids
      AND toLower(coalesce(n.name, n.text, '')) = toLower($term)
    RETURN p.paper_id AS paper_id,
           p.title AS title,
           type(r) AS relation,
           labels(n) AS labels,
           coalesce(n.name, n.text) AS entity_name,
           r.evidence_chunk_id AS evidence_chunk_id,
           r.evidence_text AS evidence_text
    ORDER BY paper_id, relation, entity_name
    """
    relations: list[dict[str, Any]] = []
    coverage = {paper_id: set() for paper_id in paper_ids}
    with graph.driver.session() as session:
        for term in entity_terms:
            records = session.run(
                query,
                relation_types=RELATION_TYPES,
                paper_ids=paper_ids,
                term=term,
            )
            for record in records:
                item = format_graph_relation_row(dict(record))
                item["matched_term"] = term
                relations.append(item)
                coverage[item["paper_id"]].add(term.lower())

    expected = {term.lower() for term in entity_terms}
    missing = {
        paper_id: sorted(expected - matched)
        for paper_id, matched in coverage.items()
        if matched != expected
    }
    if missing:
        raise ValueError(f"gold graph relations are incomplete: {missing}")
    return relations


def build_dataset(output_path: Path = OUTPUT_PATH) -> list[dict[str, Any]]:
    graph = Neo4jGraphStore()
    graph.verify()
    rows: list[dict[str, Any]] = []
    try:
        for index, seed in enumerate(SEEDS):
            relations = _collect_gold_relations(
                graph,
                entity_terms=seed["terms"],
                paper_ids=seed["papers"],
            )
            relevant_chunks = list(
                dict.fromkeys(
                    f"{item['paper_id']}:{item['evidence_chunk_id']}"
                    for item in relations
                    if item.get("evidence_chunk_id") is not None
                )
            )
            rows.append(
                {
                    "question_id": seed["id"],
                    "split": "dev" if index < 12 else "test",
                    "category": "graph_relation",
                    "graph_task": seed["task"],
                    "difficulty": "medium" if seed["task"] == "single_hop" else "hard",
                    "question": seed["question"],
                    "entity_terms": seed["terms"],
                    "relevant_paper_ids": seed["papers"],
                    "relevant_chunk_ids": relevant_chunks,
                    "reference_answer": seed["answer"],
                    "required_claims": [*seed["papers"], " + ".join(seed["terms"])],
                    "expected_terms": [term.lower() for term in seed["terms"]],
                    "should_refuse": False,
                    "gold_relations": relations,
                    "annotation_basis": "neo4j_exact_relation_and_manual_evidence_review_v1",
                }
            )
    finally:
        graph.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return rows


def main() -> None:
    rows = build_dataset()
    counts = {
        task: sum(row["graph_task"] == task for row in rows)
        for task in ("single_hop", "two_constraint", "multi_constraint")
    }
    print(json.dumps({"output": str(OUTPUT_PATH), "questions": len(rows), "tasks": counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
