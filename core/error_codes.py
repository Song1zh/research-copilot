from enum import Enum
from typing import Any

class ErrorCode(str, Enum):
    DOC_EMPTY = "DOC_EMPTY"
    RETRIEVE_EMPTY = "RETRIEVE_EMPTY"
    MODEL_EMPTY_OUTPUT = "MODEL_EMPTY_OUTPUT"
    MODEL_JSON_INVALID = "MODEL_JSON_INVALID"
    MODEL_SCHEMA_INVALID = "MODEL_SCHEMA_INVALID"
    INTERNAL_ERROR = "INTERNAL_ERROR"

def build_error_info(
        code: ErrorCode,
        message: str,
        stage: str,
        details: Any | None = None,
) -> dict[str, Any]:
    return {
        "code": code.value,
        "message": message,
        "stage": stage,
        "details": details,
    }

def build_failure_output(error_info: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": "",
        "methods": [],
        "findings": [],
        "limitations": [f"{error_info['code']}:{error_info['message']}"],
        "evidence": [],
    }