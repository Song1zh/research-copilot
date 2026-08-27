from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from core.config import CHROMA_DB_PATH, LITERATURE_CHROMA_COLLECTION, settings
from core.evidence_checker import check_answer_evidence_alignment
from core.evidence_formatter import build_evidence_items
from core.hybrid_retriever import retrieve_hybrid_evidence
from core.kg_retriever import normalize_kg_provider, retrieve_kg_evidence
from core.llm_client import LLMClient
from core.schema_parser import parse_literature_answer


MATERIAL_HINTS = ["CL-20", "HMX", "RDX", "TATB", "PETN", "NTO", "LLM-105", "FOX-7", "TKX-50", "HTPB", "PBX", "Al"]
METHOD_HINTS = ["MD", "molecular dynamics", "ReaxFF", "QMD", "DFT", "AIMD", "reactive molecular dynamics"]
PROPERTY_HINTS = ["thermal decomposition", "sensitivity", "mechanical", "thermal conductivity", "binder", "interface", "hotspot"]

ENTITY_ALIASES = {
    "ReaxFF-lg": "ReaxFF-lg",
    "反应分子动力学": "reactive molecular dynamics",
    "reactive molecular dynamics": "reactive molecular dynamics",
    "量子分子动力学": "quantum molecular dynamics",
    "quantum molecular dynamics": "quantum molecular dynamics",
    "从头算分子动力学": "ab initio molecular dynamics",
    "ab initio molecular dynamics": "ab initio molecular dynamics",
    "分子动力学": "molecular dynamics",
    "molecular dynamics": "molecular dynamics",
    "内聚能密度": "cohesive energy density",
    "cohesive energy density": "cohesive energy density",
    "扩散系数": "diffusion coefficient",
    "diffusion coefficient": "diffusion coefficient",
    "热导率": "thermal conductivity",
    "thermal conductivity": "thermal conductivity",
    "热分解": "thermal decomposition",
    "thermal decomposition": "thermal decomposition",
    "力学性能": "mechanical properties",
    "mechanical properties": "mechanical properties",
    "结合能": "binding energy",
    "binding energy": "binding energy",
    "Materials Studio": "Materials Studio",
    "ReaxFF": "ReaxFF",
    "COMPASS": "COMPASS",
    "Dreiding": "Dreiding",
    "LAMMPS": "LAMMPS",
    "Gaussian": "Gaussian",
    "DFT": "DFT",
    "CL-20": "CL-20",
    "TKX-50": "TKX-50",
    "LLM-105": "LLM-105",
    "FOX-7": "FOX-7",
    "HTPB": "HTPB",
    "TATB": "TATB",
    "PETN": "PETN",
    "HMX": "HMX",
    "RDX": "RDX",
    "PBX": "PBX",
    "NTO": "NTO",
    "TNT": "TNT",
    "热点": "hotspot",
    "hotspot": "hotspot",
}


class LiteratureAgentState(TypedDict):
    query: str
    collection_name: str
    embedding_provider: str
    reranker_provider: str
    kg_provider: str
    db_path: str
    question_type: str
    query_terms: list[str]
    query_plan: list[str]
    text_evidence: list[dict[str, Any]]
    text_evidence_override: list[dict[str, Any]] | None
    kg_context: dict[str, Any]
    fused_evidence: list[dict[str, Any]]
    final_output: dict[str, Any]
    alignment_check: dict[str, Any]
    trace: list[dict[str, Any]]
    error: str | None


def append_trace(state: LiteratureAgentState, node: str, output: dict[str, Any]) -> list[dict[str, Any]]:
    trace = list(state.get("trace", []))
    trace.append({"node": node, "output": output})
    return trace


def _find_terms(query: str, hints: list[str]) -> list[str]:
    return [hint for hint in hints if hint.lower() in query.lower()]


