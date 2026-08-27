from core.paper_loader import PaperDocument
from core.section_splitter import split_into_sections, split_paper_document


def test_split_into_common_paper_sections():
    text = """Abstract
This paper studies RDX.

1 Introduction
Background.

Methods
Reactive molecular dynamics with ReaxFF was used.

Results and Discussion
Thermal decomposition was observed.

Conclusions
The method is useful.
"""
    sections = split_into_sections(text)

    names = [name for name, _ in sections]
    assert "abstract" in names
    assert "introduction" in names
    assert "methods" in names
    assert "results" in names
    assert "conclusion" in names


def test_split_paper_document_preserves_metadata():
    doc = PaperDocument(
        paper_id="P1",
        title="RDX ReaxFF Study",
        text="Methods\nReactive molecular dynamics with ReaxFF was used for RDX.\nResults\nThermal decomposition changed.",
        metadata={"paper_id": "P1", "title": "RDX ReaxFF Study", "doi": "10.test/example"},
    )

    chunks = split_paper_document(doc, chunk_size=80, chunk_overlap=10)

    assert chunks
    assert all(chunk.metadata["paper_id"] == "P1" for chunk in chunks)
    assert {chunk.section for chunk in chunks} <= {"methods", "results"}

