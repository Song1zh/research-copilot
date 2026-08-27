from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable

from core.llm_client import LLMClient


CITATION_PATTERN = re.compile(r"\[(E\d+(?:\s*,\s*E\d+)*)\]")


@dataclass
class GroundednessResult:
    claim_count: int
    supported_claims: int
    partial_claims: int
    unsupported_claims: int
    claim_support_rate: float
    weighted_claim_support_rate: float
    citation_coverage: float
    citation_precision: float
    answer_correctness: float
    refusal_correct: bool | None
    claims: list[dict[str, Any]]
    judge_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strip_code_fence(value: str) -> str:
    value = value.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
    return value.strip()


def extract_answer_claims(answer: dict[str, Any]) -> list[str]:
    values: list[str] = []
    summary = str(answer.get("summary") or "").strip()
    if summary:
        values.extend(
            part.strip()
            for part in re.split(r"(?<=[。！？.!?])\s*", summary)
            if part.strip()
        )
    for field in ("mechanisms", "methods", "findings"):
        values.extend(str(item).strip() for item in answer.get(field, []) if str(item).strip())
    for row in answer.get("comparison_table", []):
        finding = str((row or {}).get("finding") or "").strip()
        if finding:
            values.append(finding)
    return list(dict.fromkeys(values))


def _citation_metrics(
    claims: list[str], evidence: list[dict[str, Any]]
) -> tuple[float, float]:
    available = {str(item.get("evidence_id")) for item in evidence}
    covered = 0
    cited_ids: list[str] = []
    for claim in claims:
        matches = CITATION_PATTERN.findall(claim)
        if matches:
            covered += 1
        for match in matches:
            cited_ids.extend(part.strip() for part in match.split(","))
    coverage = covered / len(claims) if claims else 1.0
    precision = (
        sum(citation in available for citation in cited_ids) / len(cited_ids)
        if cited_ids
        else (1.0 if not claims else 0.0)
    )
    return coverage, precision


