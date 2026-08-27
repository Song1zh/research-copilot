import pytest

from core.text_splitter import split_text

def test_split_text_basic():
    text = "A" * 1200
    chunks = split_text(text, chunk_size=500, chunk_overlap=50)

    assert len(chunks) == 3
    assert all(isinstance(chunk, str) for chunk in chunks)
    assert chunks[0][-50:] == chunks[1][:50]
    assert chunks[1][-50:] == chunks[2][:50]

def test_split_text_empty_returns_empty_list():
    chunks = split_text("", chunk_size=500, chunk_overlap=50)
    assert chunks == []

def test_split_text_invalid_chunk_size_raises():
    with pytest.raises(ValueError):
        split_text("abc", chunk_size=0, chunk_overlap=0)

def test_split_text_invalid_overlap_raises():
    with pytest.raises(ValueError):
        split_text("abc", chunk_size=10, chunk_overlap=10)