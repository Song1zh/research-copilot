from core.section_splitter import PaperChunk
from core.simulation_extractor import extract_from_chunks, extract_simulation_entities


def test_extract_simulation_entities_from_domain_chunk():
    chunk = PaperChunk(
        chunk_id=3,
        paper_id="P1",
        title="RDX HTPB Study",
        section="methods",
        text="LAMMPS and ReaxFF were used for reactive molecular dynamics of RDX/HTPB at 300 K. The results show reduced sensitivity.",
        metadata={"paper_id": "P1", "section": "methods"},
    )

    extraction = extract_simulation_entities(chunk)

    assert extraction.paper_id == "P1"
    assert any(entity.name == "RDX" for entity in extraction.materials)
    assert any(entity.name == "HTPB" for entity in extraction.materials)
    assert any(entity.name == "ReaxFF" for entity in extraction.force_fields)
    assert any(entity.name == "LAMMPS" for entity in extraction.software)
    assert any(entity.name == "300 K" for entity in extraction.conditions)
    assert not any(entity.name == "ReaxFF" for entity in extraction.methods)


def test_entity_matching_does_not_use_ascii_substrings():
    chunk = PaperChunk(
        chunk_id=4,
        paper_id="P2",
        title="Boundary Test",
        section="methods",
        text="All thermal results fall into the expected interval.",
        metadata={"paper_id": "P2", "section": "methods"},
    )

    extraction = extract_simulation_entities(chunk)

    assert not any(entity.name == "Al" for entity in extraction.materials)
    assert not any(entity.name == "NTO" for entity in extraction.materials)


def test_reference_dense_unknown_chunk_is_excluded_from_graph_extraction():
    chunk = PaperChunk(
        chunk_id=5,
        paper_id="P3",
        title="Reference Test",
        section="unknown",
        text=(
            "[21] A. Author, HMX and ReaxFF, J. Chem. Phys. 2018.\n"
            "[22] B. Author, RDX simulation, J. Comput. Chem. 2019.\n"
            "[23] C. Author, TATB properties, Phys. Rev. 2020."
        ),
        metadata={"paper_id": "P3", "section": "unknown"},
    )

    assert extract_from_chunks([chunk]) == []


def test_reference_tail_excludes_later_unknown_chunks_from_same_paper():
    reference_chunk = PaperChunk(
        chunk_id=6,
        paper_id="P4",
        title="Reference Tail",
        section="unknown",
        text=(
            "[1] A. Author, J. Chem. Phys. 2018.\n"
            "[2] B. Author, J. Comput. Chem. 2019.\n"
            "[3] C. Author, Phys. Rev. 2020."
        ),
        metadata={"paper_id": "P4", "section": "unknown"},
    )
    later_reference_fragment = PaperChunk(
        chunk_id=7,
        paper_id="P4",
        title="Reference Tail",
        section="unknown",
        text="HMX and ReaxFF appear in a later bibliography fragment.",
        metadata={"paper_id": "P4", "section": "unknown"},
    )

    assert extract_from_chunks([reference_chunk, later_reference_fragment]) == []
