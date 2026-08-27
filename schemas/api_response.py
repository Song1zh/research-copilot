from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResponseMeta(BaseModel):
    request_id: str = Field(..., description="Unique request id for tracing")
    timestamp: str = Field(..., description="UTC ISO-8601 timestamp")
    latency_ms: float | None = Field(default=None, description="Request latency in milliseconds")


class ErrorBody(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    stage: str | None = Field(default=None, description="Pipeline stage where the error occurred")
    details: Any | None = Field(default=None, description="Optional debug details")


class ApiResponse(BaseModel):
    success: bool
    code: str
    message: str
    data: dict[str, Any] | None = None
    error: ErrorBody | None = None
    meta: ResponseMeta