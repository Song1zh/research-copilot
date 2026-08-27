import json

from fastapi.testclient import TestClient

from app import main as app_main
from core.evidence_checker import check_answer_evidence_alignment
from core.graph_store import format_graph_relation_row
from core.kg_retriever import retrieve_kg_evidence
from core import kg_retriever as kg_retriever_module
from core.literature_graph_builder import GraphBuildResult
from workflows import literature_agent_workflow as workflow_module
from workflows.literature_agent_workflow import answer_generator
from workflows.literature_agent_workflow import question_analyzer


def test_format_graph_relation_row_builds_stable_path_text():
    row = format_graph_relation_row(
        {
            "paper_id": "P1",
            "title": "RDX HTPB Study",
            "relation": "USES_FORCE_FIELD",
            "labels": ["ForceField"],
            "entity_name": "ReaxFF",
            "evidence_chunk_id": "3",
            "evidence_text": "ReaxFF was used.",
        }
    )

    assert row["paper_id"] == "P1"
    assert row["entity_label"] == "ForceField"
    assert row["entity_name"] == "ReaxFF"
    assert row["path_text"] == "(Paper: P1) -[:USES_FORCE_FIELD]-> (ForceField: ReaxFF)"
    assert row["evidence_text"] == "ReaxFF was used."


def test_retrieve_kg_evidence_without_terms_returns_stable_fallback():
    result = retrieve_kg_evidence([])

    assert result == {"available": False, "items": [], "error": "no query terms"}


def test_question_analyzer_uses_bilingual_longest_entity_matches():
    result = question_analyzer(
        {
            "query": "哪些论文使用ReaxFF-lg研究HMX热导率与扩散系数？",
            "trace": [],
        }
    )

    assert result["query_terms"] == [
        "ReaxFF-lg",
        "HMX",
        "thermal conductivity",
        "diffusion coefficient",
    ]
    assert "ReaxFF" not in result["query_terms"]


def test_retrieve_kg_evidence_uses_and_query_and_closes_graph(monkeypatch):
    calls = {}

    class FakeGraphStore:
        def verify(self):
            calls["verified"] = True

        def query_relations_by_terms(self, terms, limit):
            calls["terms"] = terms
            calls["limit"] = limit
            return [{"paper_id": "P1", "entity_name": "HMX"}]

        def close(self):
            calls["closed"] = True

    monkeypatch.setattr(kg_retriever_module, "Neo4jGraphStore", FakeGraphStore)
    result = kg_retriever_module.retrieve_kg_evidence(
        ["HMX", "thermal conductivity"], limit=6
    )

    assert result["available"] is True
    assert result["operator"] == "AND"
    assert calls == {
        "verified": True,
        "terms": ["HMX", "thermal conductivity"],
        "limit": 6,
        "closed": True,
    }


def build_answer_state():
    return {
        "query": "哪些论文使用 ReaxFF?",
        "collection_name": "demo",
        "db_path": "dummy_db",
        "question_type": "method_parameters",
        "query_terms": ["ReaxFF"],
        "query_plan": ["Use KG retrieval"],
        "text_evidence": [],
        "kg_context": {
            "available": True,
            "items": [
                {
                    "paper_id": "P1",
                    "title": "RDX Study",
                    "relation": "USES_FORCE_FIELD",
                    "entity_label": "ForceField",
                    "entity_name": "ReaxFF",
                    "path_text": "(Paper: P1) -[:USES_FORCE_FIELD]-> (ForceField: ReaxFF)",
                    "evidence_text": "ReaxFF was used for the simulations.",
                }
            ],
            "error": None,
        },
        "fused_evidence": [
            {
                "text": "LAMMPS and ReaxFF were used for reactive molecular dynamics of RDX.",
                "metadata": {
                    "paper_id": "P1",
                    "chunk_id": 3,
                    "source_path": "paper.pdf",
                    "title": "RDX Study",
                    "topic_tags": "RDX;ReaxFF",
                    "section": "methods",
                },
            }
        ],
        "final_output": {},
        "alignment_check": {},
        "trace": [],
        "error": None,
    }


def test_answer_generator_includes_kg_context_without_breaking_alignment(monkeypatch):
    class FailingLLMClient:
        def __init__(self):
            raise ValueError("missing api key")

    monkeypatch.setattr(workflow_module, "LLMClient", FailingLLMClient)
    state = build_answer_state()

    result = answer_generator(state)
    final_output = result["final_output"]
    alignment = check_answer_evidence_alignment(final_output)

    assert "Neo4j 图谱关系" in final_output["summary"]
    assert final_output["generation_mode"] == "template_fallback"
    assert final_output["kg_context"]["available"] is True
    assert final_output["kg_context"]["items"]
    assert alignment["is_aligned"] is True


