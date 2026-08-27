from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from schemas.api_response import ApiResponse, ErrorBody, ResponseMeta


def build_meta(latency_ms: float | None = None, request_id: str | None = None) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id or str(uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        latency_ms=latency_ms,
    )


def success_response(
    *,
    data: dict[str, Any] | None = None,
    message: str = "请求成功",
    code: str = "OK",
    latency_ms: float | None = None,
    request_id: str | None = None,
) -> ApiResponse:
    return ApiResponse(
        success=True,
        code=code,
        message=message,
        data=data,
        error=None,
        meta=build_meta(latency_ms=latency_ms, request_id=request_id),
    )


def failure_response(
    *,
    code: str,
    message: str,
    stage: str | None = None,
    details: Any | None = None,
    data: dict[str, Any] | None = None,
    latency_ms: float | None = None,
    request_id: str | None = None,
) -> ApiResponse:
    return ApiResponse(
        success=False,
        code=code,
        message=message,
        data=data,
        error=ErrorBody(code=code, stage=stage, details=details),
        meta=build_meta(latency_ms=latency_ms, request_id=request_id),
    )