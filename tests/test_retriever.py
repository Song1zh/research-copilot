from unittest.mock import patch
import pytest

from core.retriever import retrieve_evidence


def test_retrieve_evidence_formats_results():
    mocked_results = [
        {
            "id": "sample.txt::chunk_5",
            "text": "MgH2 对 CL-20 热解反应具有协同作用。",
            "metadata": {
                "chunk_id": 5,
                "source_path": "data/sample.txt",
                "file_type": "txt",
            },
            "distance": 0.25,
        },
        {
            "id": "sample.txt::chunk_3",
            "text": "现有研究大多集中在铝粉体系。",
            "metadata": {
                "chunk_id": 3,
                "source_path": "data/sample.txt",
                "file_type": "txt",
            },
            "distance": 0.40,
        },
    ]

    with patch("core.retriever.ChromaVectorStore") as store_cls:
        store_cls.return_value.query.return_value = mocked_results
        results = retrieve_evidence(
            query="MgH2/CL-20 体系中有哪些关键发现",
            top_k=2,
            db_path="dummy_db",
            collection_name="dummy_collection",
        )

    assert len(results) == 2
    assert results[0]["rank"] == 1
    assert results[1]["rank"] == 2
    assert "score" in results[0]
    assert "raw_distance" in results[0]
    assert results[0]["metadata"]["chunk_id"] == 5


def test_retrieve_evidence_blank_query_raises():
    with pytest.raises(ValueError):
        retrieve_evidence(
            query="   ",
            top_k=2,
            db_path="dummy_db",
            collection_name="dummy_collection",
        )
