# Literature Corpus: Energetic Materials MD Simulation

This folder is a seed corpus for the planned Agentic RAG project:

**Energetic Materials Simulation Copilot** - a literature knowledge-base system for molecular-dynamics studies of energetic-material composites and PBX systems.

## Scope

The corpus focuses on:

- CL-20, HMX, RDX, NTO, LLM-105 and related energetic materials.
- Composite systems, cocrystals, PBX interfaces, binders, defects, pores and metal additives.
- Molecular dynamics, reactive molecular dynamics, ReaxFF/ReaxFF-lg, quantum molecular dynamics and first-principles MD.
- Properties such as mechanical response, sensitivity, thermal decomposition, interface interaction, thermal conductivity and structure-property relationships.

## Folder Layout

```text
literature_corpus/
├─ metadata/
│  ├─ paper_manifest.csv
│  ├─ manual_download_targets.md
│  ├─ core_downloaded_manifest.csv
│  ├─ core_download_failed.csv
│  ├─ core_paper_inventory.csv
│  └─ local_reaxff/
│     ├─ README.md
│     └─ local_reaxff_manifest.csv
├─ papers/
│  ├─ EMMD-016.pdf
│  ├─ core_downloaded/
│  └─ local_reaxff/
│     ├─ core_papers/
│     ├─ reaxff_methods/
│     └─ supporting_info/
└─ README.md
```

## Manifest

`metadata/paper_manifest.csv` contains 45 curated papers.

Important columns:

- `paper_id`: stable internal corpus id.
- `doi`: DOI used for metadata lookup and deduplication.
- `topic_tags`: domain tags for future retrieval filters and KG extraction.
- `corpus_role`: why the paper is useful for the project.
- `access_status`: open-access status estimate.
- `pdf_url`: direct PDF URL only when an open PDF source was found.

## PDF Policy

Only open-access or publicly downloadable PDFs should be stored in `papers/`.

Do not place paywalled PDFs from institutional access, Sci-Hub, or other unauthorized sources in this repository. For closed papers, keep only DOI, title and metadata in the manifest as candidate records.

The active knowledge base is PDF-only: metadata-only records are not indexed into Chroma, not used for Agentic RAG answers, and not written into Neo4j. This keeps every answer traceable to full-text evidence.

## Current Download Status

Core QA corpus:

- `metadata/core_paper_inventory.csv` contains 26 core papers for the main paper-QA corpus.
- `papers/core_downloaded/` contains 16 open-download core papers from OpenAlex-discovered sources and official arXiv PDFs.
- `papers/EMMD-016.pdf` contributes 1 curated open PDF.
- `papers/local_reaxff/core_papers/` contributes 9 local ReaxFF/energetic-material core PDFs copied from `D:/Desktop/Reaxff`.

Downloaded earlier:

- `papers/EMMD-016.pdf` - Acta Chimica Sinica, CL-20/HMX cocrystal PBX MD paper.

Direct scripted download was blocked by publisher-side 403 for several otherwise open papers, including MDPI and ACS Omega records. Use the `pdf_url` values in the manifest for manual browser download if needed.

## Local ReaxFF Corpus

`papers/local_reaxff/` contains PDFs copied from `D:/Desktop/Reaxff` without modifying the original desktop folder.

The local corpus currently contains:

- `core_papers/`: RDX decomposition, CL-20/TNT sensitivity, RDX-Al interface, condensed-phase energetic-material mechanisms and propellant references.
- `reaxff_methods/`: ReaxFF manuals, equations, parameter-format notes and foundational method papers.
- `supporting_info/`: supplementary PDFs paired with RDX core papers.

Use `metadata/local_reaxff/local_reaxff_manifest.csv` for ingestion. For the first MVP, ingest only `category=core_paper` and `ingestion_priority=high`; put `reaxff_method` into a separate method-reference collection.

## Recommended Initial MVP Subset

For the first formal demo, index all available PDFs. For quick learning or debugging, you can temporarily index a 15-20 paper subset:

- CL-20/PBX and CL-20 cocrystal papers: `EMMD-005` to `EMMD-024`.
- HMX thermal decomposition and HMX/PBX papers: `EMMD-025` to `EMMD-030`.
- RDX/HTPB, RDX/Al and RDX PBX papers: `EMMD-033` to `EMMD-039`.
- General ReaxFF baselines: `EMMD-042` to `EMMD-045`.

This subset is enough to demonstrate:

- literature ingestion,
- metadata extraction,
- section-aware chunking,
- vector retrieval,
- domain schema extraction,
- lightweight knowledge graph construction,
- Agentic RAG query planning,
- citation-aware multi-paper answers.

## Example Questions

- Which CL-20-based PBX systems have been studied with molecular dynamics, and what binders were compared?
- Which papers report thermal decomposition mechanisms using ReaxFF or quantum molecular dynamics?
- How do CL-20/HMX cocrystals differ from CL-20/HMX composites in mechanical properties and sensitivity?
- Which RDX composite systems involve HTPB or aluminum, and what performance or decomposition behavior is reported?
- What simulation methods and force fields are most common across this corpus?
