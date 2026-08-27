from __future__ import annotations

import re
from typing import Iterable

from core.section_splitter import PaperChunk
from schemas.simulation_extraction import (
    Finding,
    ForceField,
    MaterialSystem,
    Property,
    SimulationCondition,
    SimulationExtraction,
    SimulationMethod,
    Software,
)


MATERIAL_TERMS = [
    "CL-20",
    "HMX",
    "RDX",
    "TATB",
    "PETN",
    "NTO",
    "LLM-105",
    "FOX-7",
    "TKX-50",
    "HTPB",
    "PBX",
    "Al",
    "aluminum",
    "DNB",
    "TNT",
    "DNAN",
]

METHOD_TERMS = [
    "molecular dynamics",
    "reactive molecular dynamics",
    "quantum molecular dynamics",
    "first-principles molecular dynamics",
    "ab initio molecular dynamics",
    "DFT",
]

FORCE_FIELD_TERMS = [
    "ReaxFF",
    "ReaxFF-lg",
    "COMPASS",
    "PCFF",
    "Dreiding",
    "UFF",
]

SOFTWARE_TERMS = [
    "LAMMPS",
    "Materials Studio",
    "VASP",
    "Gaussian",
    "GROMACS",
    "CP2K",
]

PROPERTY_TERMS = [
    "thermal decomposition",
    "sensitivity",
    "mechanical properties",
    "binding energy",
    "cohesive energy density",
    "thermal conductivity",
    "diffusion coefficient",
    "elastic modulus",
    "detonation performance",
    "hotspot",
]

CONDITION_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:K|GPa|MPa|ps|fs|ns|K/ps|K ps-1)\b",
    flags=re.IGNORECASE,
)


def _term_pattern(term: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<![A-Za-z0-9-]){re.escape(term)}(?![A-Za-z0-9-])",
        flags=re.IGNORECASE,
    )


def _contains_term(text: str, term: str) -> bool:
    return _term_pattern(term).search(text) is not None


def _looks_like_reference_chunk(text: str) -> bool:
    lowered = text.lower()
    if re.search(r"(?:^|\n)\s*(references|bibliography|参考文献)\s*(?:\n|$)", lowered):
        return True
    numbered_references = len(
        re.findall(r"(?:^|\n)\s*(?:\[\d{1,3}\]|\(\d{1,3}\)|\d{1,3}\.)\s+", text)
    )
    years = len(re.findall(r"\b(?:19|20)\d{2}\b", text))
    dois = lowered.count("doi")
    journal_markers = len(
        re.findall(r"\b(?:j\.|journal|phys\.|chem\.|proc\.|rev\.|comput\.)", lowered)
    )
    return (
        numbered_references >= 3 and years >= 2
    ) or (
        years >= 5 and journal_markers >= 3
    ) or (
        numbered_references >= 2 and dois >= 2
    )


def _snippet(text: str, term: str, max_len: int = 220) -> str:
    lower = text.lower()
    idx = lower.find(term.lower())
    if idx == -1:
        return text[:max_len]
    start = max(0, idx - 80)
    end = min(len(text), idx + len(term) + 120)
    return text[start:end].strip()[:max_len]


def extract_simulation_entities(chunk: PaperChunk) -> SimulationExtraction:
    text = chunk.text
    evidence_id = chunk.chunk_id

    materials = [
        MaterialSystem(name=term, evidence_chunk_id=evidence_id, evidence_text=_snippet(text, term))
        for term in MATERIAL_TERMS
        if _contains_term(text, term)
    ]
    methods = [
        SimulationMethod(name=term, evidence_chunk_id=evidence_id, evidence_text=_snippet(text, term))
        for term in METHOD_TERMS
        if _contains_term(text, term)
    ]
    force_fields = [
        ForceField(name=term, evidence_chunk_id=evidence_id, evidence_text=_snippet(text, term))
        for term in FORCE_FIELD_TERMS
        if _contains_term(text, term)
    ]
    software = [
        Software(name=term, evidence_chunk_id=evidence_id, evidence_text=_snippet(text, term))
        for term in SOFTWARE_TERMS
        if _contains_term(text, term)
    ]
    conditions = [
        SimulationCondition(
            name=match.group(0),
            condition_type="simulation_parameter",
            evidence_chunk_id=evidence_id,
            evidence_text=_snippet(text, match.group(0)),
        )
        for match in CONDITION_PATTERN.finditer(text)
    ][:12]
    properties = [
        Property(name=term, evidence_chunk_id=evidence_id, evidence_text=_snippet(text, term))
        for term in PROPERTY_TERMS
        if _contains_term(text, term)
    ]

    findings: list[Finding] = []
    for sentence in re.split(r"(?<=[.!?。！？])\s+", text):
        sentence_lower = sentence.lower()
        if any(marker in sentence_lower for marker in ["indicat", "show", "suggest", "improv", "reduce", "increase"]):
            findings.append(
                Finding(
                    name=sentence.strip()[:180],
                    evidence_chunk_id=evidence_id,
                    evidence_text=sentence.strip()[:260],
                )
            )
        if len(findings) >= 3:
            break

    return SimulationExtraction(
        paper_id=chunk.paper_id,
        chunk_id=chunk.chunk_id,
        materials=materials,
        methods=methods,
        force_fields=force_fields,
        software=software,
        conditions=conditions,
        properties=properties,
        findings=findings,
    )


def extract_from_chunks(chunks: Iterable[PaperChunk]) -> list[SimulationExtraction]:
    target_sections = {"methods", "results", "conclusion", "unknown"}
    reference_tail_papers: set[str] = set()
    results: list[SimulationExtraction] = []
    for chunk in chunks:
        if chunk.paper_id in reference_tail_papers:
            continue
        if chunk.section == "references" or (
            chunk.section == "unknown" and _looks_like_reference_chunk(chunk.text)
        ):
            reference_tail_papers.add(chunk.paper_id)
            continue
        if chunk.section not in target_sections:
            continue
        extraction = extract_simulation_entities(chunk)
        if any(
            [
                extraction.materials,
                extraction.methods,
                extraction.force_fields,
                extraction.software,
                extraction.conditions,
                extraction.properties,
                extraction.findings,
            ]
        ):
            results.append(extraction)
    return results