def test_answer_generator_uses_llm_and_preserves_backend_context(monkeypatch):
    captured = {}

    class FakeLLMClient:
        def chat(self, system_prompt: str, user_prompt: str) -> str:
            captured["system_prompt"] = system_prompt
            captured["user_prompt"] = user_prompt
            return json.dumps(
                {
                    "summary": "ReaxFF 被用于 RDX 反应分子动力学模拟 [E1]",
                    "comparison_table": [
                        {
                            "paper_id": "P1",
                            "material_system": "RDX",
                            "method": "reactive molecular dynamics",
                            "force_field": "ReaxFF",
                            "software": "LAMMPS",
                            "conditions": "methods",
                            "finding": "论文报告了 RDX 的 ReaxFF 模拟设置 [E1]",
                            "citation": "[E1]",
                        }
                    ],
                    "mechanisms": ["证据说明该研究关注 RDX 的反应分子动力学模拟 [E1]"],
                    "methods": ["使用 LAMMPS 和 ReaxFF 进行模拟 [E1]"],
                    "findings": ["RDX 体系与 ReaxFF 图谱关系相匹配 [E1]"],
                    "limitations": ["目前只检索到一条直接 evidence [E1]"],
                    "evidence": [{"evidence_id": "E99", "chunk_id": 99, "source_path": "fake", "snippet": "fake"}],
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr(workflow_module, "LLMClient", FakeLLMClient)
    state = build_answer_state()

    result = answer_generator(state)
    final_output = result["final_output"]

    assert final_output["generation_mode"] == "llm"
    assert final_output["evidence"][0]["evidence_id"] == "E1"
    assert final_output["kg_context"]["items"][0]["path_text"].startswith("(Paper: P1)")
    assert "path_text" in captured["user_prompt"]
    assert "(Paper: P1) -[:USES_FORCE_FIELD]-> (ForceField: ReaxFF)" in captured["user_prompt"]
    assert result["trace"][-1]["output"]["mode"] == "llm"


def test_answer_generator_falls_back_on_invalid_json(monkeypatch):
    class InvalidJsonLLMClient:
        def chat(self, system_prompt: str, user_prompt: str) -> str:
            return "{bad json"

    monkeypatch.setattr(workflow_module, "LLMClient", InvalidJsonLLMClient)
    result = answer_generator(build_answer_state())
    final_output = result["final_output"]

    assert final_output["generation_mode"] == "template_fallback"
    assert final_output["llm_error"]
    assert result["trace"][-1]["output"]["mode"] == "template_fallback"


def test_answer_generator_falls_back_on_invalid_llm_citation(monkeypatch):
    class BadCitationLLMClient:
        def chat(self, system_prompt: str, user_prompt: str) -> str:
            return json.dumps(
                {
                    "summary": "ReaxFF 被用于模拟 [E99]",
                    "comparison_table": [],
                    "mechanisms": [],
                    "methods": [],
                    "findings": [],
                    "limitations": [],
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr(workflow_module, "LLMClient", BadCitationLLMClient)
    result = answer_generator(build_answer_state())
    final_output = result["final_output"]

    assert final_output["generation_mode"] == "template_fallback"
    assert "citation alignment failed" in final_output["llm_error"]


def test_answer_generator_no_evidence_does_not_call_llm(monkeypatch):
    class ExplodingLLMClient:
        def __init__(self):
            raise AssertionError("LLM should not be called without evidence")

    monkeypatch.setattr(workflow_module, "LLMClient", ExplodingLLMClient)
    state = build_answer_state()
    state["fused_evidence"] = []

    result = answer_generator(state)
    final_output = result["final_output"]

    assert final_output["generation_mode"] == "no_evidence"
    assert final_output["evidence"] == []
    assert result["trace"][-1]["output"]["mode"] == "no_evidence"


def test_graph_relations_api_returns_structured_unavailable(monkeypatch):
    class FailingGraphStore:
        def verify(self):
            raise RuntimeError("neo4j down")

        def close(self):
            pass

    monkeypatch.setattr(app_main, "Neo4jGraphStore", FailingGraphStore)
    client = TestClient(app_main.app)

    response = client.get("/literature/graph/relations", params={"term": "RDX", "limit": 5})
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["available"] is False
    assert payload["data"]["items"] == []
    assert payload["data"]["error"] == "neo4j down"


def test_graph_build_api_returns_structured_failure(monkeypatch):
    monkeypatch.setattr(app_main, "load_paper_records", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        app_main,
        "build_literature_graph",
        lambda records, max_papers=None, replace_existing=False: GraphBuildResult(ok=False, extraction_count=0, error="neo4j down"),
    )
    client = TestClient(app_main.app)

    response = client.post("/literature/graph/build", json={"max_papers": 1})
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"]["available"] is False
    assert payload["data"]["ok"] is False
    assert payload["data"]["error"] == "neo4j down"