def _extract_entity_terms(query: str) -> list[str]:
    occupied: list[tuple[int, int]] = []
    matched: list[tuple[int, str]] = []
    for alias, canonical in sorted(
        ENTITY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True
    ):
        for match in re.finditer(re.escape(alias), query, flags=re.IGNORECASE):
            span = match.span()
            if any(span[0] < end and start < span[1] for start, end in occupied):
                continue
            occupied.append(span)
            matched.append((span[0], canonical))
    return list(dict.fromkeys(value for _, value in sorted(matched)))


def question_analyzer(state: LiteratureAgentState) -> dict[str, Any]:
    query = state["query"]
    question_type = "general"
    if any(word in query for word in ["对比", "difference", "compare", "比较"]):
        question_type = "comparison"
    elif any(word.lower() in query.lower() for word in ["mechanism", "decomposition", "分解", "机制"]):
        question_type = "mechanism"
    elif any(word in query for word in ["方法", "参数", "force field", "力场"]):
        question_type = "method_parameters"

    terms = _extract_entity_terms(query)
    if not terms:
        terms = [token for token in re.findall(r"[A-Za-z][A-Za-z0-9\-+/]*", query)[:5]]

    return {
        "question_type": question_type,
        "query_terms": list(dict.fromkeys(terms)),
        "trace": append_trace(state, "question_analyzer", {"question_type": question_type, "query_terms": terms}),
    }


def query_planner(state: LiteratureAgentState) -> dict[str, Any]:
    terms = state.get("query_terms", [])
    kg_provider = state.get("kg_provider", "neo4j")
    plan = [
        f"Use hybrid retrieval for: {state['query']}",
        (
            f"Use KG retrieval for entities: {', '.join(terms) if terms else 'none'}"
            if kg_provider == "neo4j"
            else "KG retrieval is explicitly disabled for this run."
        ),
        "Fuse text evidence and graph context, then generate citation-aware answer.",
    ]
    return {"query_plan": plan, "trace": append_trace(state, "query_planner", {"query_plan": plan})}


def hybrid_retriever_node(state: LiteratureAgentState) -> dict[str, Any]:
    override = state.get("text_evidence_override")
    if override is not None:
        evidence = [dict(item) for item in override]
        return {
            "text_evidence": evidence,
            "trace": append_trace(
                state,
                "hybrid_retriever",
                {"evidence_count": len(evidence), "source": "frozen_override"},
            ),
        }
    try:
        evidence = retrieve_hybrid_evidence(
            query=state["query"],
            top_k=6,
            db_path=state["db_path"],
            collection_name=state["collection_name"],
            embedding_provider=state["embedding_provider"],
            reranker_provider=state["reranker_provider"],
            rerank_candidate_k=settings.RERANK_CANDIDATE_K,
        )
        rerank_metadata = {
            "provider": state["reranker_provider"],
            "model": evidence[0].get("reranker_model") if evidence else None,
            "candidate_count": (
                evidence[0].get("rerank_candidate_count") if evidence else 0
            ),
            "latency_ms": evidence[0].get("rerank_latency_ms") if evidence else 0,
        }
        return {
            "text_evidence": evidence,
            "trace": append_trace(
                state,
                "hybrid_retriever",
                {"evidence_count": len(evidence), "reranker": rerank_metadata},
            ),
        }
    except Exception as exc:
        return {
            "text_evidence": [],
            "error": str(exc),
            "trace": append_trace(state, "hybrid_retriever", {"error": str(exc)}),
        }


def kg_retriever_node(state: LiteratureAgentState) -> dict[str, Any]:
    kg_context = retrieve_kg_evidence(
        state.get("query_terms", []),
        limit=8,
        provider=state.get("kg_provider", "neo4j"),
    )
    return {
        "kg_context": kg_context,
        "trace": append_trace(
            state,
            "kg_retriever",
            {
                "available": kg_context.get("available"),
                "disabled": kg_context.get("disabled", False),
                "provider": kg_context.get("provider"),
                "item_count": len(kg_context.get("items", [])),
                "error": kg_context.get("error"),
            },
        ),
    }


