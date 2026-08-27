from core.keyword_retriever import keyword_search_chunks


def test_keyword_search_prioritizes_exact_domain_terms():
    chunks = [
        {
            "id": "a",
            "text": "Reactive molecular dynamics with ReaxFF was used for RDX thermal decomposition.",
            "metadata": {"paper_id": "P1", "section": "methods"},
        },
        {
            "id": "b",
            "text": "This paragraph discusses general energetic material background.",
            "metadata": {"paper_id": "P2", "section": "introduction"},
        },
    ]

    results = keyword_search_chunks("RDX ReaxFF thermal decomposition", chunks, top_k=1)

    assert results[0]["id"] == "a"
    assert results[0]["keyword_score"] > 0


def test_keyword_search_supports_metadata_filter():
    chunks = [
        {"id": "a", "text": "RDX ReaxFF", "metadata": {"section": "methods"}},
        {"id": "b", "text": "RDX ReaxFF", "metadata": {"section": "results"}},
    ]

    results = keyword_search_chunks("RDX", chunks, top_k=5, metadata_filter={"section": "results"})

    assert len(results) == 1
    assert results[0]["id"] == "b"