def build_groundedness_prompt(
    *,
    question: str,
    answer: dict[str, Any],
    reference_answer: str,
    required_claims: list[str],
    should_refuse: bool,
) -> tuple[str, str]:
    claims = extract_answer_claims(answer)
    evidence = [
        {
            "evidence_id": item.get("evidence_id"),
            "paper_id": item.get("paper_id"),
            "chunk_id": item.get("chunk_id"),
            "snippet": item.get("snippet"),
        }
        for item in answer.get("evidence", [])
    ]
    payload = {
        "question": question,
        "claims": claims,
        "evidence": evidence,
        "reference_answer": reference_answer,
        "required_claims": required_claims,
        "should_refuse": should_refuse,
        "answer_summary": answer.get("summary", ""),
        "answer_limitations": answer.get("limitations", []),
    }
    system_prompt = (
        "You are a strict RAG groundedness evaluator. Judge each atomic claim only "
        "against the supplied evidence snippets. A supported label requires direct "
        "textual or clearly entailed support; topical similarity is insufficient. "
        "Use partial when only part of the claim is supported. Evaluate answer "
        "correctness against the reference and required claims on a 0-1 scale. "
        "For should_refuse=true, refusal_correct is true only if the answer clearly "
        "states that the evidence cannot answer the question and does not invent an "
        "answer. Return JSON only. Return exactly one judged item for every input "
        "claim, in the same order, without merging, omitting, or adding claims."
    )
    user_prompt = (
        f"The INPUT contains exactly {len(claims)} claims. The output claims array "
        f"must contain exactly {len(claims)} items in the same order.\n"
        "Return this exact shape:\n"
        '{"claims":[{"claim_index":0,"claim":"","label":"supported|partial|unsupported",'
        '"evidence_ids":["E1"],"reason":""}],'
        '"answer_correctness":0.0,"refusal_correct":null}\n\n'
        f"INPUT:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    return system_prompt, user_prompt


def _repair_claim_count_with_judge(
    *,
    judge: Callable[[str, str], str],
    original_payload: dict[str, Any],
    previous_response: Any,
    expected_claims: list[str],
) -> dict[str, Any]:
    system_prompt = (
        "You are repairing a RAG groundedness JSON response. Return JSON only. "
        "You must judge every expected claim independently against the supplied "
        "evidence, preserving the exact expected claim order and count."
    )
    user_prompt = (
        f"Return exactly {len(expected_claims)} claim judgments, one per expected "
        "claim. Do not merge or omit claims.\n"
        "Return this exact shape:\n"
        '{"claims":[{"claim_index":0,"claim":"","label":"supported|partial|unsupported",'
        '"evidence_ids":["E1"],"reason":""}],'
        '"answer_correctness":0.0,"refusal_correct":null}\n\n'
        "EXPECTED_CLAIMS:\n"
        f"{json.dumps(expected_claims, ensure_ascii=False, indent=2)}\n\n"
        "ORIGINAL_INPUT:\n"
        f"{json.dumps(original_payload, ensure_ascii=False, indent=2)}\n\n"
        "PREVIOUS_BAD_RESPONSE:\n"
        f"{json.dumps(previous_response, ensure_ascii=False, indent=2)}"
    )
    return json.loads(_strip_code_fence(judge(system_prompt, user_prompt)))


def evaluate_groundedness(
    *,
    question: str,
    answer: dict[str, Any],
    reference_answer: str,
    required_claims: list[str],
    should_refuse: bool,
    judge: Callable[[str, str], str] | None = None,
) -> GroundednessResult:
    answer_claims = extract_answer_claims(answer)
    citation_coverage, citation_precision = _citation_metrics(
        answer_claims, answer.get("evidence", [])
    )
    if judge is None:
        client = LLMClient()
        judge = lambda system, user: client.chat(system_prompt=system, user_prompt=user)

    system_prompt, user_prompt = build_groundedness_prompt(
        question=question,
        answer=answer,
        reference_answer=reference_answer,
        required_claims=required_claims,
        should_refuse=should_refuse,
    )
    try:
        raw = judge(system_prompt, user_prompt)
        parsed = json.loads(_strip_code_fence(raw))
        judged_claims = parsed.get("claims", [])
        if not isinstance(judged_claims, list):
            raise ValueError("judge claims must be a list")
        if len(judged_claims) != len(answer_claims):
            parsed = _repair_claim_count_with_judge(
                judge=judge,
                original_payload={
                    "question": question,
                    "answer": answer,
                    "reference_answer": reference_answer,
                    "required_claims": required_claims,
                    "should_refuse": should_refuse,
                },
                previous_response=parsed,
                expected_claims=answer_claims,
            )
            judged_claims = parsed.get("claims", [])
            if not isinstance(judged_claims, list):
                raise ValueError("judge claims must be a list")
            if len(judged_claims) != len(answer_claims):
                raise ValueError(
                    "judge claim count does not match extracted answer claims: "
                    f"expected {len(answer_claims)}, got {len(judged_claims)}"
                )
        labels = [str(item.get("label", "unsupported")).lower() for item in judged_claims]
        if any(label not in {"supported", "partial", "unsupported"} for label in labels):
            raise ValueError("judge returned an invalid claim label")
        supported = labels.count("supported")
        partial = labels.count("partial")
        unsupported = labels.count("unsupported")
        count = len(labels)
        correctness = min(max(float(parsed.get("answer_correctness", 0.0)), 0.0), 1.0)
        refusal = parsed.get("refusal_correct")
        if refusal is not None and not isinstance(refusal, bool):
            raise ValueError("refusal_correct must be bool or null")
        return GroundednessResult(
            claim_count=count,
            supported_claims=supported,
            partial_claims=partial,
            unsupported_claims=unsupported,
            claim_support_rate=round(supported / count, 4) if count else 1.0,
            weighted_claim_support_rate=(
                round((supported + 0.5 * partial) / count, 4) if count else 1.0
            ),
            citation_coverage=round(citation_coverage, 4),
            citation_precision=round(citation_precision, 4),
            answer_correctness=round(correctness, 4),
            refusal_correct=refusal,
            claims=judged_claims,
        )
    except Exception as exc:
        return GroundednessResult(
            claim_count=0,
            supported_claims=0,
            partial_claims=0,
            unsupported_claims=0,
            claim_support_rate=0.0,
            weighted_claim_support_rate=0.0,
            citation_coverage=round(citation_coverage, 4),
            citation_precision=round(citation_precision, 4),
            answer_correctness=0.0,
            refusal_correct=None,
            claims=[],
            judge_error=f"{type(exc).__name__}: {exc}",
        )
