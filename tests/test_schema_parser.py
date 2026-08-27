import json
import pytest
from pydantic import ValidationError

from core.schema_parser import parse_literature_answer, parse_research_answer


def test_parse_research_answer_valid():
    raw_text = json.dumps(
        {
            "summary": "MgH2 与 CL-20 体系研究仍较少 [E1]",
            "methods": ["分析物质释放规律 [E1]"],
            "findings": ["CL-20 具有较高晶体密度 [E2]"],
            "limitations": ["证据仍有限 [E1]"],
            "evidence": [
                {
                    "evidence_id": "E1",
                    "chunk_id": 5,
                    "source_path": "data/sample.txt",
                    "snippet": "示例片段"
                }
            ],
        },
        ensure_ascii=False,
    )

    obj = parse_research_answer(raw_text)
    assert obj.summary.startswith("MgH2")
    assert len(obj.methods) == 1
    assert obj.evidence[0].evidence_id == "E1"


def test_parse_research_answer_invalid_json():
    raw_text = '{"summary": "abc", "methods": []'

    with pytest.raises(json.JSONDecodeError):
        parse_research_answer(raw_text)


def test_parse_research_answer_invalid_schema():
    raw_text = json.dumps(
        {
            "summary": "abc",
            "methods": "ReaxFF",
            "findings": [],
            "limitations": [],
            "evidence": [],
        },
        ensure_ascii=False,
    )

    with pytest.raises(ValidationError):
        parse_research_answer(raw_text)


def test_parse_literature_answer_from_markdown_json_block():
    raw_text = """```json
{
  "summary": "ReaxFF 用于 RDX 模拟 [E1]",
  "comparison_table": [
    {
      "paper_id": "P1",
      "material_system": "RDX",
      "method": "reactive molecular dynamics",
      "force_field": "ReaxFF",
      "software": "LAMMPS",
      "conditions": "methods",
      "finding": "论文报告了 ReaxFF 模拟 [E1]",
      "citation": "[E1]"
    }
  ],
  "mechanisms": ["反应分子动力学用于分析 RDX [E1]"],
  "methods": ["使用 ReaxFF [E1]"],
  "findings": ["检索证据支持 ReaxFF 与 RDX 的关联 [E1]"],
  "limitations": ["证据数量有限 [E1]"]
}
```"""

    obj = parse_literature_answer(raw_text)

    assert obj.summary.startswith("ReaxFF")
    assert obj.comparison_table[0].force_field == "ReaxFF"
    assert obj.methods == ["使用 ReaxFF [E1]"]
