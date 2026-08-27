from core.api_response import failure_response, success_response


def test_success_response_contains_stable_contract():
    response = success_response(data={"file_name": "sample.txt"}, latency_ms=12.3)
    payload = response.model_dump()

    assert payload["success"] is True
    assert payload["code"] == "OK"
    assert payload["message"] == "请求成功"
    assert payload["data"] == {"file_name": "sample.txt"}
    assert payload["error"] is None
    assert payload["meta"]["request_id"]
    assert payload["meta"]["timestamp"].endswith("+00:00")
    assert payload["meta"]["latency_ms"] == 12.3


def test_failure_response_uses_details_field():
    response = failure_response(
        code="MODEL_JSON_INVALID",
        message="模型输出不是合法 JSON。",
        stage="format_output",
        details={"line": 1},
    )
    payload = response.model_dump()

    assert payload["success"] is False
    assert payload["message"] == "模型输出不是合法 JSON。"
    assert payload["error"] == {
        "code": "MODEL_JSON_INVALID",
        "stage": "format_output",
        "details": {"line": 1},
    }