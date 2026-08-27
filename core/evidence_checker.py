import re
from typing import Any

CITATION_PATTERN = re.compile(r"\[(E\d+(?:\s*,\s*E\d+)*)\]")


def extract_evidence_ids(text: str) -> set[str]:
    ids = set()

    for match in CITATION_PATTERN.finditer(text):
        matched_text = match.group(1)  # 例如 "E1,E2"
        for part in matched_text.split(","):
            ids.add(part.strip())

    return ids


def check_answer_evidence_alignment(answer: dict[str, Any]) -> dict[str, Any]:
    evidence_items = answer.get("evidence", [])
    available_ids = {item["evidence_id"] for item in evidence_items if "evidence_id" in item}

    missing_citation_fields: list[str] = []
    invalid_citations: dict[str, list[str]] = {}
    referenced_ids: set[str] = set()

    summary = answer.get("summary", "")
    summary_ids = extract_evidence_ids(summary)
    if not summary_ids:
        missing_citation_fields.append("summary")
    else:
        referenced_ids |= summary_ids
        invalid = sorted(summary_ids - available_ids)
        if invalid:
            invalid_citations["summary"] = invalid

    for field in ["methods", "findings", "limitations", "mechanisms"]:
        items = answer.get(field, [])
        for idx, text in enumerate(items, start=1):
            ids = extract_evidence_ids(text)
            field_key = f"{field}[{idx}]"

            if not ids:
                missing_citation_fields.append(field_key)
                continue

            referenced_ids |= ids
            invalid = sorted(ids - available_ids)
            if invalid:
                invalid_citations[field_key] = invalid

    for idx, row in enumerate(answer.get("comparison_table", []), start=1):
        finding = row.get("finding", "") if isinstance(row, dict) else ""
        if not finding:
            continue

        ids = extract_evidence_ids(finding)
        field_key = f"comparison_table[{idx}].finding"
        if not ids:
            missing_citation_fields.append(field_key)
            continue

        referenced_ids |= ids
        invalid = sorted(ids - available_ids)
        if invalid:
            invalid_citations[field_key] = invalid

    unused_evidence_ids = sorted(available_ids - referenced_ids)

    is_aligned = (len(missing_citation_fields) == 0 and len(invalid_citations) == 0)

    return {
        "is_aligned": is_aligned,
        "missing_citation_fields": missing_citation_fields,
        "invalid_citations": invalid_citations,
        "unused_evidence_ids": unused_evidence_ids,
    }
