import re
from typing import Any, List

CITATION_PATTERN = re.compile(r"\[(E\d+(?:\s*,\s*E\d+)*)\]")
CHINESE_SEQ_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}")
LATIN_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9\-\+\/\.]*")

COMMON_STOP_TOKENS = {
    "研究", "结果", "表明", "发现", "说明", "进行", "采用", "方法", "体系",
    "当前", "相关", "主要", "可以", "通过", "具有", "其中", "以及", "方面",
    "process", "method", "study", "result", "using",
}


def extract_cited_ids(text: str) -> List[str]:
    cited_ids: List[str] = []

    for match in CITATION_PATTERN.finditer(text):
        matched_text = match.group(1)
        for part in matched_text.split(","):
            cited_ids.append(part.strip())

    seen = set()
    ordered = []
    for citation_id in cited_ids:
        if citation_id not in seen:
            seen.add(citation_id)
            ordered.append(citation_id)
    return ordered


def strip_citations(text: str) -> str:
    return CITATION_PATTERN.sub("", text).strip()


def extract_tokens(text: str) -> set[str]:
    text = text.lower()
    tokens: set[str] = set()

    for token in LATIN_TOKEN_PATTERN.findall(text):
        if len(token) >= 2:
            tokens.add(token)

    for sequence in CHINESE_SEQ_PATTERN.findall(text):
        if len(sequence) <= 4:
            tokens.add(sequence)
        for i in range(len(sequence) - 1):
            tokens.add(sequence[i:i + 2])

    return {
        token for token in tokens
        if token not in COMMON_STOP_TOKENS and len(token.strip()) >= 2
    }


def evaluate_claim_support(
    claim_text: str,
    cited_evidence_ids: List[str],
    evidence_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    missing_evidence_ids = [eid for eid in cited_evidence_ids if eid not in evidence_map]

    cited_items = [evidence_map[eid] for eid in cited_evidence_ids if eid in evidence_map]
    combined_snippet = " ".join(item.get("snippet", "") for item in cited_items)

    claim_core = strip_citations(claim_text)
    claim_tokens = extract_tokens(claim_core)
    snippet_tokens = extract_tokens(combined_snippet)
    overlap_terms = sorted(claim_tokens & snippet_tokens)

    direct_supported = False
    if claim_tokens and combined_snippet:
        claim_no_space = re.sub(r"\s+", " ", claim_core)
        snippet_no_space = re.sub(r"\s+", " ", combined_snippet)
        direct_supported = claim_no_space in snippet_no_space

    support_score = 0.0
    if claim_tokens:
        support_score = len(overlap_terms) / len(claim_tokens)

    if missing_evidence_ids:
        support_label = "missing_evidence"
    elif direct_supported:
        support_label = "supported"
        support_score = max(support_score, 1.0)
    elif len(overlap_terms) >= 2 and support_score >= 0.20:
        support_label = "supported"
    elif len(overlap_terms) >= 1:
        support_label = "weak_supported"
    else:
        support_label = "unsupported"

    return {
        "claim_text": claim_text,
        "claim_core": claim_core,
        "cited_evidence_ids": cited_evidence_ids,
        "missing_evidence_ids": missing_evidence_ids,
        "support_label": support_label,
        "support_score": round(float(support_score), 4),
        "overlap_terms": overlap_terms,
        "snippet_preview": combined_snippet[:220],
    }


def verify_citations(answer: dict[str, Any]) -> dict[str, Any]:
    evidence_items = answer.get("evidence", [])
    evidence_map = {
        item["evidence_id"]: item
        for item in evidence_items
        if "evidence_id" in item
    }

    checked_items: list[dict[str, Any]] = []
    unsupported_fields: list[str] = []
    uncited_fields: list[str] = []

    summary = answer.get("summary", "")
    summary_citations = extract_cited_ids(summary)
    if not summary_citations:
        unsupported_fields.append("summary")
        checked_items.append(
            {
                "field": "summary",
                "support_label": "no_citation",
                "claim_text": summary,
                "cited_evidence_ids": [],
                "missing_evidence_ids": [],
                "support_score": 0.0,
                "overlap_terms": [],
                "snippet_preview": "",
            }
        )
    else:
        result = evaluate_claim_support(summary, summary_citations, evidence_map)
        result["field"] = "summary"
        checked_items.append(result)
        if result["support_label"] != "supported":
            unsupported_fields.append("summary")

    for field in ["methods", "findings", "limitations"]:
        for idx, text in enumerate(answer.get(field, []), start=1):
            field_key = f"{field}[{idx}]"
            cited_ids = extract_cited_ids(text)

            if not cited_ids:
                uncited_fields.append(field_key)
                checked_items.append(
                    {
                        "field": field_key,
                        "support_label": "no_citation",
                        "claim_text": text,
                        "cited_evidence_ids": [],
                        "missing_evidence_ids": [],
                        "support_score": 0.0,
                        "overlap_terms": [],
                        "snippet_preview": "",
                    }
                )
                continue

            result = evaluate_claim_support(text, cited_ids, evidence_map)
            result["field"] = field_key
            checked_items.append(result)

            if result["support_label"] != "supported":
                unsupported_fields.append(field_key)

    is_verified = len(unsupported_fields) == 0 and len(uncited_fields) == 0

    return {
        "is_verified": is_verified,
        "uncited_fields": uncited_fields,
        "unsupported_fields": unsupported_fields,
        "checked_items": checked_items,
    }