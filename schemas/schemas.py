from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class Citation(BaseModel):
    title: str = Field(..., description="引用标题")
    source: str = Field(..., description="引用来源，如论文、官网、文档平台")
    url: str | None = Field(default=None, description="引用链接，可为空")


class StructuredAnswer(BaseModel):
    topic: str = Field(..., description="当前回答主题")
    summary: str = Field(..., description="对主题的简要总结")
    key_points: List[str] = Field(..., description="核心要点列表")
    citations: List[Citation] = Field(default_factory=list, description="引用信息列表")
    uncertainty: str | None = Field(default=None, description="不确定性说明，可为空")