def evidence_fusion(state: LiteratureAgentState) -> dict[str, Any]:
    seen: set[str] = set()
    fused: list[dict[str, Any]] = []
    for item in state.get("text_evidence", []):
        metadata = item.get("metadata", {})
        key = f"{metadata.get('paper_id')}::{metadata.get('chunk_id')}"
        if key in seen:
            continue
        seen.add(key)
        fused.append(item)
    return {"fused_evidence": fused, "trace": append_trace(state, "evidence_fusion", {"fused_count": len(fused)})}


def build_literature_answer_prompt(state: LiteratureAgentState, evidence_items: list[dict[str, Any]]) -> tuple[str, str]:
    kg_context = state.get("kg_context", {})
    kg_items = kg_context.get("items", [])
    payload = {
        "query": state.get("query", ""),
        "question_type": state.get("question_type", "general"),
        "query_plan": state.get("query_plan", []),
        "evidence": evidence_items,
        "kg_context": {
            "available": kg_context.get("available", False),
            "disabled": kg_context.get("disabled", False),
            "provider": kg_context.get("provider", state.get("kg_provider")),
            "items": [
                {
                    "path_text": item.get("path_text", ""),
                    "paper_id": item.get("paper_id", ""),
                    "title": item.get("title", ""),
                    "relation": item.get("relation", ""),
                    "entity_label": item.get("entity_label", ""),
                    "entity_name": item.get("entity_name", ""),
                    "evidence_text": item.get("evidence_text", ""),
                }
                for item in kg_items[:8]
            ],
            "error": kg_context.get("error"),
        },
    }

    system_prompt = """你是一个严格的科研文献 RAG Agent。
你必须只基于用户提供的 evidence 和 kg_context 回答，不能使用外部知识补全，不能编造论文、材料、方法、力场、软件、性质或结论。
你必须输出合法 JSON 对象，不要 Markdown、不要代码块、不要额外解释。
只能生成这些字段：summary, comparison_table, mechanisms, methods, findings, limitations。
所有 summary、mechanisms、methods、findings、limitations 中的结论都必须包含 evidence 引用，例如 [E1] 或 [E1,E2]。
comparison_table 中的 finding 也必须包含 evidence 引用。
kg_context 只能帮助你理解论文和实体关系，不能替代 evidence 引用；不要引用 KG id，只能引用 E1、E2 这类 evidence_id。
如果 evidence 不足以回答某个部分，把不足写入 limitations，并引用最相关的 evidence。
"""
    user_prompt = (
        "请根据下面的 JSON 输入生成结构化文献回答。\n"
        "输出 JSON 字段格式：\n"
        "{\n"
        '  "summary": "string with [E#]",\n'
        '  "comparison_table": [{"paper_id": "", "material_system": "", "method": "", "force_field": "", "software": "", "conditions": "", "finding": "string with [E#]", "citation": "[E#]"}],\n'
        '  "mechanisms": ["string with [E#]"],\n'
        '  "methods": ["string with [E#]"],\n'
        '  "findings": ["string with [E#]"],\n'
        '  "limitations": ["string with [E#]"]\n'
        "}\n\n"
        f"输入：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    return system_prompt, user_prompt


def _no_evidence_answer(state: LiteratureAgentState) -> dict[str, Any]:
    return {
        "summary": "当前文献库没有检索到足够证据回答该问题。",
        "comparison_table": [],
        "mechanisms": [],
        "methods": [],
        "findings": [],
        "limitations": ["未检索到可用 evidence，建议先运行 /literature/index 或扩大文献库。"],
        "evidence": [],
        "query_plan": state.get("query_plan", []),
        "kg_context": state.get("kg_context", {}),
        "generation_mode": "no_evidence",
        "llm_error": None,
    }


def _template_answer(
    state: LiteratureAgentState,
    evidence_items: list[dict[str, Any]],
    llm_error: str | None = None,
) -> dict[str, Any]:
    summary_ids = ",".join(item["evidence_id"] for item in evidence_items[: min(3, len(evidence_items))])
    kg_context = state.get("kg_context", {})
    kg_items = kg_context.get("items", [])
    if kg_context.get("available") and kg_items:
        summary = (
            f"基于混合检索证据，并结合 {len(kg_items)} 条 Neo4j 图谱关系，"
            f"当前问题可从 {len(evidence_items)} 条文献片段中获得初步回答 [{summary_ids}]。"
        )
    else:
        summary = f"基于混合检索证据，当前问题可从 {len(evidence_items)} 条文献片段中获得初步回答 [{summary_ids}]。"

    comparison_table = []
    mechanisms = []
    methods_for_alignment = []
    findings_for_alignment = []
    for evidence, raw in zip(evidence_items, state.get("fused_evidence", [])):
        metadata = raw.get("metadata", {})
        paper_id = str(metadata.get("paper_id", "unknown"))
        section = str(metadata.get("section", "unknown"))
        title = str(metadata.get("title", ""))
        citation = f"[{evidence['evidence_id']}]"
        comparison_table.append(
            {
                "paper_id": paper_id,
                "material_system": metadata.get("topic_tags", ""),
                "method": "See evidence snippet",
                "force_field": "",
                "software": "",
                "conditions": section,
                "finding": f"{title[:120]} {citation}",
                "citation": citation,
            }
        )
        findings_for_alignment.append(f"{title[:120]} {citation}")
        if any(term in evidence["snippet"].lower() for term in ["decomposition", "thermal", "mechanism", "分解"]):
            mechanisms.append(f"{evidence['snippet']} {citation}")
        if any(term in evidence["snippet"].lower() for term in ["molecular dynamics", "reaxff", "force field", "simulation"]):
            methods_for_alignment.append(f"{evidence['snippet']} {citation}")

    limitations = []
    if llm_error:
        limitations.append(f"LLM 生成不可用，已降级为规则模板回答；错误信息见 llm_error 字段 [{evidence_items[0]['evidence_id']}]。")
    if kg_context.get("disabled"):
        limitations.append(
            f"Neo4j 图谱在本次对照实验中被显式关闭，回答仅基于文本混合检索 [{evidence_items[0]['evidence_id']}]。"
        )
    elif not kg_context.get("available"):
        limitations.append(f"Neo4j 图谱上下文不可用，本次回答仅基于文本混合检索 [{evidence_items[0]['evidence_id']}]。")
    elif not kg_items:
        limitations.append(f"Neo4j 图谱已连接，但未命中与当前问题实体相关的关系，本次主要基于文本 evidence [{evidence_items[0]['evidence_id']}]。")

    return {
        "summary": summary,
        "comparison_table": comparison_table,
        "mechanisms": mechanisms[:4],
        "limitations": limitations,
        "methods": methods_for_alignment[:4],
        "findings": findings_for_alignment[:4],
        "evidence": evidence_items,
        "query_plan": state.get("query_plan", []),
        "kg_context": kg_context,
        "generation_mode": "template_fallback",
        "llm_error": llm_error,
    }


def _attach_backend_context(
    generated_answer: dict[str, Any],
    state: LiteratureAgentState,
    evidence_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "summary": generated_answer.get("summary", ""),
        "comparison_table": generated_answer.get("comparison_table", []),
        "mechanisms": generated_answer.get("mechanisms", []),
        "methods": generated_answer.get("methods", []),
        "findings": generated_answer.get("findings", []),
        "limitations": generated_answer.get("limitations", []),
        "evidence": evidence_items,
        "query_plan": state.get("query_plan", []),
        "kg_context": state.get("kg_context", {}),
        "generation_mode": "llm",
        "llm_error": None,
    }


def answer_generator(state: LiteratureAgentState) -> dict[str, Any]:
    evidence_items = build_evidence_items(state.get("fused_evidence", []), snippet_len=260)
    if not evidence_items:
        final_output = _no_evidence_answer(state)
        return {
            "final_output": final_output,
            "trace": append_trace(state, "answer_generator", {"mode": "no_evidence", "evidence_count": 0}),
        }

    try:
        system_prompt, user_prompt = build_literature_answer_prompt(state, evidence_items)
        raw_answer = LLMClient().chat(system_prompt=system_prompt, user_prompt=user_prompt)
        parsed_answer = parse_literature_answer(raw_answer)
        final_output = _attach_backend_context(parsed_answer.model_dump(), state, evidence_items)
        alignment = check_answer_evidence_alignment(final_output)
        if not alignment.get("is_aligned", False):
            raise ValueError(f"LLM citation alignment failed: {alignment}")
        return {
            "final_output": final_output,
            "trace": append_trace(
                state,
                "answer_generator",
                {
                    "mode": "llm",
                    "evidence_count": len(evidence_items),
                    "kg_item_count": len(state.get("kg_context", {}).get("items", [])),
                },
            ),
        }
    except Exception as exc:
        llm_error = str(exc)
        final_output = _template_answer(state, evidence_items, llm_error=llm_error)
        return {
            "final_output": final_output,
            "trace": append_trace(
                state,
                "answer_generator",
                {
                    "mode": "template_fallback",
                    "evidence_count": len(evidence_items),
                    "llm_error": llm_error,
                },
            ),
        }


def citation_verifier(state: LiteratureAgentState) -> dict[str, Any]:
    final_output = state.get("final_output", {})
    alignment = check_answer_evidence_alignment(final_output)
    return {
        "alignment_check": alignment,
        "trace": append_trace(state, "citation_verifier", {"is_aligned": alignment.get("is_aligned")}),
    }


def self_reflection(state: LiteratureAgentState) -> dict[str, Any]:
    final_output = dict(state.get("final_output", {}))
    limitations = list(final_output.get("limitations", []))
    if len(state.get("fused_evidence", [])) < 2:
        limitations.append("检索证据少于 2 条，答案只能作为探索性线索。")
    if not state.get("alignment_check", {}).get("is_aligned", False):
        limitations.append("引用对齐检查未完全通过，需要人工复核。")
    final_output["limitations"] = limitations
    return {
        "final_output": final_output,
        "trace": append_trace(state, "self_reflection", {"limitations_count": len(limitations)}),
    }


def build_graph():
    builder = StateGraph(LiteratureAgentState)
    builder.add_node("question_analyzer", question_analyzer)
    builder.add_node("query_planner", query_planner)
    builder.add_node("hybrid_retriever", hybrid_retriever_node)
    builder.add_node("kg_retriever", kg_retriever_node)
    builder.add_node("evidence_fusion", evidence_fusion)
    builder.add_node("answer_generator", answer_generator)
    builder.add_node("citation_verifier", citation_verifier)
    builder.add_node("self_reflection", self_reflection)

    builder.add_edge(START, "question_analyzer")
    builder.add_edge("question_analyzer", "query_planner")
    builder.add_edge("query_planner", "hybrid_retriever")
    builder.add_edge("hybrid_retriever", "kg_retriever")
    builder.add_edge("kg_retriever", "evidence_fusion")
    builder.add_edge("evidence_fusion", "answer_generator")
    builder.add_edge("answer_generator", "citation_verifier")
    builder.add_edge("citation_verifier", "self_reflection")
    builder.add_edge("self_reflection", END)
    return builder.compile()


graph = build_graph()


def run_literature_agent_workflow(
    query: str,
    collection_name: str = LITERATURE_CHROMA_COLLECTION,
    db_path: str | None = None,
    embedding_provider: str | None = None,
    reranker_provider: str | None = None,
    kg_provider: str | None = None,
    text_evidence_override: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if db_path is None:
        db_path = str(CHROMA_DB_PATH)
    initial_state: LiteratureAgentState = {
        "query": query,
        "collection_name": collection_name,
        "embedding_provider": embedding_provider or settings.EMBEDDING_PROVIDER,
        "reranker_provider": reranker_provider or settings.RERANKER_PROVIDER,
        "kg_provider": normalize_kg_provider(kg_provider or settings.KG_PROVIDER),
        "db_path": db_path,
        "question_type": "",
        "query_terms": [],
        "query_plan": [],
        "text_evidence": [],
        "text_evidence_override": text_evidence_override,
        "kg_context": {},
        "fused_evidence": [],
        "final_output": {},
        "alignment_check": {},
        "trace": [],
        "error": None,
    }
    return graph.invoke(initial_state)
