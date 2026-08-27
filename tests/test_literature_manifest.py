from core.config import LITERATURE_CORPUS_DIR
from core.literature_indexer import build_paper_chunks
from core.literature_manifest import load_paper_records, summarize_records


def test_load_literature_records_defaults_to_pdf_only_active_corpus():
    records = load_paper_records(LITERATURE_CORPUS_DIR)
    candidates = load_paper_records(LITERATURE_CORPUS_DIR, include_metadata_only=True)

    assert candidates
    assert [record.paper_id for record in records] == [
        record.paper_id for record in candidates if record.has_pdf
    ]
    assert all(record.paper_id for record in records)
    assert all(record.has_pdf for record in records)

    summary = summarize_records(records)
    assert summary["total"] == len(records)
    assert summary["full_text_pdf"] == len(records)
    assert summary["metadata_only"] == 0


def test_candidate_manifest_can_still_report_metadata_only_records():
    records = load_paper_records(LITERATURE_CORPUS_DIR, include_metadata_only=True)

    assert records
    assert any(not record.has_pdf for record in records)

    summary = summarize_records(records)
    assert summary["metadata_only"] >= 1


def test_filter_high_priority_local_reaxff_records():
    records = load_paper_records(
        LITERATURE_CORPUS_DIR,
        categories={"core_paper"},
        priorities={"high"},
        include_metadata_only=False,
    )
    candidates = load_paper_records(
        LITERATURE_CORPUS_DIR,
        categories={"core_paper"},
        priorities={"high"},
        include_metadata_only=True,
    )

    assert candidates
    assert [record.paper_id for record in records] == [
        record.paper_id for record in candidates if record.has_pdf
    ]
    assert all(record.category == "core_paper" for record in records)
    assert all(record.ingestion_priority == "high" for record in records)
    assert all(record.has_pdf for record in records)


def test_metadata_only_records_do_not_generate_chunks_even_if_requested():
    records = load_paper_records(LITERATURE_CORPUS_DIR, include_metadata_only=True)
    metadata_only_record = next(record for record in records if not record.has_pdf)

    chunks = build_paper_chunks([metadata_only_record], include_metadata_only=True)

    assert chunks == []
