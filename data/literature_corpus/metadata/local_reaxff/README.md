# Local ReaxFF Corpus

This folder records PDFs copied from `D:/Desktop/Reaxff` for the energetic-materials MD literature knowledge base.

The original desktop folder was not modified. Files were copied into:

```text
data/literature_corpus/papers/local_reaxff/
├─ core_papers/
├─ reaxff_methods/
└─ supporting_info/
```

## Categories

- `core_paper`: literature that should be considered for the main RAG corpus.
- `reaxff_method`: ReaxFF manuals, equations, force-field format notes and foundational method papers. These are useful for method questions but should not dominate material-performance answers.
- `supporting_info`: supplementary PDFs paired with core papers. These should be skipped by default unless the user asks for detailed mechanisms, reaction paths or parameter tables.

## Recommended Ingestion Defaults

For the first MVP:

1. Ingest `core_paper` with `ingestion_priority=high`.
2. Ingest `reaxff_method` only into a separate `method_reference` collection.
3. Skip `supporting_info` initially.
4. Use `topic_tags` as metadata filters.

This avoids mixing tutorials/manuals with evidence for material-performance claims.

