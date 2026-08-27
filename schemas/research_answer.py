from pydantic import BaseModel, Field
from typing import List


class EvidenceItem(BaseModel):
    evidence_id: str = Field(..., description="证据编号，如 E1")
    chunk_id: int | str = Field(..., description="来源 chunk id")
    source_path: str = Field(..., description="来源文档路径")
    snippet: str = Field(..., description="证据片段摘要/截断片段")
    paper_id: str = ""
    title: str = ""
    section: str = ""
    rank: int | None = None
    hybrid_score: float | None = None
    pre_rerank_rank: int | None = None
    pre_rerank_score: float | None = None
    rerank_score: float | None = None
    reranker_model: str | None = None
    rerank_candidate_count: int | None = None
    rerank_latency_ms: float | None = None


class ResearchCopilotAnswer(BaseModel):
    summary: str = Field(..., description="对问题的简要总结，必须附 evidence_id 引用")
    methods: List[str] = Field(default_factory=list, description="方法列表，每条必须附 evidence_id 引用")
    findings: List[str] = Field(default_factory=list, description="发现列表，每条必须附 evidence_id 引用")
    limitations: List[str] = Field(default_factory=list, description="局限列表，每条必须附 evidence_id 引用")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="结构化 evidence 列表")
