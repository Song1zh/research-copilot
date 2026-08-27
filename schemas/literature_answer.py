from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from schemas.research_answer import EvidenceItem


class MethodComparisonRow(BaseModel):
    paper_id: str
    material_system: str = ""
    method: str = ""
    force_field: str = ""
    software: str = ""
    conditions: str = ""
    finding: str = ""
    citation: str = ""


class LiteratureAgentAnswer(BaseModel):
    summary: str = Field(..., description="Answer summary with evidence citations")
    comparison_table: list[MethodComparisonRow] = Field(default_factory=list)
    mechanisms: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    query_plan: list[str] = Field(default_factory=list)
    kg_context: dict[str, Any] = Field(default_factory=dict)
    generation_mode: str = ""
    llm_error: str | None = None
