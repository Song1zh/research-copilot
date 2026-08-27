import pytest

from core.history_store import RequestHistoryStore


def test_history_store_insert_and_list_recent():
    store = RequestHistoryStore(":memory:")

    record_id = store.insert_record(
        query="MgH2/CL-20 体系中有哪些关键方法和发现",
        answer_summary="研究通过分析物质释放规律与化学键演化轨迹研究 MgH2 对 CL-20 热解过程的影响。",
        timestamp="2026-04-20T10:00:00+00:00",
        latency_ms=123.45,
    )

    rows = store.list_recent(limit=10)

    assert len(rows) == 1
    assert rows[0]["id"] == record_id
    assert rows[0]["query"] == "MgH2/CL-20 体系中有哪些关键方法和发现"
    assert rows[0]["latency_ms"] == 123.45


def test_history_store_orders_by_timestamp_desc():
    store = RequestHistoryStore(":memory:")

    store.insert_record(
        query="old query",
        answer_summary="old answer",
        timestamp="2026-04-20T09:00:00+00:00",
        latency_ms=200.0,
    )
    store.insert_record(
        query="new query",
        answer_summary="new answer",
        timestamp="2026-04-20T10:00:00+00:00",
        latency_ms=100.0,
    )

    rows = store.list_recent(limit=10)

    assert len(rows) == 2
    assert rows[0]["query"] == "new query"
    assert rows[1]["query"] == "old query"


def test_history_store_invalid_limit_raises():
    store = RequestHistoryStore(":memory:")

    with pytest.raises(ValueError):
        store.list_recent(limit=0)
